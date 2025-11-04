# GitHub Actions デプロイ最適化設定

## 🚀 デプロイ時間短縮施策

### 1. 変更検知による選択的デプロイ
- **paths-filter**: ファイル変更を検知し、変更されたサービスのみデプロイ
- **条件分岐**: 不要なビルド・デプロイをスキップ

### 2. Docker最適化
- **BuildKit**: 並列ビルドとキャッシュ最適化
- **Multi-stage builds**: イメージサイズ削減
- **Layer caching**: GitHub Actions cache利用

### 3. 並列処理
- **Matrix strategy**: 複数サービスの並列ビルド
- **Artifact transfer**: ビルド済みイメージの転送

### 4. rsync最適化
- **増分同期**: 変更ファイルのみ転送
- **圧縮転送**: ネットワーク効率化
- **不要ファイル除外**: .git, .md等のスキップ

## 📋 必要なGitHub Secrets

以下のSecretsをGitHubリポジトリに設定してください：

```
EC2_PRIVATE_KEY: EC2のプライベートキー内容
```

## 🔧 さらなる最適化案

### Docker Registry利用
- AWS ECRまたはDocker Hubでイメージキャッシュ
- EC2での直接pullによる高速化

### Blue-Green Deployment
- ゼロダウンタイムデプロイ
- ロールバック機能

### CDN Integration
- CloudFrontでの静的ファイルキャッシュ
- 画像・CSS最適化
