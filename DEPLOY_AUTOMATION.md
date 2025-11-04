# GitHub Actions Auto Deploy Setup

## 🔐 GitHub Secrets設定

### 1. EC2_PRIVATE_KEY の設定

1. GitHubリポジトリのページに移動
2. **Settings** → **Secrets and variables** → **Actions** をクリック
3. **New repository secret** をクリック
4. 以下を設定：
   - **Name**: `EC2_PRIVATE_KEY`
   - **Secret**: EC2プライベートキーの内容全体をコピー&ペースト

```bash
# プライベートキーの内容確認（参考）
cat chuden-demoapp.pem
```

### 2. 自動デプロイの動作確認

```bash
# mainブランチにプッシュして動作確認
git add .
git commit -m "feat: Add auto deploy with optimization"
git push origin matsumoto

# matsumoto → main への PR作成
# PRマージ後、GitHub Actionsが自動実行されます
```

## 🚀 デプロイ最適化の詳細

### 1. 変更検知システム
- **manual_generator/**: Manual Generator関連の変更
- **operation_analysis/**: Operation Analysis関連の変更  
- **docker-compose.yml**: 両サービスに影響する設定変更
- **infra/**: インフラ関連の変更

### 2. ビルド最適化
- **Multi-stage Docker builds**: イメージサイズ最小化
- **Layer caching**: GitHub Actions cache活用
- **並列ビルド**: 複数サービスの同時処理
- **Dependency caching**: pip/apt パッケージキャッシュ

### 3. デプロイ最適化
- **増分同期**: rsyncによる変更ファイルのみ転送
- **選択的再起動**: 変更されたサービスのみ再起動
- **Health checks**: デプロイ後の自動検証
- **Rollback準備**: 失敗時の復旧機能

### 4. 時間短縮効果（推定）

| 項目 | 従来 | 最適化後 | 短縮効果 |
|------|------|----------|----------|
| 変更検知 | なし | 5-10秒 | スキップ可能 |
| Docker build | 全体3-5分 | 変更分のみ1-2分 | 60-70%短縮 |
| ファイル転送 | 全体30-60秒 | 増分5-15秒 | 70-80%短縮 |
| サービス再起動 | 全体60-90秒 | 変更分のみ30-45秒 | 50%短縮 |
| **合計** | **5-7分** | **2-3分** | **50-60%短縮** |

## 🔍 動作ログの確認

### GitHub Actions画面
1. リポジトリの **Actions** タブをクリック
2. **Auto Deploy to EC2** ワークフローを選択
3. 各ステップの詳細ログを確認

### よく見るログ
```bash
# 変更検知結果
✅ Manual Generator changes: true
✅ Operation Analysis changes: false

# ビルド実行
🔨 Building manual service...
ℹ️ Skipping analysis build (no changes)

# デプロイ実行
🚀 Starting deployment...
📦 Transferring manual image...
⏹️ Stopping manual...
🚀 Starting services...
✅ Deployment completed successfully!
```

## 🛠️ トラブルシューティング

### よくある問題

1. **SSH接続エラー**
   ```
   Permission denied (publickey)
   ```
   → `EC2_PRIVATE_KEY` Secretが正しく設定されているか確認

2. **Docker build失敗**
   ```
   ERROR: failed to solve: process "/bin/sh -c pip install" did not complete
   ```
   → requirements.txtの内容確認、依存関係の競合解決

3. **Health check失敗**
   ```
   ❌ Manual health check failed
   ```
   → EC2上でコンテナログ確認: `sudo docker-compose logs manual`

### デバッグ方法

```bash
# EC2に直接SSH接続してデバッグ
ssh -i "chuden-demoapp.pem" ec2-user@ec2-52-198-123-171.ap-northeast-1.compute.amazonaws.com

# コンテナ状況確認
sudo docker ps -a

# ログ確認
sudo docker-compose logs -f

# 手動再起動
sudo docker-compose restart manual
```
