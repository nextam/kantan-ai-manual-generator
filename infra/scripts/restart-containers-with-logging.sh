#!/bin/bash
# CloudWatch Logsドライバーでコンテナを起動するスクリプト

set -e

HOST_BASE="/home/ec2-user"
MANUAL_HOST_DIR="$HOST_BASE/manual_generator"
ANALYSIS_HOST_DIR="$HOST_BASE/operation_analysis"

echo "Preparing host directories..."
mkdir -p "$MANUAL_HOST_DIR/logs" "$MANUAL_HOST_DIR/instance" "$MANUAL_HOST_DIR/uploads" || true
mkdir -p "$ANALYSIS_HOST_DIR/logs" "$ANALYSIS_HOST_DIR/results" || true

# Backup existing SQLite DB from container to host volume (one-time migration)
if docker ps -a --format '{{.Names}}' | grep -q '^manual-generator$'; then
  echo "Found existing manual-generator container. Attempting to back up SQLite to host before removal..."
  if docker exec manual-generator test -f /app/instance/manual_generator.db; then
    echo "Copying /app/instance/manual_generator.db -> $MANUAL_HOST_DIR/instance/manual_generator.db"
    docker cp manual-generator:/app/instance/manual_generator.db "$MANUAL_HOST_DIR/instance/manual_generator.db" || true
  else
    echo "No SQLite file found inside the container. Skipping copy."
  fi
fi

echo "Stopping existing containers..."
docker stop manual-generator operation-analysis || true
docker rm manual-generator operation-analysis || true

echo "Starting containers with CloudWatch logging..."

# Manual Generator コンテナ
docker run -d \
  --name manual-generator \
  --restart unless-stopped \
  --log-driver awslogs \
  --log-opt awslogs-group=/aws/ec2/kantan-ai-manual-generator \
  --log-opt awslogs-stream=manual-generator-container \
  --log-opt awslogs-region=ap-northeast-1 \
  -p 8080:5000 \
  -e DATABASE_PATH=/app/instance/manual_generator.db \
  -v "$MANUAL_HOST_DIR/logs":/app/logs \
  -v "$MANUAL_HOST_DIR/instance":/app/instance \
  -v "$MANUAL_HOST_DIR/uploads":/app/uploads \
  a40340375d69

# Operation Analysis コンテナ  
docker run -d \
  --name operation-analysis \
  --restart unless-stopped \
  --log-driver awslogs \
  --log-opt awslogs-group=/aws/ec2/kantan-ai-manual-generator/operation_analysis \
  --log-opt awslogs-stream=operation-analysis-container \
  --log-opt awslogs-region=ap-northeast-1 \
  -p 8081:5000 \
  -v "$ANALYSIS_HOST_DIR/results":/app/results \
  kantan-ai-manual-generator-analysis

echo "Containers started with CloudWatch logging"
docker ps
