# SQLite データベースマイグレーション問題の解決

## 🔍 問題の概要

### 症状
- 画像編集機能で画像保存後にマニュアル詳細のデータが消失
- ローカル環境では正常動作するが、EC2本番環境で発生

### 根本原因
**EC2内のSQLiteデータベースでマイグレーションが未実行**のため、`manuals`テーブルに以下のカラムが存在しない：

- `description` - マニュアル説明文
- `stage1_content` - Stage1分析結果
- `stage2_content` - Stage2フレーム抽出結果  
- `stage3_content` - Stage3HTML生成結果
- `generation_status` - 生成ステータス
- `generation_progress` - 生成進捗
- `error_message` - エラーメッセージ

### 影響範囲
画像編集保存API (`/api/video-manual/three-stage/save-edited-image`) で以下の処理が失敗：
```python
# 存在しないカラムへの書き込みでSQLiteエラー
manual.stage2_content = json.dumps(stage2_result, ensure_ascii=False, indent=2)
manual.stage3_content = html_manual
db.session.commit()  # ← ここでエラー
```

## 🛠️ 解決策

### 1. 自動マイグレーション機能の実装

#### `migrate_unified.py` - 統合マイグレーションスクリプト
- 既存の2つのマイグレーション（description追加 + 画像機能フィールド追加）を統合
- マイグレーション前の自動バックアップ機能
- エラーハンドリングと詳細ログ出力

#### `app.py` の init_database() 修正  
- `db.create_all()` 実行後にマイグレーション自動実行
- 失敗時もアプリケーション継続（可用性重視）

### 2. 安全性の確保

#### 本番環境への配慮
- **EC2のファイルは一切編集しない**
- GitHub Actions経由でのみ変更適用
- マイグレーション前の自動バックアップ
- 既存マイグレーション適用済みの場合はスキップ

#### 段階的適用
1. **ローカルテスト**: migrate_unified.py の動作確認
2. **コンテナテスト**: docker build & run での確認  
3. **本番適用**: 次回GitHub Actionsデプロイで自動実行

### 3. 実装内容

#### ファイル変更
```
manual_generator/
├── migrate_unified.py        # 新規作成 - 統合マイグレーション
├── app.py                   # 修正 - 自動マイグレーション呼び出し
├── Dockerfile              # 修正 - 新ファイルのコピー追加
└── README_MIGRATION_FIX.md  # 本文書
```

#### Dockerfile更新
```dockerfile
# マイグレーションファイル追加
COPY migrate_add_description.py ./
COPY migrate_unified.py ./
```

#### app.py の init_database() 更新
```python
# データベーステーブル作成後にマイグレーション実行
db.create_all()
logger.info("データベーステーブルを作成しました")

# 新規追加: マイグレーション自動実行
try:
    from migrate_unified import run_migrations
    logger.info("データベースマイグレーションを実行します...")
    migration_success = run_migrations(db_path, logger)
    if migration_success:
        logger.info("✅ データベースマイグレーションが完了しました")
    else:
        logger.warning("⚠️ データベースマイグレーションで問題が発生しましたが、続行します")
except Exception as migration_error:
    logger.error(f"マイグレーション実行エラー: {migration_error}")
    # エラーでもアプリケーション継続
```

## 📋 適用手順

### 次回デプロイ時の自動実行
1. 本変更をmainブランチにマージ
2. GitHub Actionsが自動実行
3. EC2でコンテナ再起動時にマイグレーション自動実行
4. アプリケーション起動ログで成功確認

### ログ出力例（期待値）
```
INFO - Database path: /app/instance/manual_generator.db
INFO - データベーステーブルを作成しました
INFO - データベースマイグレーションを実行します...
INFO - 📋 マイグレーション前バックアップ作成: /app/instance/manual_generator.db.backup_before_migration
INFO - 既存のカラム: ['id', 'title', 'content', 'manual_type', 'company_id', 'created_by', 'created_at', 'updated_at']
INFO - Migration 1: description カラムを追加中...
INFO - ✅ description カラムが追加されました
INFO - Migration 2: stage1_content カラムを追加中...
INFO - ✅ stage1_content カラムが追加されました
INFO - Migration 2: stage2_content カラムを追加中...
INFO - ✅ stage2_content カラムが追加されました
INFO - Migration 2: stage3_content カラムを追加中...
INFO - ✅ stage3_content カラムが追加されました
INFO - Migration 2: generation_status カラムを追加中...
INFO - ✅ generation_status カラムが追加されました
INFO - Migration 2: generation_progress カラムを追加中...
INFO - ✅ generation_progress カラムが追加されました
INFO - Migration 2: error_message カラムを追加中...
INFO - ✅ error_message カラムが追加されました
INFO - 🎉 7個のマイグレーションが適用されました
INFO - マイグレーション後のカラム: ['id', 'title', 'description', 'content', 'manual_type', 'company_id', 'created_by', 'created_at', 'updated_at', 'stage1_content', 'stage2_content', 'stage3_content', 'generation_status', 'generation_progress', 'error_message']
INFO - ✅ データベースマイグレーションが完了しました
```

## 🎯 期待効果

### 即座の問題解決
- 画像編集機能での データ消失エラー解消
- `stage2_content`, `stage3_content` への正常な書き込み
- マニュアル詳細データの永続化

### 運用面の向上  
- 今後のマイグレーション自動化
- 本番環境への手動介入不要
- エラー時の自動バックアップ保全

## 📞 トラブルシューティング

### マイグレーション失敗時
1. **コンテナログ確認**: `sudo docker logs manual-generator`
2. **バックアップ確認**: `/app/instance/manual_generator.db.backup_before_migration`
3. **手動復旧**: 必要に応じてバックアップからの復元

### 既知の制限事項
- SQLiteの `ALTER TABLE` 制約（カラム削除・型変更不可）
- マイグレーション中の一時的な書き込みロック
- 大容量DBでのマイグレーション時間

## 🔄 今後の展開

### v2 改善案
- マイグレーションバージョン管理機能
- ロールバック機能の実装
- PostgreSQL対応時の適応

---

**作成日**: 2025年9月8日  
**対象バージョン**: manual_generator v1.0  
**適用環境**: EC2本番環境 (GitHub Actions経由)
