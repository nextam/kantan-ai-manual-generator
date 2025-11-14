# リンク検証レポート

## 実行日時
2025-11-14 08:53

## 検証結果サマリー
- **有効なリンク**: 66
- **無効なリンク**: 33
- **検証したテンプレート**: 21

## 修正済みの問題

### 1. company_dashboard.html
✅ クイックアクションのリンクを修正
- `/manual/create` → `/manuals/create` (新しい統合版)
- `/templates` → `/company/templates`
- `/users` → `/company/users`

✅ クイックリンクを修正
- `/manuals` → `/manual/list`
- `/templates` → `/company/templates`
- `/users` → `/company/users`
- 未実装機能（翻訳、PDF、活動ログ、設定）を無効化

### 2. company_templates.html
✅ テンプレート作成・編集をAPI呼び出しに変更
- `createTemplate()`: promptでフォーム表示 → POST /api/company/templates
- `editTemplate()`: promptでフォーム表示 → PUT /api/company/templates/{id}

### 3. company_routes.py
✅ `/api/company/templates/<id>/set-default` エンドポイントを追加

### 4. company_routes.py (preview)
✅ テンプレートプレビューをHTML表示に変更
- JSONレスポンス → `render_template('template_preview.html')`

### 5. template_preview.html
✅ 新規作成 - テンプレートプレビュー用HTML

### 6. ui_routes.py
✅ Super adminダッシュボードルートを追加
- `/super-admin/dashboard` → `render_template('super_admin_dashboard.html')`

### 7. materials.html
✅ バックリンクを修正
- `/dashboard` → `/manual/list`

## 残存する問題

### 1. /api/jobs ルート (重要度: 中)
**影響範囲**: `jobs.html`
**原因**: Celeryがインストールされていないため、job_routesの登録に失敗
**状態**: 
```python
# src/core/app.py:1770
try:
    from src.api.job_routes import job_bp
    app.register_blueprint(job_bp)
except Exception as e:
    logger.warning(f"Failed to register job routes: {e}")
```

**推奨対応**:
1. Celeryをインストール: `pip install celery redis`
2. または、jobs.htmlでエラーハンドリングを改善

### 2. Staticファイル (重要度: 低)
**影響範囲**: 複数のテンプレート
**問題のファイル**:
- `/static/icons/favicon.ico`
- `/static/icons/favicon-16x16.png`
- `/static/icons/favicon-32x32.png`
- `/static/icons/favicon-48x48.png`
- `/static/icons/favicon-64x64.png`
- `/static/icons/apple-touch-icon.png`

**状態**: これらはFlaskの静的ファイル配信で自動処理されるため、ルート登録不要
**対応**: 不要（正常動作）

### 3. Jinja2変数 in URL (重要度: 低)
**影響範囲**: `manual_detail.html`
**問題のリンク**: `/api/manuals/{{ manual.id }}/convert`
**状態**: Jinja2テンプレート変数が展開されるため、実際のリクエストでは正常に動作
**対応**: 不要（false positive）

## 全リンク一覧

### 有効なリンク (66個)
1. `/auth/status` - 認証状態確認
2. `/login` - ログイン画面
3. `/api/company/dashboard` - 企業ダッシュボードAPI
4. `/company/templates` - テンプレート管理
5. `/company/users` - ユーザー管理
6. `/manual/list` - マニュアル一覧
7. `/manuals/create` - マニュアル作成（統合版）
8. `/materials` - 学習資料管理
9. `/api/company/templates` - テンプレートAPI
10. `/api/company/users` - ユーザーAPI
11. `/manual/create` - マニュアル作成（旧版）
12. `/upload` - ファイルアップロード
13. `/api/manuals/generate` - マニュアル生成API
14. `/api/manuals/output-formats` - 出力形式API
15. `/api/manuals/upload-file` - ファイルアップロードAPI
16. `/api/video-manual/three-stage/*` - 動画マニュアルAPI
... (その他51個)

### 無効なリンク (要確認)
1. `/api/jobs` - Celery依存、登録失敗
2. `/static/icons/*` - 静的ファイル（問題なし）
3. `/api/manuals/{{ manual.id }}/convert` - Jinja2変数（問題なし）

## 推奨される次のアクション

### 優先度: 高
- [ ] Celeryのインストールと設定確認

### 優先度: 中
- [ ] jobs.htmlのエラーハンドリング改善
- [ ] 未実装機能のUIを完全に無効化（または実装）

### 優先度: 低
- [ ] 旧バージョンのマニュアル作成画面を非推奨として明示

## テスト方法

各修正後、ブラウザで以下を確認：

1. **企業ダッシュボード**: http://localhost:5000/company/dashboard
   - すべてのクイックアクションボタンをクリック
   - すべてのクイックリンクをクリック

2. **テンプレート管理**: http://localhost:5000/company/templates
   - プレビューボタン → 新しいウィンドウでHTML表示
   - デフォルト設定ボタン → 成功メッセージ
   - 編集ボタン → prompt表示 → API呼び出し
   - 削除ボタン → 確認ダイアログ → API呼び出し

3. **ユーザー管理**: http://localhost:5000/company/users
   - ユーザー作成ボタン → prompt表示 → API呼び出し
   - 編集ボタン → role変更prompt → API呼び出し
   - 削除ボタン → 確認ダイアログ → API呼び出し

4. **サイドバー**:
   - Super adminでログイン → すべてのメニュー項目をクリック
   - 企業管理者でログイン → すべてのメニュー項目をクリック
   - 一般ユーザーでログイン → すべてのメニュー項目をクリック
