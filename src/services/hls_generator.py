"""
File: hls_generator.py
Purpose: HLS (HTTP Live Streaming) video generation service
Main functionality: Convert videos to HLS format with multiple quality levels, adaptive bitrate streaming
Dependencies: FFmpeg
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class HLSGenerator:
    """HLS video generation service for adaptive streaming"""
    
    # HLS quality presets
    QUALITY_LEVELS = {
        '360p': {
            'resolution': '640:360',
            'video_bitrate': '800k',
            'audio_bitrate': '96k',
            'name': '360p'
        },
        '480p': {
            'resolution': '854:480',
            'video_bitrate': '1200k',
            'audio_bitrate': '128k',
            'name': '480p'
        },
        '720p': {
            'resolution': '1280:720',
            'video_bitrate': '2500k',
            'audio_bitrate': '128k',
            'name': '720p'
        },
        '1080p': {
            'resolution': '1920:1080',
            'video_bitrate': '5000k',
            'audio_bitrate': '192k',
            'name': '1080p'
        }
    }
    
    def __init__(self, ffmpeg_path: str = 'ffmpeg', segment_duration: int = 6):
        """
        Initialize HLSGenerator
        
        Args:
            ffmpeg_path: Path to FFmpeg executable
            segment_duration: Duration of each HLS segment in seconds (default: 6)
        """
        self.ffmpeg_path = ffmpeg_path
        self.segment_duration = segment_duration
        self._check_ffmpeg_availability()
    
    def _check_ffmpeg_availability(self) -> bool:
        """Check if FFmpeg is available and supports HLS"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("FFmpeg is available for HLS generation")
                return True
            return False
        except Exception as e:
            logger.error(f"FFmpeg not available: {e}")
            return False
    
    def generate_hls(
        self,
        input_path: str,
        output_dir: str,
        quality_levels: Optional[List[str]] = None,
        base_filename: str = 'video'
    ) -> Dict:
        """
        Generate HLS streams with multiple quality levels
        
        Creates:
        - Multiple quality variants (360p, 720p, etc.)
        - Segmented .ts files for each quality
        - Individual playlist .m3u8 for each quality
        - Master playlist.m3u8 for adaptive streaming
        
        Args:
            input_path: Path to input video file
            output_dir: Directory to save HLS files
            quality_levels: List of quality levels to generate (default: ['360p', '720p'])
            base_filename: Base name for output files (default: 'video')
            
        Returns:
            Dictionary with generation results
        """
        if not os.path.exists(input_path):
            return {
                'success': False,
                'error': f'Input file not found: {input_path}'
            }
        
        # Default quality levels
        if quality_levels is None:
            quality_levels = ['360p', '720p']
        
        # Validate quality levels
        invalid_levels = [q for q in quality_levels if q not in self.QUALITY_LEVELS]
        if invalid_levels:
            return {
                'success': False,
                'error': f'Invalid quality levels: {invalid_levels}'
            }
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Generating HLS streams: {input_path} -> {output_dir}")
        logger.info(f"Quality levels: {quality_levels}")
        
        # Generate each quality level
        generated_variants = []
        
        for quality in quality_levels:
            result = self._generate_quality_variant(
                input_path,
                output_dir,
                quality,
                base_filename
            )
            
            if result['success']:
                generated_variants.append(result)
            else:
                logger.error(f"Failed to generate {quality} variant: {result.get('error')}")
        
        if not generated_variants:
            return {
                'success': False,
                'error': 'Failed to generate any HLS variants'
            }
        
        # Generate master playlist
        master_playlist_path = output_path / 'master.m3u8'
        self._generate_master_playlist(generated_variants, str(master_playlist_path))
        
        return {
            'success': True,
            'master_playlist': str(master_playlist_path),
            'variants': generated_variants,
            'output_dir': output_dir,
            'quality_levels': quality_levels
        }
    
    def _generate_quality_variant(
        self,
        input_path: str,
        output_dir: str,
        quality: str,
        base_filename: str
    ) -> Dict:
        """
        Generate HLS variant for specific quality level
        
        Args:
            input_path: Input video path
            output_dir: Output directory
            quality: Quality level ('360p', '720p', etc.)
            base_filename: Base filename
            
        Returns:
            Dictionary with variant generation results
        """
        settings = self.QUALITY_LEVELS[quality]
        
        # Output paths
        playlist_filename = f"{base_filename}_{quality}.m3u8"
        segment_pattern = f"{base_filename}_{quality}_%03d.ts"
        
        playlist_path = Path(output_dir) / playlist_filename
        segment_path = Path(output_dir) / segment_pattern
        
        # FFmpeg command for HLS generation
        cmd = [
            self.ffmpeg_path,
            '-i', input_path,
            '-vf', f"scale={settings['resolution']}",
            '-c:v', 'libx264',
            '-b:v', settings['video_bitrate'],
            '-maxrate', settings['video_bitrate'],
            '-bufsize', f"{int(settings['video_bitrate'].rstrip('k')) * 2}k",
            '-preset', 'medium',
            '-g', '48',  # GOP size (2 seconds at 24fps)
            '-sc_threshold', '0',  # Disable scene change detection
            '-c:a', 'aac',
            '-b:a', settings['audio_bitrate'],
            '-ar', '48000',
            '-f', 'hls',
            '-hls_time', str(self.segment_duration),
            '-hls_list_size', '0',  # Keep all segments in playlist
            '-hls_segment_filename', str(segment_path),
            '-hls_flags', 'independent_segments',
            str(playlist_path)
        ]
        
        logger.info(f"Generating {quality} variant...")
        logger.debug(f"Command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error for {quality}: {result.stderr}")
                return {
                    'success': False,
                    'quality': quality,
                    'error': result.stderr
                }
            
            # Count generated segments
            segment_files = list(Path(output_dir).glob(f"{base_filename}_{quality}_*.ts"))
            
            logger.info(f"{quality} variant generated: {len(segment_files)} segments")
            
            return {
                'success': True,
                'quality': quality,
                'playlist': playlist_filename,
                'resolution': settings['resolution'],
                'video_bitrate': settings['video_bitrate'],
                'audio_bitrate': settings['audio_bitrate'],
                'segments': len(segment_files),
                'bandwidth': self._calculate_bandwidth(settings['video_bitrate'], settings['audio_bitrate'])
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"{quality} variant generation timed out")
            return {
                'success': False,
                'quality': quality,
                'error': 'Generation timed out'
            }
        except Exception as e:
            logger.error(f"Error generating {quality} variant: {e}")
            return {
                'success': False,
                'quality': quality,
                'error': str(e)
            }
    
    def _calculate_bandwidth(self, video_bitrate: str, audio_bitrate: str) -> int:
        """
        Calculate total bandwidth in bits per second
        
        Args:
            video_bitrate: Video bitrate (e.g., '800k', '2500k')
            audio_bitrate: Audio bitrate (e.g., '96k', '128k')
            
        Returns:
            Total bandwidth in bps
        """
        def parse_bitrate(bitrate_str: str) -> int:
            """Parse bitrate string to integer (bps)"""
            value = int(bitrate_str.rstrip('kKmM'))
            if bitrate_str.lower().endswith('k'):
                return value * 1000
            elif bitrate_str.lower().endswith('m'):
                return value * 1000000
            return value
        
        return parse_bitrate(video_bitrate) + parse_bitrate(audio_bitrate)
    
    def _generate_master_playlist(
        self,
        variants: List[Dict],
        output_path: str
    ) -> None:
        """
        Generate master playlist file for adaptive streaming
        
        Args:
            variants: List of generated variants
            output_path: Path to master playlist file
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('#EXTM3U\n')
            f.write('#EXT-X-VERSION:3\n\n')
            
            # Sort variants by bandwidth (lowest first)
            sorted_variants = sorted(variants, key=lambda v: v['bandwidth'])
            
            for variant in sorted_variants:
                width, height = variant['resolution'].split(':')
                
                # Write stream info
                f.write(f"#EXT-X-STREAM-INF:")
                f.write(f"BANDWIDTH={variant['bandwidth']},")
                f.write(f"RESOLUTION={width}x{height},")
                f.write(f"NAME=\"{variant['quality']}\"\n")
                f.write(f"{variant['playlist']}\n\n")
        
        logger.info(f"Master playlist generated: {output_path}")
    
    def generate_single_quality_hls(
        self,
        input_path: str,
        output_dir: str,
        quality: str = '720p',
        base_filename: str = 'video'
    ) -> Dict:
        """
        Generate HLS for a single quality level (simplified)
        
        Args:
            input_path: Input video path
            output_dir: Output directory
            quality: Quality level (default: '720p')
            base_filename: Base filename
            
        Returns:
            Generation results
        """
        return self.generate_hls(
            input_path,
            output_dir,
            quality_levels=[quality],
            base_filename=base_filename
        )
