# SQLite バックアップ (S3 保存) ガイド

## 目的
本番 EC2 上の Manual Generator の SQLite データベース `manual_generator.db` を安全に世代管理し、S3 バケット `chuden-demoapp` にバックアップします。

## 構成概要
- データ本体: Docker Named Volume `manual_instance` 内 `/app/instance/manual_generator.db`
- バックアップ方式: ボリューム上の DB を一時コピー → gzip 圧縮 → ローカル退避 → S3 へアップロード
- 保存形式: `sqlite-backup/YYYY/MM/manual_generator_<timestamp>.db.gz` + `sqlite-backup/latest.db.gz`

## 追加ファイル
`infra/scripts/backup_sqlite_to_s3.sh`

## 事前要件
1. S3 バケット `chuden-demoapp` が存在する (リージョン: ap-northeast-1 など)
2. EC2 インスタンスに IAM Role (例: `ChudenDemoAppBackupRole`) をアタッチし以下の最小ポリシー付与:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject","s3:GetObject","s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::chuden-demoapp",
        "arn:aws:s3:::chuden-demoapp/sqlite-backup/*"
      ]
    }
  ]
}
```
3. EC2 に awscli v2 がインストール済み
4. Docker が稼働中 (既存アプリ運用中)

## 手動実行手順 (読み取りのみ)
SSH で EC2 に入り:
```bash
cd /opt/chuden-demoapp
chmod +x infra/scripts/backup_sqlite_to_s3.sh
./infra/scripts/backup_sqlite_to_s3.sh
```
成功例出力:
```
[sqlite-backup] Integrity: ok
[sqlite-backup] Compressed size: 123456 bytes
[sqlite-backup] Local saved: /opt/chuden-demoapp_backups/sqlite/manual_generator_20250908_120001.db.gz
[sqlite-backup] Uploaded to s3://chuden-demoapp/sqlite-backup/2025/09/manual_generator_20250908_120001.db.gz
[sqlite-backup] Updated latest marker
[sqlite-backup] Backup completed successfully
```

## 環境変数 (任意調整)
| 変数 | 既定値 | 説明 |
|------|--------|------|
| S3_BUCKET | chuden-demoapp | バックアップ先バケット |
| SQLITE_VOLUME_NAME | manual_instance | DB を含む Docker Volume 名 |
| DB_FILE_NAME | manual_generator.db | SQLite ファイル名 |
| RETAIN_LOCAL_DAYS | 7 | ローカル保持日数 (古い.gz を削除) |

例:
```bash
S3_BUCKET=chuden-demoapp ./infra/scripts/backup_sqlite_to_s3.sh
```

## Cron による自動化 (例: 毎時)
```bash
sudo crontab -e
# 追記
0 * * * * /opt/chuden-demoapp/infra/scripts/backup_sqlite_to_s3.sh >> /var/log/sqlite_backup.log 2>&1
```
ログ確認:
```bash
sudo tail -f /var/log/sqlite_backup.log
```

## systemd タイマー方式 (より管理しやすい)
1. ユニットファイル `/etc/systemd/system/sqlite-backup.service`:
```
[Unit]
Description=SQLite Backup to S3
After=docker.service

[Service]
Type=oneshot
Environment=S3_BUCKET=chuden-demoapp
WorkingDirectory=/opt/chuden-demoapp
ExecStart=/opt/chuden-demoapp/infra/scripts/backup_sqlite_to_s3.sh
```
2. タイマー `/etc/systemd/system/sqlite-backup.timer`:
```
[Unit]
Description=Run SQLite Backup hourly

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```
3. 有効化:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sqlite-backup.timer
systemctl list-timers | grep sqlite-backup
```

## 復元手順 (安全に停止して実施)
1. 対象ファイル選定:
```bash
aws s3 ls s3://chuden-demoapp/sqlite-backup/2025/09/
```
2. ダウンロード:
```bash
aws s3 cp s3://chuden-demoapp/sqlite-backup/2025/09/manual_generator_20250908_120001.db.gz /tmp/
cd /tmp && gunzip manual_generator_20250908_120001.db.gz
```
3. アプリ停止 (最小ダウンタイム):
```bash
cd /opt/chuden-demoapp
sudo docker-compose stop manual
```
4. Volume パス特定と置換:
```bash
VOL_PATH=$(sudo docker volume inspect manual_instance --format '{{ .Mountpoint }}')
sudo cp /tmp/manual_generator_20250908_120001.db "$VOL_PATH/manual_generator.db"
```
5. 再起動:
```bash
sudo docker-compose up -d manual
```
6. 整合性確認:
```bash
sudo docker exec manual-generator sqlite3 /app/instance/manual_generator.db 'PRAGMA integrity_check;'
```

## 整合性/健全性チェック
- スクリプトは `PRAGMA quick_check;` の結果をログに残す (ok / failed)
- 失敗ログが続く場合、復元かフルダンプ検討:
```bash
sqlite3 manual_generator.db '.dump' > dump.sql
```

## 注意点
- 稼働中 SQLite のホットコピーは通常安全だが、極端な高更新負荷時は `backup api` を使う方式も検討可能。
- 機密データが含まれる場合 S3 バケットはバージョニング + サーバーサイド暗号化(SSE-S3 もしくは KMS) 有効化推奨。
- バケットポリシーで外部アクセスを最小化。
- デプロイ先 `/opt/chuden-demoapp` は GitHub Actions の workflow 内で自動生成されるようになりました（消失しても次回デプロイで再作成）。手動作業で削除しない運用を推奨。
- `.env` ファイルは `.dockerignore` から除外され、リポジトリの最新内容がコンテナに取り込まれます。秘匿情報を直接置く場合は GitHub 公開リスクに注意し、必要なら `secrets` / SSM Parameter Store への移行を検討してください。

## 今後の拡張案
- S3 バージョニング + ライフサイクル: 30日後 IA, 180日後 Glacier
- 失敗通知: CloudWatch Events + SNS
- RDS (PostgreSQL) への段階的移行 (同時接続や集計需要増加時)
- 差分バックアップ（WAL 分離）で転送コスト削減
- 暗号化（KMS envelope）+ 復元検証自動ジョブ（週次）

---
このドキュメントは初期バージョンです。運用で得た知見を追記してください。
