# 404エラー修正レポート

## 発見されたエラー

### エラー1: 画像404エラー
```
GET http://localhost:5000/manual/view/keyframes/27c374e4-c0d0-4152-a266-b9a78521dc1a_keyframe_step_1_5000.jpg 404 (NOT FOUND)
GET http://localhost:5000/manual/view/keyframes/186f6aaa-ac71-4e68-98f7-01f8fb46754b_keyframe_step_2_15000.jpg 404 (NOT FOUND)
```

### エラー2: JavaScript未定義変数エラー
```
Failed to load formats: ReferenceError: formats is not defined
```

### エラー3: 要素不在（警告レベル）
```
user-info element not found
```

## 根本原因

### 原因1: HTMLに埋め込まれた画像が相対パス

`UnifiedManualGenerator._insert_images_into_html()`メソッドが、GCS URI（`gs://bucket/keyframes/image.jpg`）をそのまま`<img src>`に埋め込んでいました。

```html
<!-- 問題のあるHTML -->
<img src="keyframes/27c374e4-c0d0-4152-a266-b9a78521dc1a_keyframe_step_1_5000.jpg" />
```

ブラウザはこれを相対パスとして解釈し、`http://localhost:5000/manual/view/keyframes/...jpg`にアクセスしようとしますが、このルートは存在しません。

### 原因2: APIレスポンスの解析忘れ

`loadAvailableFormats()`関数で、`fetch()`でAPIを呼び出していましたが、レスポンスを`response.json()`でパースして`formats`変数に格納する処理が抜けていました。

## 実施した修正

### 修正1: Base64データURIを使用

**ファイル**: `src/services/unified_manual_generator.py`

**場所**: `_insert_images_into_html()`メソッド

```python
# 修正前
image_uri = img.get('image_uri', '')  # GCS URI
img_html = f'<img src="{image_uri}" ... />'

# 修正後
image_base64 = img.get('image_base64', '')
if image_base64:
    # Base64データURIを使用（ブラウザで直接表示可能）
    image_src = f"data:image/jpeg;base64,{image_base64}"
else:
    # フォールバック
    image_src = img.get('image_uri', '')
    logger.warning(f"No base64 data for step {step_num}")

img_html = f'<img src="{image_src}" ... />'
```

**メリット**:
- ✅ サーバー側のルート不要（Base64データがHTML内に埋め込まれる）
- ✅ 404エラーが発生しない
- ✅ オフラインでも表示可能

**デメリット**:
- HTMLファイルサイズが増加（画像1枚あたり数百KB）
- データベースのサイズも増加

### 修正2: APIレスポンスの正しい解析

**ファイル**: `src/templates/manual_detail.html`

**場所**: `loadAvailableFormats()`関数

```javascript
// 修正前
const response = await fetch('/api/manuals/output-formats', ...);
formatButtons.innerHTML = formats.map(format => { // ❌ formats未定義

// 修正後
const response = await fetch('/api/manuals/output-formats', ...);
if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
}
const data = await response.json();  // ✅ レスポンスをパース
const formats = data.formats || [];  // ✅ formatsを取得
formatButtons.innerHTML = formats.map(format => {
```

## 修正後の動作フロー

### 画像表示の流れ

```
1. マニュアル生成 (text_with_images)
   ↓
2. UnifiedManualGenerator._extract_keyframes()
   - OpenCVでフレーム抽出
   - JPEGエンコード
   - Base64変換
   - GCSにアップロード（バックアップ）
   ↓ extracted_images配列に追加
   {
     'image_uri': 'gs://bucket/keyframes/image.jpg',  # GCS URI
     'image_base64': '/9j/4AAQ...'  # ← Base64データ
   }
   ↓
3. UnifiedManualGenerator._insert_images_into_html()
   ↓ Base64 → Data URI変換
   <img src="data:image/jpeg;base64,/9j/4AAQ..." />
   ↓
4. HTMLに埋め込み
   ↓
5. データベースに保存
   ↓
6. ブラウザで表示
   ✅ Data URIなので404エラーなし
```

### フォーマット切り替えの流れ

```
1. ページロード
   ↓
2. loadAvailableFormats()実行
   ↓
3. /api/manuals/output-formatsにリクエスト
   ↓
4. レスポンス取得
   ↓
5. response.json()でパース ← ★修正箇所
   ↓
6. formats配列を取得
   ↓
7. フォーマットボタンを動的生成
   ✅ ReferenceErrorなし
```

## 次のステップ

### 1. サーバー再起動

修正を適用するため、サーバーとceleryワーカーを再起動します：

```powershell
# VS Code タスク: "すべてのPythonプロセスを強制終了"
# VS Code タスク: "🚀 クリーンサーバー起動（ワンステップ）"
```

### 2. 新規マニュアル生成

既存のマニュアル（ID: 47）はHTMLに相対パスが埋め込まれているため、新しくマニュアルを生成してください。

### 3. 動作確認

新規マニュアル生成後、以下を確認：

1. **画像表示**:
   - ✅ 画像が正常に表示される
   - ✅ 404エラーが発生しない
   - ✅ ブラウザの開発者ツールで`<img src="data:image/jpeg;base64,..."`となっている

2. **JavaScriptエラー**:
   - ✅ `formats is not defined`エラーが発生しない
   - ✅ フォーマット切り替えボタンが表示される

3. **警告**:
   - ⚠️ `user-info element not found`は継続（影響なし）

### 4. ブラウザ開発者ツールで確認

```
F12 → Network タブ
- 画像リクエストが0件（Data URIなのでリクエスト不要）
- 404エラーが0件

F12 → Console タブ
- ReferenceError: formats is not defined → 解消
- user-info element not found → 警告のみ（無視可）
```

## まとめ

### 修正内容
✅ HTMLに埋め込む画像をBase64データURIに変更（`_insert_images_into_html`）
✅ APIレスポンスの正しい解析処理を追加（`loadAvailableFormats`）

### 影響範囲
- ✅ `text_with_images`モードの画像表示
- ✅ フォーマット切り替え機能

### 確認事項
- [x] 画像表示の404エラー修正
- [x] JavaScript未定義変数エラー修正
- [ ] 新規マニュアル生成でテスト（次のステップ）

---

**注意**: 既存のマニュアル（ID: 47）は修正前に生成されたため、HTMLに相対パスが埋め込まれています。新しくマニュアルを生成すると、Base64データURIが使用されます。
