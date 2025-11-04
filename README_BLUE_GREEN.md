# Blue-Green デプロイ ガイド (Manual Generator)

## 目的
本番稼働中(Blue)を停止せずに新バージョン(Green)を並行起動・検証し、正常性確認後にカットオーバーすることで、デプロイ失敗時の停止時間とデータリスクを最小化します。

## 実装概要
`.github/workflows/deploy.yml` の `deploy` ジョブ内で `manual-changed == true` の場合:
1. 旧コンテナ (blue: `manual-generator` / ポート 8080) を動かしたまま新イメージをビルド
2. 一時コンテナ (green: `manual-generator-green` / ポート 8081) を起動
3. コンテナ稼働状態 & HTTP レスポンス確認
4. 必要なら SQLite シード (空の場合のみ)
5. Green 正常 → Blue 停止 & 削除 → `docker-compose up -d manual` で新サービスを 8080 に再構築
6. Compose サービス健康確認 (失敗時は Green イメージでロールバック)
7. Green 一時コンテナ破棄 / 後片付け

## ロールバック動作
- カットオーバー後のヘルスチェック失敗: 自動で Green イメージを `manual-generator` 名で再起動して終了コード 1。GitHub Actions は失敗を通知しつつサービスは利用可能。
- さらに手動ロールバックしたい場合: 過去の安定 commit を再度デプロイするか、S3 バックアップ DB を利用して任意再起動。

## 手動ロールバック手順 (緊急)
1. 安定版イメージ一覧:
```bash
docker images | grep manual-generator
```
2. 稼働確認:
```bash
docker ps | grep manual-generator
```
3. 強制再起動 (現行イメージ使用):
```bash
docker stop manual-generator || true
docker rm -f manual-generator || true
docker run -d \
  --name manual-generator \
  -p 8080:5000 \
  -e PORT=5000 \
  -e DATABASE_PATH=/app/instance/manual_generator.db \
  -v manual_instance:/app/instance \
  -v manual_logs:/app/logs \
  -v manual_uploads:/app/uploads \
  manual-generator:latest ./startup.sh
```
4. 特定タグへ戻したい場合 (例: sha):
```bash
docker run -d --name manual-generator ... manual-generator:<IMAGE_ID> ./startup.sh
```

## 注意点
- 一時的に 8081 を使用。ALB / SG で 8081 を公開する必要は無く、内部のみアクセス。
- 旧 Blue を早期に停止しないためコンテナ同時メモリ利用が一時増加する。メモリ余裕を確保。
- DB は共有 Volume (`manual_instance`) をマウント → Green 起動は “同じ” DB を参照する。移行スクリプトが破壊的な場合は別クローン volume 戦略を検討。

## 拡張余地
| 項目 | 説明 |
|------|------|
| Canary テスト | 追加 HTTP エンドポイント / 負荷シミュレーション |
| ヘルス詳細 | `/health` エンドポイント利用 (現在 root `/` をチェック) |
| 切替前差分検証 | DB マイグレーション dry-run, schema diff |
| Green 分離 Volume | 破壊的 migration 時に snapshot / clone volume を作成 |
| Slack 通知 | 成功 / 失敗 / ロールバックイベント通知 |

## 既知の制約
- 現在は docker-compose サービス再作成後に直接 HTTP ポート (8080) をポーリング。ALB 経由の外形監視追加は未実装。
- Blue 停止後に compose up 失敗し、且つ rollback ロジックも失敗した場合、手動介入が必要。

## 追加の安全策 (任意実装案)
1. Blue のログ・メトリクスを S3 / CloudWatch にスナップショット保存後に停止。
2. Green 起動時に `PRAGMA quick_check;` を追加実行し DB 健全性をログ化。
3. 切替直前に S3 バックアップを再取得 (二重化)。

---
Blue-Green デプロイに関する運用上の質問や拡張要望があればこのファイルに追記してください。
