"""
File: video_optimizer.py
Purpose: Video optimization and compression service
Main functionality: Compress videos, optimize for web playback, progressive download support
Dependencies: FFmpeg
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class VideoOptimizer:
    """Video compression and optimization service"""
    
    # Preset configurations for different quality levels
    PRESETS = {
        '360p': {
            'resolution': '640:-2',
            'video_bitrate': '800k',
            'audio_bitrate': '96k',
            'crf': '28'
        },
        '720p': {
            'resolution': '1280:-2',
            'video_bitrate': '1500k',
            'audio_bitrate': '128k',
            'crf': '23'
        },
        '1080p': {
            'resolution': '1920:-2',
            'video_bitrate': '3000k',
            'audio_bitrate': '192k',
            'crf': '21'
        }
    }
    
    def __init__(self, ffmpeg_path: str = 'ffmpeg'):
        """
        Initialize VideoOptimizer
        
        Args:
            ffmpeg_path: Path to FFmpeg executable (default: 'ffmpeg' assumes in PATH)
        """
        self.ffmpeg_path = ffmpeg_path
        self._check_ffmpeg_availability()
    
    def _check_ffmpeg_availability(self) -> bool:
        """Check if FFmpeg is available"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"FFmpeg is available: {result.stdout.split()[0:3]}")
                return True
            else:
                logger.warning("FFmpeg check returned non-zero exit code")
                return False
        except FileNotFoundError:
            logger.error(f"FFmpeg not found at: {self.ffmpeg_path}")
            logger.error("Please install FFmpeg: https://ffmpeg.org/download.html")
            return False
        except Exception as e:
            logger.error(f"Error checking FFmpeg: {e}")
            return False
    
    def get_video_info(self, input_path: str) -> Optional[Dict]:
        """
        Get video metadata using FFprobe
        
        Args:
            input_path: Path to input video file
            
        Returns:
            Dictionary with video info (duration, resolution, bitrate, etc.)
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                input_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                # Extract video stream info
                video_stream = next(
                    (s for s in data.get('streams', []) if s.get('codec_type') == 'video'),
                    None
                )
                
                if video_stream:
                    return {
                        'duration': float(data.get('format', {}).get('duration', 0)),
                        'width': video_stream.get('width'),
                        'height': video_stream.get('height'),
                        'codec': video_stream.get('codec_name'),
                        'bitrate': int(data.get('format', {}).get('bit_rate', 0)),
                        'size': int(data.get('format', {}).get('size', 0))
                    }
            
            return None
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return None
    
    def optimize_video(
        self,
        input_path: str,
        output_path: str,
        quality: str = '720p',
        custom_settings: Optional[Dict] = None
    ) -> Dict:
        """
        Optimize video for web playback
        
        Compression settings:
        - Codec: H.264 (best compatibility)
        - Resolution: Based on quality preset (default: 720p)
        - Bitrate: Balanced quality/size
        - Frame rate: 30fps
        - Audio: AAC 128kbps
        - Progressive download: faststart flag enabled
        
        Args:
            input_path: Path to input video file
            output_path: Path to save optimized video
            quality: Quality preset ('360p', '720p', '1080p')
            custom_settings: Override default settings
            
        Returns:
            Dictionary with optimization results
        """
        if not os.path.exists(input_path):
            return {
                'success': False,
                'error': f'Input file not found: {input_path}'
            }
        
        # Get preset or use custom settings
        settings = self.PRESETS.get(quality, self.PRESETS['720p'])
        if custom_settings:
            settings.update(custom_settings)
        
        # Create output directory if needed
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Build FFmpeg command
        cmd = [
            self.ffmpeg_path,
            '-i', input_path,
            '-vf', f"scale={settings['resolution']}",  # Resolution
            '-c:v', 'libx264',                          # H.264 codec
            '-preset', 'medium',                        # Encoding speed/quality balance
            '-crf', settings['crf'],                    # Quality (lower = better)
            '-maxrate', settings['video_bitrate'],      # Max video bitrate
            '-bufsize', f"{int(settings['video_bitrate'].rstrip('k')) * 2}k",  # Buffer size
            '-r', '30',                                 # Frame rate
            '-c:a', 'aac',                              # Audio codec
            '-b:a', settings['audio_bitrate'],          # Audio bitrate
            '-movflags', '+faststart',                  # Progressive download support
            '-y',                                       # Overwrite without confirmation
            output_path
        ]
        
        logger.info(f"Optimizing video: {input_path} -> {output_path} (quality: {quality})")
        logger.debug(f"FFmpeg command: {' '.join(cmd)}")
        
        try:
            # Run FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr,
                    'command': ' '.join(cmd)
                }
            
            # Calculate compression results
            original_size = os.path.getsize(input_path)
            optimized_size = os.path.getsize(output_path)
            compression_ratio = (1 - optimized_size / original_size) * 100
            
            logger.info(f"Video optimized successfully: {compression_ratio:.1f}% size reduction")
            
            return {
                'success': True,
                'original_size': original_size,
                'optimized_size': optimized_size,
                'compression_ratio': f'{compression_ratio:.1f}%',
                'original_size_mb': f'{original_size / (1024 * 1024):.2f} MB',
                'optimized_size_mb': f'{optimized_size / (1024 * 1024):.2f} MB',
                'quality': quality,
                'output_path': output_path
            }
            
        except subprocess.TimeoutExpired:
            logger.error("Video optimization timed out (>10 minutes)")
            return {
                'success': False,
                'error': 'Optimization timed out after 10 minutes'
            }
        except Exception as e:
            logger.error(f"Video optimization failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def optimize_for_streaming(
        self,
        input_path: str,
        output_path: str
    ) -> Dict:
        """
        Optimize video specifically for streaming (fast start, lower latency)
        
        Args:
            input_path: Path to input video
            output_path: Path to output video
            
        Returns:
            Optimization results
        """
        custom_settings = {
            'crf': '23',
            'video_bitrate': '1200k'
        }
        
        return self.optimize_video(
            input_path,
            output_path,
            quality='720p',
            custom_settings=custom_settings
        )
