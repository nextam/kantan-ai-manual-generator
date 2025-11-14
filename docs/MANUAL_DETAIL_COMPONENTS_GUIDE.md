# マニュアル詳細ページ コンポーネント実装ガイド

## 概要

マニュアル詳細ページの機能を保守性の高いコンポーネントベースアーキテクチャに分割しました。

## ファイル構成

### JavaScript Components

#### 1. `static/js/video_display.js`
- **目的**: 動画表示と動画クリップ再生機能
- **機能**:
  - 元動画の表示
  - 動画クリップの時間範囲指定再生
  - `text_with_video_clips` フォーマット対応
  - 動画タイムスタンプ管理

**主要メソッド**:
- `displayVideos(videos, manualType, outputFormat)` - 元動画を表示
- `displayVideoClips(clips, sourceVideoUrl)` - 動画クリップセクションを生成
- `playClip(clipId, startTime, endTime)` - 特定区間を再生
- `setupClipHandlers()` - クリップ再生の自動ループ設定

#### 2. `static/js/image_editor.js`
- **目的**: 抽出画像の回転編集機能
- **機能**:
  - 画像の90度回転（左/右）
  - 回転状態の保存
  - サーバーとの同期

**主要メソッド**:
- `init(manual)` - 画像エディター初期化
- `addRotationControls()` - 回転ボタンを各画像に追加
- `rotateImage(stepNumber, delta)` - 画像を回転
- `saveRotationToServer(stepNumber, rotation)` - 回転をサーバーに保存
- `loadRotationStates()` - 保存された回転を復元

#### 3. `static/js/manual_display.js`
- **目的**: マニュアルコンテンツの表示とタブ管理
- **機能**:
  - マルチステージマニュアル表示
  - 単一マニュアル表示
  - Markdown/HTMLレンダリング
  - タブ切り替え

**主要メソッド**:
- `displayManual(manual)` - メイン表示ロジック
- `displayMultiStageManual(manual)` - マルチステージ表示
- `displaySingleManual(manual)` - 単一マニュアル表示
- `displayContent(content, elementId)` - コンテンツレンダリング
- `setupTabSwitching()` - タブイベント設定

### CSS Styles

#### `static/css/manual_detail_components.css`
- 動画クリップグリッドレイアウト
- 画像回転コントロールスタイル
- レスポンシブデザイン
- アニメーションとトランジション

### API Endpoints

#### `POST /api/manuals/image/rotate`
画像の回転状態を保存

**リクエスト**:
```json
{
  "manual_id": 123,
  "step_number": 1,
  "rotation": 90
}
```

**レスポンス**:
```json
{
  "success": true,
  "message": "Image rotation saved",
  "rotation": 90,
  "step_number": 1
}
```

## 使用方法

### 1. HTMLでのインクルード

`manual_detail.html`の`extra_styles`ブロック:
```html
{% block extra_styles %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/manual_detail_components.css') }}">
```

`extra_scripts`ブロック:
```html
{% block extra_scripts %}
<script src="{{ url_for('static', filename='js/video_display.js') }}"></script>
<script src="{{ url_for('static', filename='js/image_editor.js') }}"></script>
<script src="{{ url_for('static', filename='js/manual_display.js') }}"></script>
```

### 2. コンポーネントの初期化

```javascript
// マニュアル読み込み時
async function loadManual(manualId) {
    const response = await fetch(`/api/manual/${manualId}`);
    const result = await response.json();
    
    if (result.success) {
        // コンポーネント初期化
        videoDisplay.init();
        
        // マニュアル表示
        manualDisplay.displayManual(result.manual);
    }
}
```

### 3. 動画クリップ機能の使用

動画クリップは `output_format` が `text_with_video_clips` の場合に自動表示されます:

```javascript
// manual.video_clips データ形式
[
  {
    "step_number": 1,
    "step_title": "部品の確認",
    "start_time": 10.5,
    "end_time": 25.3,
    "duration": 14.8,
    "video_uri": "gs://bucket/video.mp4"
  }
]
```

### 4. 画像編集機能の使用

画像編集は `output_format` が `text_with_images` または `hybrid` の場合に自動有効化:

```javascript
// manual.extracted_images データ形式
[
  {
    "step_number": 1,
    "step_title": "ステップ1",
    "image": "data:image/jpeg;base64,...",
    "timestamp": 10.5,
    "rotation": 90  // 保存された回転角度
  }
]
```

## データフロー

### 動画クリップ表示
```
Manual Data (video_clips)
  ↓
videoDisplay.displayVideoClips()
  ↓
HTML生成 (video-clips-grid)
  ↓
setupClipHandlers()
  ↓
ユーザーが再生 → 時間範囲内でループ
```

### 画像回転
```
User clicks rotate button
  ↓
imageEditor.rotateImage()
  ↓
Apply CSS transform (visual)
  ↓
saveRotationToServer()
  ↓
POST /api/manuals/image/rotate
  ↓
DB更新 (extracted_images JSON)
```

## レスポンシブ対応

- **動画クリップ**: モバイルでは1カラム表示
- **回転コントロール**: モバイルでは常に表示
- **タブ**: 小画面でも適切に表示

## エラーハンドリング

各コンポーネントは以下のエラーを適切に処理します:

- ネットワークエラー
- データ形式エラー
- DOM要素の欠落
- API通信エラー

エラーはコンソールログに記録され、ユーザーにはわかりやすいメッセージを表示します。

## デバッグ

### コンソールログ

各コンポーネントは詳細なログを出力:

```javascript
console.log('displayVideoClips:', { clips, sourceVideoUrl });
console.log('Rotating image:', { stepNumber, delta });
console.log('Content displayed in', elementId);
```

### ブラウザ開発ツール

1. **Elements**: DOM構造の確認
2. **Console**: エラーログとデバッグ情報
3. **Network**: API通信の監視

## 今後の拡張

### 推奨される追加機能

1. **画像トリミング**: `imageEditor`に切り抜き機能を追加
2. **動画アノテーション**: 動画クリップにマーカーを追加
3. **一括回転**: 複数画像の一括回転
4. **プレビューモード**: 編集前のプレビュー

## トラブルシューティング

### 問題: 動画クリップが表示されない

**確認事項**:
- `manual.video_clips` が配列であること
- `manual.output_format` が `text_with_video_clips` であること
- 動画URLが有効であること

### 問題: 画像回転が保存されない

**確認事項**:
- APIエンドポイント `/api/manuals/image/rotate` が登録されていること
- 認証トークンが有効であること
- `manual.extracted_images` が正しい形式であること

### 問題: スタイルが適用されない

**確認事項**:
- CSSファイルのパスが正しいこと
- `url_for('static', ...)` が正しく動作していること
- ブラウザキャッシュをクリア

## まとめ

このコンポーネントベースのアーキテクチャにより:

✅ コードの再利用性が向上
✅ 保守性が改善
✅ テストが容易
✅ 機能の独立性が確保

各コンポーネントは独立して動作し、必要に応じて簡単に拡張・修正が可能です。
