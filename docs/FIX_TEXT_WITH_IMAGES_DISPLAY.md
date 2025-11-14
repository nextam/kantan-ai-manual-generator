# テキスト+画像モード 画像表示修正レポート

## 問題の原因

テキスト+画像モードでマニュアル生成した際、画像が表示されない問題が発生していました。

### 根本原因の分析

1. **データベースの状態**:
   - `Manual.extracted_images`フィールドが`None`（空）
   - APIレスポンスで`extracted_images: Array(0)`

2. **データフロー**:
   ```
   UnifiedManualGenerator.generate_manual()
   ↓
   _generate_manual_with_images()
   ↓ 返り値: {'content': ..., 'extracted_images': [...], ...}
   ↓
   Celery Task (manual_tasks.py)
   ↓ 画像データの抽出・保存 ← ★ここで失敗
   ↓
   Manual.set_extracted_images() ← 呼ばれない
   ↓
   Database: extracted_images = None
   ```

3. **構造の不一致**:
   - `UnifiedManualGenerator`が返す画像構造:
     ```python
     {
       'step_number': 1,
       'step_title': 'ステップ1',
       'timestamp': 5.2,
       'timestamp_formatted': '00:05',
       'image_uri': 'gs://...',  # GCS URI
       'image_base64': 'iVBORw...'  # Base64データ
     }
     ```
   
   - Celeryタスクが探していた構造 (旧仕様):
     ```python
     analysis['steps'][0]['frame_data']['image_base64']
     ```

## 修正内容

### 1. Celeryタスクの画像抽出ロジック修正

**ファイル**: `src/workers/manual_tasks.py`

**変更内容**:
- `UnifiedManualGenerator`が返す`extracted_images`フィールドを直接取得
- 優先順位付き抽出ロジック:
  1. **優先**: `manual_content_result['extracted_images']` (text_with_imagesモード)
  2. **フォールバック**: `analysis.steps.frame_data` (レガシー互換性)

```python
# PRIORITY 1: Check if extracted_images is directly in the result
if isinstance(manual_content_result, dict):
    if 'extracted_images' in manual_content_result:
        raw_images = manual_content_result['extracted_images']
        if raw_images and isinstance(raw_images, list):
            extracted_images = []
            for img in raw_images:
                image_entry = {
                    'step_number': img.get('step_number'),
                    'step_title': img.get('step_title'),
                    'timestamp': img.get('timestamp', 0),
                    'timestamp_formatted': img.get('timestamp_formatted'),
                    'gcs_uri': img.get('image_uri'),  # GCS URI
                    'image': f"data:image/jpeg;base64,{img['image_base64']}" if 'image_base64' in img else None,
                    'filename': img.get('filename')
                }
                extracted_images.append(image_entry)
```

**改善点**:
- ✅ `UnifiedManualGenerator`の出力構造に合わせた
- ✅ GCS URIとBase64の両方を保存 (バックエンド/フロントエンド対応)
- ✅ フォールバックロジックでレガシーコードとの互換性維持
- ✅ 詳細なログ出力でデバッグしやすく

### 2. 検証スクリプト作成

**ファイル**: `scripts/test_text_with_images_workflow.py`

マニュアル生成の全フローを検証するスクリプト:
- データベースの`extracted_images`フィールド確認
- JSON解析テスト
- APIレスポンス確認
- コンテンツ内のプレースホルダー確認

## 修正後のテスト手順

### 1. 既存マニュアルの確認

```powershell
python scripts/check_images_simple.py 2>$null
```

現在の最新マニュアルの画像データ状態を確認します。

### 2. 新しいマニュアル生成 (推奨)

修正を適用するには、**新しくマニュアルを生成**する必要があります：

1. **ブラウザで操作**:
   - http://localhost:5000 にアクセス
   - ログイン: `support@career-survival.com` / `0000`
   - 「新規マニュアル作成」
   - **出力形式**: 「テキスト+画像」を選択
   - 動画ファイルをアップロード
   - 生成開始

2. **生成完了後、確認**:
   ```powershell
   python scripts/test_text_with_images_workflow.py 2>$null
   ```

### 3. 動作確認

生成完了後、以下を確認:
- ✅ データベースに`extracted_images`が保存されている
- ✅ APIレスポンスに画像データが含まれる
- ✅ ブラウザで画像が表示される

## 既存マニュアルについて

**重要**: 既存のマニュアル (ID: 45など) は、画像抽出が実行されなかったため、修正後も画像データは含まれません。

以下の選択肢があります:

### オプション1: 再生成 (推奨)
同じ動画で新しくマニュアルを生成すると、修正が適用されます。

### オプション2: 手動で画像を再抽出 (高度)
データベースに保存されている動画URIから、画像を再抽出して既存マニュアルに追加するスクリプトを作成できます。

## 技術的詳細

### 画像データのフロー

```
1. 動画アップロード
   ↓
2. UnifiedManualGenerator._extract_keyframes()
   - OpenCVで動画からフレーム抽出
   - Base64エンコード
   - GCSにアップロード
   ↓
3. 返り値に'extracted_images'含める
   ↓
4. Celeryタスク
   - manual_content_result['extracted_images']を取得 ← ★修正箇所
   - Manual.set_extracted_images()を呼ぶ
   ↓
5. データベース保存
   - extracted_images (JSON string)
   ↓
6. API応答
   - Manual.to_dict() → extracted_images配列
   ↓
7. フロントエンド表示
   - displayManualImages()で画像表示
```

### データ構造

**データベース** (`Manual.extracted_images`):
```json
[
  {
    "step_number": 1,
    "step_title": "部品とネジを準備する",
    "timestamp": 5.2,
    "timestamp_formatted": "00:05",
    "gcs_uri": "gs://bucket/image1.jpg",
    "image": "data:image/jpeg;base64,/9j/4AAQ...",
    "filename": "keyframe_step_1_5200.jpg"
  }
]
```

**APIレスポンス**:
```json
{
  "id": 46,
  "title": "新しいマニュアル",
  "output_format": "text_with_images",
  "extracted_images": [
    {
      "step_number": 1,
      "step_title": "部品とネジを準備する",
      "timestamp": 5.2,
      "timestamp_formatted": "00:05",
      "gcs_uri": "gs://bucket/image1.jpg",
      "image": "data:image/jpeg;base64,/9j/4AAQ...",
      "filename": "keyframe_step_1_5200.jpg"
    }
  ]
}
```

## まとめ

### 修正内容
✅ Celeryタスクの画像抽出ロジックを`UnifiedManualGenerator`の出力に合わせて修正

### 影響範囲
- ✅ `text_with_images`モード: 修正適用
- ✅ その他のモード: 影響なし (フォールバックロジックで互換性維持)

### 次のアクション
1. サーバー再起動 (修正適用)
2. 新しいマニュアル生成でテスト
3. 画像が正常に表示されることを確認

---

**注意**: Celeryワーカーが動作していない場合、マニュアル生成は`pending`状態のままになります。ローカル開発環境では、Celeryワーカーを別途起動する必要があります。
