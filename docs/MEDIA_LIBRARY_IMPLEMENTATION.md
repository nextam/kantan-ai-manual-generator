# Media Library Implementation Guide

## 📋 実装概要

このドキュメントは、WordPressライクなメディアライブラリシステムの実装ガイドです。

## ✅ 完了した実装

### Backend (完了)
1. **データベーススキーマ** (`src/models/models.py`)
   - `Media` モデル追加
   - テナント分離 (company_id)
   - GCS URI管理
   - メタデータ管理

2. **MediaManager サービス** (`src/services/media_manager.py`)
   - GCS統合
   - アップロード機能
   - 動画フレームキャプチャ
   - テナント分離の徹底

3. **Media API** (`src/api/media_routes.py`)
   - GET /api/media/library - メディア一覧取得
   - POST /api/media/upload - アップロード
   - POST /api/media/capture-frame - フレームキャプチャ
   - GET /api/media/<id> - 詳細取得
   - PUT /api/media/<id> - 更新
   - DELETE /api/media/<id> - 削除
   - GET /api/media/stats - 統計情報

4. **マイグレーションスクリプト** (`scripts/migrate_add_media_table.py`)

## 🚧 残りの実装タスク

### Frontend Components

#### 1. Media Library JavaScript (`src/static/js/media_library.js`)
```javascript
/**
 * MediaLibrary - 再利用可能なメディアライブラリコンポーネント
 * 
 * 使用方法:
 * MediaLibrary.open({
 *   mode: 'select',  // 'select' or 'manage'
 *   mediaType: 'image',  // 'image', 'video', or null for all
 *   onSelect: (media) => { console.log('Selected:', media); }
 * });
 */
class MediaLibrary {
    constructor() {
        this.currentPage = 1;
        this.perPage = 20;
        this.selectedMedia = null;
        this.config = {};
    }

    // 主要メソッド:
    // - open(config)
    // - close()
    // - loadMedia(page)
    // - search()
    // - applyFilters()
    // - selectMedia()
    // - showMediaDetails(mediaId)
    // - updateMediaDetails()
    // - deleteMedia()
    // - openUploadDialog()
    // - uploadFile()
    // - openCaptureDialog()
    // - captureCurrentFrame()
    // - editMedia() // 画像編集モーダルを開く
}
```

#### 2. Media Library CSS (`src/components/media_library/media_library.css`)
- モーダルスタイリング
- グリッドレイアウト
- レスポンシブ対応
- アニメーション

#### 3. Image Editor Integration (`src/static/js/image_editor_standalone.js`)
既存の `image_editor.js` を再利用可能にモジュール化:
- テキスト追加
- 図形描画
- 回転・トリミング
- フィルター適用
- GCS保存連携

### Integration

#### 1. Manual Edit Page (`src/templates/manual_edit.html`)
```javascript
// TinyMCEとの統合
tinymce.init({
    selector: '#editor',
    plugins: 'image media',
    file_picker_callback: function(callback, value, meta) {
        if (meta.filetype === 'image') {
            MediaLibrary.open({
                mode: 'select',
                mediaType: 'image',
                onSelect: (media) => {
                    callback(media.signed_url, {
                        alt: media.alt_text,
                        title: media.title
                    });
                }
            });
        }
    },
    // 画像クリック時にメディアライブラリで編集
    setup: function(editor) {
        editor.on('click', function(e) {
            if (e.target.tagName === 'IMG') {
                const imgSrc = e.target.src;
                MediaLibrary.openForEdit(imgSrc);
            }
        });
    }
});
```

#### 2. Manual Create Page (`src/templates/manual_create.html`)
```html
<!-- 動画選択をメディアライブラリ経由に変更 -->
<button type="button" onclick="selectVideoFromLibrary()">
    <span class="material-icons">video_library</span>
    メディアライブラリから選択
</button>
<button type="button" onclick="uploadNewVideo()">
    <span class="material-icons">upload</span>
    新規動画をアップロード
</button>
```

#### 3. Manual Detail Page Cleanup (`src/templates/manual_detail.html`)
削除する機能:
- `openImageEditMode()` ボタン
- `openRecaptureModal()` ボタン
- 画像編集関連のインラインコード

残す機能:
- マニュアル表示
- 編集画面へのリンク

## 📝 実装手順

### Phase 1: Core Components (優先度: 高)
1. ✅ Backend API実装 (完了)
2. ✅ MediaManager実装 (完了)
3. ✅ Database migration (完了)
4. 🔄 Media Library Modal HTML (完了)
5. ⏳ Media Library JavaScript
6. ⏳ Media Library CSS

### Phase 2: Image Editor Integration (優先度: 高)
1. ⏳ image_editor.js のモジュール化
2. ⏳ MediaLibraryとの統合
3. ⏳ GCS保存機能

### Phase 3: Page Integration (優先度: 中)
1. ⏳ Manual Edit画面統合
2. ⏳ Manual Create画面統合
3. ⏳ Manual Detail画面クリーンアップ

### Phase 4: Testing & Refinement (優先度: 中)
1. ⏳ テナント分離テスト
2. ⏳ GCS連携テスト
3. ⏳ UI/UXテスト
4. ⏳ エラーハンドリング

## 🔧 設定とデプロイ

### 1. APIルート登録
`src/core/app.py` に追加:
```python
from src.api.media_routes import media_bp
app.register_blueprint(media_bp)
```

### 2. マイグレーション実行
```bash
python scripts/migrate_add_media_table.py
```

### 3. 環境変数確認
```bash
# 必須
GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-credentials.json
GCS_BUCKET_NAME=kantan-ai-manual-generator
PROJECT_ID=kantan-ai-database
```

## 🔒 セキュリティ要件

### テナント分離の徹底
- すべてのメディアクエリに `company_id` フィルタ必須
- MediaManager の `_enforce_tenant_isolation()` による検証
- API Routes での current_user.company_id チェック

### GCS アクセス制御
- Signed URLで一時アクセス許可
- Company別のフォルダ分離: `company_{company_id}/media/`
- Service Account 権限の最小化

### ファイルアップロード制限
- ファイルサイズ制限
- MIMEタイプ検証
- ファイル名のサニタイズ

## 🎯 次のステップ

1. **JavaScript実装** - `media_library.js` の完全実装
2. **CSS実装** - WordPressライクなスタイリング
3. **Image Editor統合** - 既存コンポーネントの再利用化
4. **TinyMCE統合** - 編集画面での画像選択・編集
5. **テスト実行** - 全機能の動作確認

## 📚 参考資料

- WordPress Media Library UI/UX
- TinyMCE File Picker API
- Google Cloud Storage Signed URLs
- Flask-SQLAlchemy Models
