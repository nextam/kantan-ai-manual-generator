from werkzeug.utils import secure_filename
import uuid

def safe_filename_with_extension(filename):
    """ファイル名を安全に処理（拡張子を保持）"""
    secure_name = secure_filename(filename)
    
    # 拡張子を元のファイル名から取得
    original_ext = ''
    if '.' in filename:
        original_ext = '.' + filename.rsplit('.', 1)[1].lower()
    
    # secure_filenameが空の場合や拡張子が失われた場合の対処
    if not secure_name or secure_name == original_ext.lstrip('.'):
        # ファイル名の本体部分がない場合、generic nameを使用
        secure_name = f"file{original_ext}"
    elif not secure_name.endswith(original_ext) and original_ext:
        # 拡張子が失われた場合、再度追加
        if secure_name.endswith(original_ext.lstrip('.')):
            # 拡張子のドットが失われただけの場合
            secure_name = secure_name[:-len(original_ext.lstrip('.'))] + original_ext
        else:
            # 完全に拡張子が失われた場合
            secure_name += original_ext
    
    return f"{uuid.uuid4()}_{secure_name}"

# テスト
test_files = [
    "ピアスビス.mp4",
    "熟練者(スマホ).mp4", 
    "熟練者①.mp4",
    "非熟練者.mp4",
    "熟練者③.mp4",
    "normal_file.mp4",
    "test.MOV",
    "video.AVI"
]

print("修正されたファイル名生成のテスト:")
for filename in test_files:
    result = safe_filename_with_extension(filename)
    print(f"元: '{filename}' -> 修正後: '{result}'")