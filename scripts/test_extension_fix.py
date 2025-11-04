#!/usr/bin/env python3
from utils.path_normalization import fix_mp4_extension
print("Extension fix test:")
print(f"'video/test_mp4' -> '{fix_mp4_extension('video/test_mp4')}'")
print(f"'video/cf7657db-dddf-4465-92de-3e31c452dbde_mp4' -> '{fix_mp4_extension('video/cf7657db-dddf-4465-92de-3e31c452dbde_mp4')}'")