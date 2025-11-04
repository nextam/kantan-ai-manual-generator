#!/usr/bin/env bash
# SQLiteバックアップ -> S3 アップロードスクリプト
# 用途: manual_generator の Docker named volume(manual_instance) 内SQLiteを安全に取得し S3 へバージョン付き保管
# 前提:
#  - EC2 インスタンスに awscli v2 インストール済み
#  - インスタンスロール / 認証情報で 's3:PutObject','s3:ListBucket' 権限あり
#  - バケット: $S3_BUCKET (存在すること)
#  - docker / sqlite3 利用可能
#  - 読み取りのみ (データ改変なし)
#
# 推奨 IAM ポリシー例:
# {
#   "Version": "2012-10-17",
#   "Statement": [
#     {"Effect":"Allow","Action":["s3:PutObject","s3:GetObject","s3:ListBucket"],"Resource":["arn:aws:s3:::kantan-ai-manual-generator","arn:aws:s3:::kantan-ai-manual-generator/sqlite-backup/*"]}
#   ]
# }
#
# 使い方(手動):
#   chmod +x infra/scripts/backup_sqlite_to_s3.sh
#   ./infra/scripts/backup_sqlite_to_s3.sh
# 環境変数で調整可能:
#   S3_BUCKET=kantan-ai-manual-generator
#   SQLITE_VOLUME_NAME=manual_instance
#   DB_FILE_NAME=manual_generator.db
#   RETAIN_LOCAL_DAYS=7
set -euo pipefail

S3_BUCKET="${S3_BUCKET:-kantan-ai-manual-generator}"
SQLITE_VOLUME_NAME="${SQLITE_VOLUME_NAME:-manual_instance}"
DB_FILE_NAME="${DB_FILE_NAME:-manual_generator.db}"
RETAIN_LOCAL_DAYS="${RETAIN_LOCAL_DAYS:-7}"
DATE_STAMP=$(date +%Y%m%d_%H%M%S)
WORK_DIR="/tmp/sqlite_backup"
LOCAL_ARCHIVE_DIR="/opt/kantan-ai-manual-generator_backups/sqlite"
LOG_PREFIX="[sqlite-backup]"

log(){ echo "${LOG_PREFIX} $1"; }
err(){ echo "${LOG_PREFIX} ERROR: $1" >&2; }

command -v aws >/dev/null || { err "aws CLI が見つかりません"; exit 1; }
command -v docker >/dev/null || { err "docker が見つかりません"; exit 1; }
if ! command -v sqlite3 >/dev/null; then
  log "sqlite3 コマンドが見つかりません (integrity チェックをスキップします)"
  SQLITE3_AVAILABLE=false
else
  SQLITE3_AVAILABLE=true
fi

mkdir -p "$WORK_DIR" "$LOCAL_ARCHIVE_DIR"

# volume のマウントポイントを取得
VOL_PATH=$(docker volume inspect "$SQLITE_VOLUME_NAME" --format '{{ .Mountpoint }}' 2>/dev/null || true)
if [ -z "$VOL_PATH" ]; then
  err "Volume $SQLITE_VOLUME_NAME が見つかりません"
  exit 2
fi
DB_PATH="$VOL_PATH/$DB_FILE_NAME"
if [ ! -f "$DB_PATH" ]; then
  err "DB ファイルが見つかりません: $DB_PATH"
  exit 3
fi

# SQLite 整合性チェック (失敗してもバックアップは継続: ファイル確保を優先)
if [ "$SQLITE3_AVAILABLE" = true ]; then
  INTEGRITY_RESULT=$(sqlite3 "$DB_PATH" 'PRAGMA quick_check;' 2>/dev/null || echo "quick_check_failed") || true
  log "Integrity: $INTEGRITY_RESULT"
else
  log "Integrity: skipped (sqlite3 not installed)"
fi

# 安全な一時コピー (稼働中でもクラッシュしないよう cp)
TMP_COPY="$WORK_DIR/${DB_FILE_NAME%.db}_$DATE_STAMP.db"
cp -p "$DB_PATH" "$TMP_COPY"

# 追加で圧縮 (サイズ削減) ※任意
GZ_PATH="$TMP_COPY.gz"
gzip -c "$TMP_COPY" > "$GZ_PATH"
SIZE_BYTES=$(stat -c%s "$GZ_PATH" 2>/dev/null || stat -f%z "$GZ_PATH")
log "Compressed size: ${SIZE_BYTES} bytes"

# ローカル退避
FINAL_LOCAL="$LOCAL_ARCHIVE_DIR/${DB_FILE_NAME%.db}_$DATE_STAMP.db.gz"
mv "$GZ_PATH" "$FINAL_LOCAL"
log "Local saved: $FINAL_LOCAL"

# S3 パス (日付プレフィックス + 年/月)
S3_KEY_DIR="sqlite-backup/$(date +%Y)/$(date +%m)"
S3_KEY="$S3_KEY_DIR/${DB_FILE_NAME%.db}_$DATE_STAMP.db.gz"

# アップロード
aws s3 cp "$FINAL_LOCAL" "s3://$S3_BUCKET/$S3_KEY" --only-show-errors
log "Uploaded to s3://$S3_BUCKET/$S3_KEY"

# 最新へのコピー (上書き) で簡易参照: latest.db.gz
aws s3 cp "$FINAL_LOCAL" "s3://$S3_BUCKET/sqlite-backup/latest.db.gz" --only-show-errors || true
log "Updated latest marker"

# ローカル世代整理
find "$LOCAL_ARCHIVE_DIR" -type f -name '*.db.gz' -mtime +"$RETAIN_LOCAL_DAYS" -print -delete || true

log "Backup completed successfully"
