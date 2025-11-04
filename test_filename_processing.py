import sys
sys.path.append('/app')

from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import io
import uuid
import os

# テスト: secure_filename の動作
print("=== secure_filename Test ===")
test_filenames = [
    "test.mp4",
    "video file.mp4", 
    "my@video.mp4",
    "video.with.dots.mp4",
    "file_name.mp4",
    "normal-video.mp4"
]

for filename in test_filenames:
    secure_name = secure_filename(filename)
    print(f"Original: '{filename}' -> Secure: '{secure_name}'")

# テスト: 実際のファイル名生成ロジック
print("\n=== File Name Generation Test ===")
for filename in test_filenames:
    secure_name = secure_filename(filename)
    unique_filename = f"{uuid.uuid4()}_{secure_name}"
    print(f"Generated filename: {unique_filename}")

# テスト: ファイル拡張子の取得
print("\n=== File Extension Test ===")
for filename in test_filenames:
    secure_name = secure_filename(filename)
    ext = secure_name.lower().split('.')[-1] if '.' in secure_name else ''
    print(f"File: '{secure_name}' -> Extension: '{ext}'")