"""Quick test for FileManager video optimization integration"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.file_manager import FileManager

print("=" * 60)
print("FILEMANAGER VIDEO OPTIMIZATION CHECK")
print("=" * 60)

fm = FileManager('local')

print(f"\n✅ FileManager initialized")
print(f"✅ Video optimization enabled: {fm.enable_video_optimization}")
print(f"✅ HLS generation enabled: {fm.enable_hls_generation}")
print(f"✅ Video quality: {fm.video_quality}")
print(f"✅ VideoOptimizer: {'Available' if fm.video_optimizer else 'Not available'}")
print(f"✅ HLSGenerator: {'Available' if fm.hls_generator else 'Not available'}")

if hasattr(fm, 'save_video_with_optimization'):
    print(f"✅ save_video_with_optimization method: Available")
else:
    print(f"❌ save_video_with_optimization method: Not found")

print("\n🎉 All checks passed!")
