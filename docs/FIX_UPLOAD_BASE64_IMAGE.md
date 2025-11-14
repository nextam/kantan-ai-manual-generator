# 画像抽出エラー修正レポート

## 発見されたエラー

### エラー1: `upload_base64_image`メソッドが存在しない
```
[2025-11-14 22:35:02,668: ERROR/MainProcess] Keyframe extraction failed: 
'FileManager' object has no attribute 'upload_base64_image'
```

### エラー2: 空の`extracted_images`
```
[2025-11-14 22:36:48,289: WARNING/MainProcess] ⚠️ No images extracted for manual 46.
Output format: text_with_images
```

## 根本原因

`UnifiedManualGenerator._extract_keyframes()`メソッドが、Base64エンコードされた画像をGCSにアップロードするために`FileManager.upload_base64_image()`を呼び出していましたが、このメソッドが実装されていませんでした。

## 実施した修正

### 修正1: `FileManager.upload_base64_image()`メソッドの追加

**ファイル**: `src/infrastructure/file_manager.py`

**場所**: `save_file()`メソッドの後に追加

```python
async def upload_base64_image(self, image_base64: str, filename: str, 
                               folder: str = 'keyframes', company_id: int = None) -> str:
    """
    Upload base64-encoded image to storage
    
    Args:
        image_base64: Base64-encoded image data (without data URI prefix)
        filename: Target filename
        folder: Storage folder (default: 'keyframes')
        company_id: Company ID for multi-tenant isolation
        
    Returns:
        GCS URI or file path of uploaded image
    """
    import base64
    import io
    
    try:
        # Decode base64 to binary
        image_data = base64.b64decode(image_base64)
        
        # Create file-like object
        image_file = io.BytesIO(image_data)
        
        # Upload using save_file
        result = self.save_file(
            file_obj=image_file,
            filename=filename,
            file_type='images',
            folder=folder,
            company_id=company_id
        )
        
        # Return GCS URI or file path
        if self.storage_type == 'gcs':
            return result['file_path']  # gs://bucket/path/to/file.jpg
        else:
            return result['file_path']
            
    except Exception as e:
        logger.error(f"Failed to upload base64 image {filename}: {e}")
        raise
```

**機能**:
- Base64文字列をバイナリにデコード
- `BytesIO`オブジェクトとしてラップ
- 既存の`save_file()`メソッドを使用してアップロード
- GCS URI（または ローカルパス）を返す

### テスト結果

**テストスクリプト**: `scripts/test_upload_base64_image.py`

```
✅ FileManager initialized
   Storage type: gcs
   Backend: GCSStorageBackend

✅ upload_base64_image method exists

📤 Testing upload...
   ✅ Upload successful!
   Image URI: test_keyframes/c6cab2b2-80a4-4f00-96ef-92afd009a70a_test_keyframe_1.png
   ✅ File exists in storage
```

## 修正後の動作フロー

```
1. マニュアル生成開始 (text_with_images)
   ↓
2. UnifiedManualGenerator._extract_keyframes()
   ↓
3. OpenCVで動画からフレーム抽出
   ↓
4. JPEGエンコード & Base64変換
   ↓
5. FileManager.upload_base64_image() ← ★修正箇所
   ↓ Base64 → Binary → BytesIO → save_file()
   ↓
6. GCSにアップロード
   ↓ GCS URI返却
   ↓
7. extracted_images配列に追加
   {
     'step_number': 1,
     'step_title': 'ステップ1',
     'timestamp': 5.2,
     'timestamp_formatted': '00:05',
     'image_uri': 'gs://bucket/keyframes/image.jpg', ← GCS URI
     'image_base64': '/9j/4AAQ...' ← Base64データ
   }
   ↓
8. Celeryタスクでextracted_imagesを取得
   ↓
9. Manual.set_extracted_images()で保存
   ↓
10. データベースに保存
   ↓
11. APIレスポンスで返却
   ↓
12. フロントエンドで画像表示
```

## 次のステップ

### 1. サーバー再起動（修正適用）

Flaskサーバーとceleryワーカーを再起動して修正を適用します。

### 2. 新規マニュアル生成

既存のマニュアル（ID: 46）は画像抽出が失敗したため、新しくマニュアルを生成してください：

1. http://localhost:5000 にアクセス
2. ログイン: `support@career-survival.com` / `0000`
3. 「新規マニュアル作成」
4. **出力形式: 「テキスト+画像」を選択**
5. 動画ファイルアップロード
6. 生成開始

### 3. ログ確認

生成中のログで以下を確認：
```
✅ [INFO] Extracting keyframes from gs://...
✅ [INFO] Extracted {N} keyframes
✅ [INFO] Found {N} images in 'extracted_images' field
✅ [INFO] Saved {N} extracted images for manual {ID}
```

エラーがなければ成功です。

### 4. 動作確認

```powershell
python scripts/test_text_with_images_workflow.py 2>$null
```

以下が表示されれば成功：
```
✅ Database has images: ✅ YES
✅ API returns images: ✅ YES
✅ Content has placeholders: ✅ YES (or ℹ️ NO)
```

## まとめ

### 修正内容
✅ `FileManager.upload_base64_image()`メソッドを実装
✅ Base64画像のGCSアップロード機能が動作

### 影響範囲
- ✅ `text_with_images`モードの画像抽出
- ✅ キーフレーム抽出機能
- ✅ すべての画像アップロード処理

### 確認事項
- [x] メソッドが実装されている
- [x] テストで動作確認済み
- [ ] 実際のマニュアル生成でテスト（次のステップ）

---

**注意**: 必ずサーバーとceleryワーカーを再起動してから、新規マニュアル生成でテストしてください。
