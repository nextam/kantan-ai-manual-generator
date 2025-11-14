"""
File: unified_manual_generator.py
Purpose: Unified manual generation service supporting multiple output formats
Main functionality: Multi-format manual generation with configurable options
Dependencies: GeminiUnifiedService, FileManager, OpenCV, markdown (optional)
"""

import os
import json
import logging
import base64
import tempfile
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.services.gemini_service import GeminiService
from src.infrastructure.file_manager import FileManager
from src.config.output_formats import get_format_info, is_valid_format, get_default_format

logger = logging.getLogger(__name__)

# Optional dependencies - check availability
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("opencv-python not installed - keyframe extraction will be disabled")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("numpy not installed - some features may be limited")

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    logger.info("markdown library not installed - using fallback HTML conversion")

try:
    from google.cloud import storage
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    logger.warning("google-cloud-storage not installed - GCS video download disabled")


class UnifiedManualGenerator:
    """
    Unified manual generation service supporting multiple output formats
    
    Supports:
    - text_only: Text-only detailed manual
    - text_with_images: Text with image snapshots
    - text_with_video_clips: Text with video clips
    - subtitle_video: Original video with subtitles
    - hybrid: Combined multiple formats
    """
    
    def __init__(self):
        """Initialize unified manual generator"""
        import os
        self.gemini_service = GeminiService()
        
        # Initialize FileManager with GCS configuration
        storage_type = os.getenv('STORAGE_TYPE', 'gcs')
        storage_config = {
            'bucket_name': os.getenv('GCS_BUCKET_NAME', 'kantan-ai-manual-generator-dev'),
            'credentials_path': os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'gcp-credentials.json')
        }
        self.file_manager = FileManager(storage_type=storage_type, storage_config=storage_config)
    
    async def generate_manual(
        self,
        videos: List[Dict[str, str]],
        output_format: str,
        generation_config: Dict[str, Any],
        rag_context: Optional[Dict] = None,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate manual with specified output format
        
        Args:
            videos: List of video info dicts with 'uri' and 'role' (expert/novice/single)
            output_format: Output format key (text_only, text_with_images, etc.)
            generation_config: Generation configuration
            rag_context: Optional RAG context for enhancement
            custom_prompt: Optional custom prompt override
            
        Returns:
            Generated manual data dict
        """
        
        # Validate format
        if not is_valid_format(output_format):
            logger.warning(f"Invalid format '{output_format}', using default")
            output_format = get_default_format()
        
        format_info = get_format_info(output_format)
        logger.info(f"Generating manual with format: {format_info['name']}")
        
        # Stage 1: Video Analysis (common for all formats)
        analysis = await self._analyze_videos(videos, generation_config, rag_context)
        
        # Stage 2: Format-specific processing
        result = {
            'output_format': output_format,
            'analysis': analysis,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        if output_format == 'text_only':
            result.update(await self._generate_text_manual(analysis, generation_config, custom_prompt))
        
        elif output_format == 'text_with_images':
            result.update(await self._generate_manual_with_images(
                videos, analysis, generation_config, custom_prompt
            ))
        
        elif output_format == 'text_with_video_clips':
            result.update(await self._generate_manual_with_clips(
                videos, analysis, generation_config, custom_prompt
            ))
        
        elif output_format == 'subtitle_video':
            result.update(await self._generate_subtitle_video(
                videos, analysis, generation_config
            ))
        
        elif output_format == 'hybrid':
            result.update(await self._generate_hybrid_manual(
                videos, analysis, generation_config, custom_prompt
            ))
        
        return result
    
    async def _analyze_videos(
        self,
        videos: List[Dict[str, str]],
        generation_config: Dict[str, Any],
        rag_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Analyze videos to extract work steps and insights
        
        Args:
            videos: List of video info dicts
            generation_config: Generation configuration
            rag_context: Optional RAG context
            
        Returns:
            Analysis result dict
        """
        logger.info(f"Analyzing {len(videos)} video(s)")
        
        # Determine analysis mode
        if len(videos) > 1:
            # Multiple videos: comparison analysis
            expert_video = next((v for v in videos if v.get('role') == 'expert'), None)
            novice_video = next((v for v in videos if v.get('role') == 'novice'), None)
            
            if expert_video and novice_video:
                analysis = await self.gemini_service.analyze_expert_novice_comparison(
                    expert_video_uri=expert_video['uri'],
                    novice_video_uri=novice_video['uri'],
                    context_documents=rag_context.get('reference_materials', []) if rag_context else []
                )
            else:
                # Fallback to single video analysis
                analysis = await self.gemini_service._analyze_single_video(
                    videos[0]['uri'],
                    skill_level='standard'
                )
        else:
            # Single video analysis
            analysis = await self.gemini_service._analyze_single_video(
                videos[0]['uri'],
                skill_level='standard'
            )
        
        return analysis
    
    async def _generate_text_manual(
        self,
        analysis: Dict[str, Any],
        generation_config: Dict[str, Any],
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate text-only manual
        
        Args:
            analysis: Video analysis result
            generation_config: Generation configuration
            custom_prompt: Optional custom prompt
            
        Returns:
            Manual content dict
        """
        logger.info("Generating text-only manual")
        
        # Get sections configuration with custom prompts
        sections_config = generation_config.get('sections', [])
        
        output_config = {
            "format": "detailed",
            "sections": sections_config if isinstance(sections_config, list) and len(sections_config) > 0 and isinstance(sections_config[0], str) else [
                "overview", "preparation", "steps", 
                "expert_tips", "safety", "quality", "troubleshooting"
            ],
            "sections_with_prompts": sections_config if isinstance(sections_config, list) and len(sections_config) > 0 and isinstance(sections_config[0], dict) else [],
            "content_length": generation_config.get('detail_level', 'normal'),
            "writing_style": generation_config.get('writing_style', 'formal'),
            "language": "ja",
            "include_comparisons": len(analysis.get('comparison', {})) > 0,
            "custom_prompt": custom_prompt,
            "template_description": generation_config.get('template_description', '')
        }
        
        # Debug logging - write to both logger and print for Celery
        logger.info(f"[PROMPT DEBUG] sections_config type: {type(sections_config)}")
        logger.info(f"[PROMPT DEBUG] sections_config length: {len(sections_config) if isinstance(sections_config, list) else 0}")
        logger.info(f"[PROMPT DEBUG] sections_with_prompts: {output_config['sections_with_prompts']}")
        logger.info(f"[PROMPT DEBUG] template_description: {output_config['template_description'][:100] if output_config['template_description'] else 'None'}")
        
        print(f"[PROMPT DEBUG] sections_config type: {type(sections_config)}")
        print(f"[PROMPT DEBUG] sections_with_prompts length: {len(output_config['sections_with_prompts'])}")
        print(f"[PROMPT DEBUG] Will trigger ReAct: {len(output_config['sections_with_prompts']) > 0}")
        
        content = await self.gemini_service.generate_comprehensive_manual(
            analysis_data=analysis,
            output_config=output_config
        )
        
        return {
            'content': content,
            'content_text': content,
            'content_html': self._convert_markdown_to_html(content),
            'analysis_result': analysis
        }
    
    async def _generate_manual_with_images(
        self,
        videos: List[Dict[str, str]],
        analysis: Dict[str, Any],
        generation_config: Dict[str, Any],
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate manual with image snapshots
        
        Args:
            videos: Video list
            analysis: Video analysis result
            generation_config: Generation configuration
            custom_prompt: Optional custom prompt
            
        Returns:
            Manual content dict with images
        """
        logger.info("Generating manual with images")
        
        # Extract key frames from video
        primary_video = videos[0]
        images = await self._extract_keyframes(primary_video['uri'], analysis)
        
        # Generate text content
        text_result = await self._generate_text_manual(analysis, generation_config, custom_prompt)
        
        # Insert images into content
        html_content = self._insert_images_into_html(text_result['content_html'], images)
        
        return {
            'content': html_content,
            'content_html': html_content,
            'content_text': text_result['content_text'],
            'extracted_images': images,
            'analysis_result': analysis
        }
    
    async def _generate_manual_with_clips(
        self,
        videos: List[Dict[str, str]],
        analysis: Dict[str, Any],
        generation_config: Dict[str, Any],
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate manual with video clips
        
        Args:
            videos: Video list
            analysis: Video analysis result
            generation_config: Generation configuration
            custom_prompt: Optional custom prompt
            
        Returns:
            Manual content dict with video clips
        """
        logger.info("Generating manual with video clips")
        
        # Extract video clips for each step
        primary_video = videos[0]
        clips = await self._extract_video_clips(primary_video['uri'], analysis)
        
        # Generate text content
        text_result = await self._generate_text_manual(analysis, generation_config, custom_prompt)
        
        # Insert video clips into content
        html_content = self._insert_video_clips_into_html(text_result['content_html'], clips)
        
        return {
            'content': html_content,
            'content_html': html_content,
            'content_text': text_result['content_text'],
            'video_clips': clips,
            'analysis_result': analysis
        }
    
    async def _generate_subtitle_video(
        self,
        videos: List[Dict[str, str]],
        analysis: Dict[str, Any],
        generation_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate subtitle data for video (video burning requires FFmpeg)
        
        Args:
            videos: Video list
            analysis: Video analysis result
            generation_config: Generation configuration
            
        Returns:
            Subtitle video info dict
        """
        logger.info("Generating subtitle data")
        
        try:
            # Try multiple paths to get work_steps
            work_steps = analysis.get('work_steps', [])
            
            # If not found, try arguments.steps (from function call response)
            if not work_steps and 'arguments' in analysis:
                work_steps = analysis['arguments'].get('steps', [])
            
            # If still not found, try expert_analysis or novice_analysis (for comparison mode)
            if not work_steps:
                if 'expert_analysis' in analysis:
                    work_steps = analysis['expert_analysis'].get('work_steps', [])
                    if not work_steps and 'arguments' in analysis['expert_analysis']:
                        work_steps = analysis['expert_analysis']['arguments'].get('steps', [])
            
            if not work_steps:
                logger.warning("No work steps found for subtitle generation")
                logger.warning(f"Analysis keys: {list(analysis.keys())}")
                return {
                    'content': '字幕データなし',
                    'content_video_uri': videos[0]['uri'] if videos else None,
                    'subtitles_data': []
                }
            
            # Generate subtitle entries (SRT/VTT format)
            subtitles = []
            
            for idx, step in enumerate(work_steps):
                start_time = step.get('start_time', idx * 10)
                end_time = step.get('end_time', start_time + 10)
                step_title = step.get('step_title', f'ステップ {idx+1}')
                description = step.get('step_description', '')
                
                # Combine title and description for subtitle text
                subtitle_text = f"{step_title}"
                if description:
                    subtitle_text += f": {description[:100]}"  # Limit length
                
                subtitles.append({
                    'index': idx + 1,
                    'start_time': start_time,
                    'end_time': end_time,
                    'text': subtitle_text,
                    'start_formatted': self._format_subtitle_time(start_time),
                    'end_formatted': self._format_subtitle_time(end_time)
                })
            
            # Generate SRT content
            srt_content = self._generate_srt_content(subtitles)
            
            logger.info(f"Generated {len(subtitles)} subtitle entries")
            logger.warning("Note: Video burning with subtitles requires FFmpeg (not yet implemented)")
            
            return {
                'content': f'字幕データ生成完了 ({len(subtitles)}件)\n\nFFmpegによる動画焼き込みは未実装です。',
                'content_video_uri': videos[0]['uri'] if videos else None,
                'subtitles_data': subtitles,
                'srt_content': srt_content,
                'analysis_result': analysis  # Include analysis for database storage
            }
            
        except Exception as e:
            logger.error(f"Subtitle generation failed: {e}")
            return {
                'content': f'字幕生成エラー: {str(e)}',
                'content_video_uri': videos[0]['uri'] if videos else None,
                'subtitles_data': []
            }
    
    def _format_subtitle_time(self, seconds: float) -> str:
        """Format time for SRT subtitles (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _generate_srt_content(self, subtitles: List[Dict[str, Any]]) -> str:
        """Generate SRT file content from subtitle data"""
        srt_lines = []
        
        for sub in subtitles:
            srt_lines.append(str(sub['index']))
            srt_lines.append(f"{sub['start_formatted']} --> {sub['end_formatted']}")
            srt_lines.append(sub['text'])
            srt_lines.append('')  # Blank line between entries
        
        return '\n'.join(srt_lines)
    
    async def _download_video_if_needed(self, video_uri: str) -> str:
        """Download video from GCS if needed, return local path"""
        if not video_uri.startswith('gs://'):
            return video_uri
        
        if not GCS_AVAILABLE:
            raise ImportError("google-cloud-storage is required for GCS video download")
        
        try:
            # Parse GCS URI
            bucket_name, blob_path = video_uri[5:].split('/', 1)
            
            # Download to temp file
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            suffix = os.path.splitext(blob_path)[1] or '.mp4'
            fd, temp_path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            
            blob.download_to_filename(temp_path)
            logger.info(f"Downloaded video from GCS: {video_uri} -> {temp_path}")
            
            return temp_path
            
        except Exception as e:
            logger.error(f"Failed to download video from GCS: {e}")
            raise
    
    async def _cleanup_temp_video(self, local_path: str, original_uri: str):
        """Clean up temporary video file if it was downloaded from GCS"""
        if original_uri.startswith('gs://') and os.path.exists(local_path):
            try:
                os.remove(local_path)
                logger.debug(f"Cleaned up temp video: {local_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp video: {e}")
    
    async def _generate_hybrid_manual(
        self,
        videos: List[Dict[str, str]],
        analysis: Dict[str, Any],
        generation_config: Dict[str, Any],
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate hybrid manual with multiple formats
        
        Args:
            videos: Video list
            analysis: Video analysis result
            generation_config: Generation configuration
            custom_prompt: Optional custom prompt
            
        Returns:
            Hybrid manual content dict
        """
        logger.info("Generating hybrid manual")
        
        # Generate all components
        text_result = await self._generate_text_manual(analysis, generation_config, custom_prompt)
        primary_video = videos[0]
        images = await self._extract_keyframes(primary_video['uri'], analysis)
        clips = await self._extract_video_clips(primary_video['uri'], analysis)
        
        # Combine into rich HTML
        html_content = self._create_hybrid_html(
            text_result['content_html'],
            images,
            clips
        )
        
        return {
            'content': html_content,
            'content_html': html_content,
            'content_text': text_result['content_text'],
            'extracted_images': images,
            'video_clips': clips,
            'analysis_result': analysis
        }
    
    async def _extract_keyframes(
        self,
        video_uri: str,
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract key frames from video based on analysis
        
        Args:
            video_uri: Video URI
            analysis: Analysis result with timing info
            
        Returns:
            List of extracted image info dicts
        """
        logger.info(f"Extracting keyframes from {video_uri}")
        
        # Check dependencies
        if not CV2_AVAILABLE:
            logger.error("opencv-python is required for keyframe extraction")
            return []
        
        if not NUMPY_AVAILABLE:
            logger.error("numpy is required for keyframe extraction")
            return []
        
        try:
            # Download video if GCS URI
            local_path = await self._download_video_if_needed(video_uri)
            
            # Extract frames based on work steps
            work_steps = analysis.get('work_steps', [])
            if not work_steps:
                logger.warning("No work steps found in analysis")
                return []
            
            cap = cv2.VideoCapture(local_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video: {video_uri}")
            
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            extracted_images = []
            
            for idx, step in enumerate(work_steps):
                # Get timestamp for this step (middle of duration if available)
                start_time = step.get('start_time', idx * 10)  # fallback
                end_time = step.get('end_time', start_time + 10)
                mid_time = (start_time + end_time) / 2
                
                # Calculate frame number
                frame_num = int(mid_time * fps)
                frame_num = min(frame_num, total_frames - 1)
                
                # Extract frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                
                if not ret:
                    logger.warning(f"Failed to extract frame at {mid_time}s")
                    continue
                
                # Encode to JPEG
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if not ret:
                    continue
                
                image_base64 = base64.b64encode(buffer).decode('utf-8')
                
                # Upload to GCS
                image_filename = f"keyframe_step_{idx+1}_{int(mid_time*1000)}.jpg"
                image_uri = await self.file_manager.upload_base64_image(
                    image_base64,
                    image_filename
                )
                
                extracted_images.append({
                    'step_number': idx + 1,
                    'step_title': step.get('step_title', f'Step {idx+1}'),
                    'timestamp': mid_time,
                    'timestamp_formatted': f"{int(mid_time//60):02d}:{int(mid_time%60):02d}",
                    'image_uri': image_uri,
                    'image_base64': image_base64
                })
            
            cap.release()
            logger.info(f"Extracted {len(extracted_images)} keyframes")
            
            # Cleanup temporary file if downloaded
            await self._cleanup_temp_video(local_path, video_uri)
            
            return extracted_images
            
        except Exception as e:
            logger.error(f"Keyframe extraction failed: {e}")
            return []
    
    async def _extract_video_clips(
        self,
        video_uri: str,
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract video clips for each work step
        
        Args:
            video_uri: Video URI
            analysis: Analysis result with timing info
            
        Returns:
            List of video clip info dicts
        """
        logger.info(f"Extracting video clips from {video_uri}")
        
        try:
            # Try multiple paths to get work_steps
            work_steps = analysis.get('work_steps', [])
            
            # If not found, try arguments.steps (from function call response)
            if not work_steps and 'arguments' in analysis:
                work_steps = analysis['arguments'].get('steps', [])
            
            # If still not found, try expert_analysis or novice_analysis (for comparison mode)
            if not work_steps:
                if 'expert_analysis' in analysis:
                    work_steps = analysis['expert_analysis'].get('work_steps', [])
                    if not work_steps and 'arguments' in analysis['expert_analysis']:
                        work_steps = analysis['expert_analysis']['arguments'].get('steps', [])
            
            if not work_steps:
                logger.warning("No work steps found for clip extraction")
                return []
            
            # For now, store clip metadata (start/end times)
            # Actual video splitting would require FFmpeg
            # Client can use video player with start/end times
            
            clips = []
            for idx, step in enumerate(work_steps):
                start_time = step.get('start_time', idx * 10)
                end_time = step.get('end_time', start_time + 10)
                
                clips.append({
                    'step_number': idx + 1,
                    'step_title': step.get('step_title', f'Step {idx+1}'),
                    'video_uri': video_uri,  # Reference original video
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': end_time - start_time,
                    'start_formatted': f"{int(start_time//60):02d}:{int(start_time%60):02d}",
                    'end_formatted': f"{int(end_time//60):02d}:{int(end_time%60):02d}"
                })
            
            logger.info(f"Generated {len(clips)} video clip references")
            return clips
            
        except Exception as e:
            logger.error(f"Video clip extraction failed: {e}")
            return []
    
    def _convert_markdown_to_html(self, markdown_text: str) -> str:
        """Convert markdown to HTML"""
        if MARKDOWN_AVAILABLE:
            try:
                # Use markdown library with extensions
                html = markdown.markdown(
                    markdown_text,
                    extensions=['extra', 'codehilite', 'tables', 'toc']
                )
                return html
            except Exception as e:
                logger.warning(f"markdown conversion failed: {e}, using fallback")
        else:
            logger.debug("Using fallback markdown conversion")
            # Simple fallback conversion
            html = markdown_text
            # Headers
            html = html.replace('\n#### ', '\n<h4>').replace('\n', '</h4>\n', 1)
            html = html.replace('\n### ', '\n<h3>').replace('\n', '</h3>\n', 1)
            html = html.replace('\n## ', '\n<h2>').replace('\n', '</h2>\n', 1)
            html = html.replace('\n# ', '\n<h1>').replace('\n', '</h1>\n', 1)
            # Bold and italic
            import re
            html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
            html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
            # Line breaks
            html = html.replace('\n\n', '</p>\n<p>').replace('\n', '<br>\n')
            html = f'<p>{html}</p>'
            return html
    
    def _insert_images_into_html(
        self,
        html_content: str,
        images: List[Dict[str, Any]]
    ) -> str:
        """Insert images into HTML content at appropriate locations"""
        if not images:
            return html_content
        
        try:
            # Insert images after step headings in the procedure section
            import re
            
            # First, find the procedure section (作業手順)
            procedure_patterns = [
                r'<h2[^>]*>.*?作業手順.*?</h2>',
                r'<h2[^>]*>.*?手順.*?</h2>',
                r'<h2[^>]*>.*?Procedure.*?</h2>',
                r'<h2[^>]*>.*?Steps.*?</h2>'
            ]
            
            procedure_start = -1
            for pattern in procedure_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    procedure_start = match.start()
                    logger.debug(f"Found procedure section at position {procedure_start}")
                    break
            
            if procedure_start == -1:
                logger.warning("Could not find procedure section (作業手順), inserting images after any matching heading")
                search_content = html_content
                search_offset = 0
            else:
                # Search only within procedure section and after
                search_content = html_content[procedure_start:]
                search_offset = procedure_start
            
            # Sort images by step_number to insert in correct order
            sorted_images = sorted(images, key=lambda x: x.get('step_number', 0), reverse=True)
            
            for img in sorted_images:
                step_num = img.get('step_number', 0)
                step_title = img.get('step_title', '')
                timestamp = img.get('timestamp_formatted', '')
                
                # Use base64 data URI for embedded images (works in browser without server routes)
                image_base64 = img.get('image_base64', '')
                if image_base64:
                    # Create data URI
                    image_src = f"data:image/jpeg;base64,{image_base64}"
                else:
                    # Fallback to GCS URI (may not work in browser without proxy)
                    image_src = img.get('image_uri', '')
                    logger.warning(f"No base64 data for step {step_num}, using GCS URI (may not display)")
                
                # Create image HTML with better styling
                img_html = f'''
                <div class="step-image" data-step="{step_num}" style="margin: 20px 0; text-align: center;">
                    <img src="{image_src}" alt="{step_title}" class="img-fluid" style="max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; padding: 5px;" />
                    <div class="image-caption" style="margin-top: 10px; font-size: 0.9em; color: #666;">
                        <strong>図{step_num}:</strong> {step_title} <span style="color: #999;">({timestamp})</span>
                    </div>
                </div>
                '''
                
                # Find step heading in procedure section
                # Match h3 tags with step number at the beginning (e.g., "1. ", "2. ", "3. ")
                pattern = rf'(<h3[^>]*>\s*{re.escape(str(step_num))}\.\s+.*?</h3>)'
                match = re.search(pattern, search_content, re.IGNORECASE)
                
                if match:
                    # Calculate absolute position in original content
                    insert_pos = search_offset + match.end()
                    html_content = (
                        html_content[:insert_pos] + 
                        img_html + 
                        html_content[insert_pos:]
                    )
                    logger.debug(f"Inserted image for step {step_num} at position {insert_pos}")
                    
                    # Update offsets for subsequent insertions (we're inserting in reverse order)
                    search_offset += len(img_html)
                else:
                    logger.warning(f"Could not find heading for step {step_num} in procedure section")
            
            return html_content
            
        except Exception as e:
            logger.error(f"Image insertion failed: {e}")
            return html_content
    
    def _insert_video_clips_into_html(
        self,
        html_content: str,
        clips: List[Dict[str, Any]]
    ) -> str:
        """Insert video clips into HTML content at appropriate locations"""
        if not clips:
            return html_content
        
        try:
            import re
            
            for clip in clips:
                step_num = clip.get('step_number', 0)
                step_title = clip.get('step_title', '')
                video_uri = clip.get('video_uri', '')
                start_time = clip.get('start_time', 0)
                end_time = clip.get('end_time', 0)
                start_fmt = clip.get('start_formatted', '')
                end_fmt = clip.get('end_formatted', '')
                
                # Create video player HTML with time range
                video_html = f'''
                <div class="step-video" data-step="{step_num}">
                    <video controls class="video-fluid" data-start="{start_time}" data-end="{end_time}">
                        <source src="{video_uri}#t={start_time},{end_time}" type="video/mp4">
                        お使いのブラウザは動画タグをサポートしていません。
                    </video>
                    <div class="video-caption">
                        動画{step_num}: {step_title} ({start_fmt} - {end_fmt})
                    </div>
                </div>
                '''
                
                # Find step heading and insert video after it
                pattern = rf'(<h[34][^>]*>.*?{re.escape(str(step_num))}.*?</h[34]>)'
                match = re.search(pattern, html_content, re.IGNORECASE)
                
                if match:
                    insert_pos = match.end()
                    html_content = (
                        html_content[:insert_pos] + 
                        video_html + 
                        html_content[insert_pos:]
                    )
                else:
                    logger.debug(f"Could not find heading for step {step_num}, appending video")
            
            return html_content
            
        except Exception as e:
            logger.error(f"Video clip insertion failed: {e}")
            return html_content
    
    def _create_hybrid_html(
        self,
        text_html: str,
        images: List[Dict[str, Any]],
        clips: List[Dict[str, Any]]
    ) -> str:
        """Create hybrid HTML with text, images, and video clips"""
        try:
            # First insert images
            html = self._insert_images_into_html(text_html, images)
            
            # Then insert video clips (after images)
            html = self._insert_video_clips_into_html(html, clips)
            
            # Add custom styling for hybrid content
            style = '''
            <style>
                .step-image, .step-video {
                    margin: 20px 0;
                    padding: 15px;
                    background: #f8f9fa;
                    border-radius: 8px;
                    border: 1px solid #e9ecef;
                }
                .step-image img, .step-video video {
                    max-width: 100%;
                    height: auto;
                    border-radius: 4px;
                }
                .image-caption, .video-caption {
                    margin-top: 10px;
                    font-size: 14px;
                    color: #666;
                    font-weight: 500;
                }
            </style>
            '''
            
            html = style + html
            
            return html
            
        except Exception as e:
            logger.error(f"Hybrid HTML generation failed: {e}")
            return text_html
