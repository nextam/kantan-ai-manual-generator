"""
Test script for video optimization and HLS generation

This script tests:
1. VideoOptimizer - Video compression and optimization
2. HLSGenerator - HLS playlist generation with multiple qualities
3. File size reduction and quality metrics

Usage:
    python scripts/test_video_optimization.py <input_video_path>

Example:
    python scripts/test_video_optimization.py uploads/test_video.mp4
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.video_optimizer import VideoOptimizer
from src.services.hls_generator import HLSGenerator


def format_size(bytes_size):
    """Format byte size to human-readable string"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


def test_video_optimization(input_video):
    """Test video optimization"""
    print("=" * 60)
    print("VIDEO OPTIMIZATION TEST")
    print("=" * 60)
    
    if not os.path.exists(input_video):
        print(f"Error: Input video not found: {input_video}")
        return False
    
    # Create output directory
    output_dir = Path('scripts/test_output')
    output_dir.mkdir(exist_ok=True)
    
    # Initialize optimizer
    optimizer = VideoOptimizer()
    
    # Get video info
    print("\n1. Analyzing input video...")
    video_info = optimizer.get_video_info(input_video)
    if video_info:
        print(f"   Resolution: {video_info['width']}x{video_info['height']}")
        print(f"   Duration: {video_info['duration']:.1f}s")
        print(f"   Codec: {video_info['codec']}")
        print(f"   Bitrate: {video_info['bitrate'] / 1000:.0f} kbps")
        print(f"   Size: {format_size(video_info['size'])}")
    else:
        print("   Warning: Could not get video info")
    
    # Test different quality levels
    quality_levels = ['360p', '720p']
    
    for quality in quality_levels:
        print(f"\n2. Optimizing to {quality}...")
        output_path = output_dir / f"optimized_{quality}.mp4"
        
        result = optimizer.optimize_video(
            input_video,
            str(output_path),
            quality=quality
        )
        
        if result['success']:
            print(f"   ✅ Success!")
            print(f"   Original: {result['original_size_mb']}")
            print(f"   Optimized: {result['optimized_size_mb']}")
            print(f"   Reduction: {result['compression_ratio']}")
            print(f"   Output: {output_path}")
        else:
            print(f"   ❌ Failed: {result.get('error')}")
            return False
    
    print("\n✅ Video optimization test completed successfully!")
    return True


def test_hls_generation(input_video):
    """Test HLS generation"""
    print("\n" + "=" * 60)
    print("HLS GENERATION TEST")
    print("=" * 60)
    
    if not os.path.exists(input_video):
        print(f"Error: Input video not found: {input_video}")
        return False
    
    # Create output directory
    output_dir = Path('scripts/test_output/hls')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize generator
    generator = HLSGenerator()
    
    print("\n1. Generating HLS streams...")
    print("   Quality levels: 360p, 720p")
    
    result = generator.generate_hls(
        input_video,
        str(output_dir),
        quality_levels=['360p', '720p'],
        base_filename='test_video'
    )
    
    if result['success']:
        print(f"   ✅ Success!")
        print(f"   Master playlist: {result['master_playlist']}")
        print(f"   Variants generated: {len(result['variants'])}")
        
        for variant in result['variants']:
            print(f"\n   - {variant['quality']}:")
            print(f"     Resolution: {variant['resolution']}")
            print(f"     Video bitrate: {variant['video_bitrate']}")
            print(f"     Audio bitrate: {variant['audio_bitrate']}")
            print(f"     Segments: {variant['segments']}")
            print(f"     Playlist: {variant['playlist']}")
        
        # List all generated files
        hls_files = list(output_dir.rglob('*'))
        print(f"\n   Total files generated: {len(hls_files)}")
        
        print("\n✅ HLS generation test completed successfully!")
        return True
    else:
        print(f"   ❌ Failed: {result.get('error')}")
        return False


def main():
    """Main test function"""
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_video_optimization.py <input_video_path>")
        print("\nExample:")
        print("  python scripts/test_video_optimization.py uploads/test_video.mp4")
        sys.exit(1)
    
    input_video = sys.argv[1]
    
    print("VIDEO OPTIMIZATION AND HLS GENERATION TEST")
    print(f"Input video: {input_video}")
    print()
    
    # Test 1: Video Optimization
    optimization_success = test_video_optimization(input_video)
    
    # Test 2: HLS Generation
    hls_success = test_hls_generation(input_video)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Video Optimization: {'✅ PASS' if optimization_success else '❌ FAIL'}")
    print(f"HLS Generation: {'✅ PASS' if hls_success else '❌ FAIL'}")
    
    if optimization_success and hls_success:
        print("\n🎉 All tests passed!")
        print("\nNext steps:")
        print("1. Check test_output/ directory for generated files")
        print("2. Test HLS playback in browser using master.m3u8")
        print("3. Deploy to production environment")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
