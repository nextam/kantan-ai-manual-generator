# Security Best Practices - Manual Generator

## 🔐 認証方式の選択

### 推奨: サービスアカウント認証（Vertex AI）

**本番環境では必ずサービスアカウント認証を使用してください。**

#### ✅ メリット

1. **細かい権限管理（IAM）**
   - 必要最小限の権限のみを付与可能
   - プロジェクト単位ではなく、リソース単位で制御
   - 例: Vertex AI Userのみ、Storage Object Adminのみ

2. **完全な監査ログ**
   - すべてのAPI呼び出しがCloud Audit Logsに記録
   - 誰が、いつ、何をしたかを追跡可能
   - セキュリティインシデント調査が容易

3. **鍵のローテーション**
   - サービスアカウントキーを定期的に更新可能
   - 鍵の有効期限設定が可能
   - 漏洩時の影響を最小化

4. **環境別の分離**
   - 開発環境、ステージング環境、本番環境で異なるサービスアカウントを使用
   - 環境間の影響を完全に分離

5. **コンプライアンス対応**
   - SOC 2、ISO 27001などの認証取得に有利
   - エンタープライズ要件を満たす

#### 設定方法

```bash
# 1. サービスアカウント作成
gcloud iam service-accounts create manual-generator \
    --display-name="Manual Generator Service Account" \
    --description="Service account for AI Manual Generator application"

# 2. 必要最小限の権限を付与
# Vertex AI使用権限
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:manual-generator@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# Cloud Storage権限
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:manual-generator@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# 3. キーファイル生成
gcloud iam service-accounts keys create gcp-credentials.json \
    --iam-account=manual-generator@YOUR_PROJECT_ID.iam.gserviceaccount.com

# 4. 環境変数設定
# .envファイルに以下を追加
# GOOGLE_APPLICATION_CREDENTIALS="gcp-credentials.json"
```

---

### ⚠️ 非推奨: API Key認証（Maker Suite）

**開発・テスト環境のみで使用。本番環境では絶対に使用しないでください。**

#### ❌ デメリット

1. **粗い権限管理**
   - プロジェクト全体へのアクセス権限
   - 細かい制御ができない

2. **限定的な監査機能**
   - 詳細なログが残らない
   - セキュリティインシデント調査が困難

3. **鍵の漏洩リスク**
   - 単一の鍵が漏洩すると全システムが危険
   - ローテーションが困難

4. **エンタープライズ要件を満たさない**
   - SOC 2、ISO 27001などの認証取得が困難
   - コンプライアンス違反のリスク

#### 使用が許可される場合

- ローカル開発環境のみ
- プロトタイプ・概念実証（PoC）
- 短期間のテスト

---

## 🛡️ 本番環境のセキュリティチェックリスト

### デプロイ前の確認事項

- [ ] **サービスアカウント認証を使用**
  - `GOOGLE_APPLICATION_CREDENTIALS`が設定されている
  - `GOOGLE_API_KEY`は未設定（コメントアウト）

- [ ] **最小権限の原則**
  - サービスアカウントに必要最小限の権限のみ付与
  - 不要なロールは削除

- [ ] **認証情報の管理**
  - `gcp-credentials.json`はGitにコミットしない（`.gitignore`に追加済み）
  - `.env`ファイルもGitにコミットしない（`.gitignore`に追加済み）

- [ ] **環境変数の設定**
  - `FLASK_ENV=production`
  - `DEBUG=False`
  - `SECRET_KEY`は十分にランダムな値

- [ ] **ネットワークセキュリティ**
  - HTTPSを使用（ALB + ACM設定済み）
  - 不要なポートは閉じる

- [ ] **ログとモニタリング**
  - Cloud Loggingを有効化
  - 異常なアクセスパターンを監視

### 定期的なセキュリティメンテナンス

#### 月次

- [ ] サービスアカウントキーをローテーション
- [ ] 不要な権限の確認と削除
- [ ] アクセスログのレビュー

#### 四半期

- [ ] セキュリティ監査の実施
- [ ] 依存パッケージの脆弱性スキャン
- [ ] セキュリティポリシーの見直し

---

## 📋 認証方式の比較表

| 項目 | API Key | サービスアカウント |
|------|---------|-------------------|
| **セキュリティレベル** | ⚠️ 低 | ✅ 高 |
| **権限の細かさ** | プロジェクト全体 | リソース単位 |
| **監査ログ** | 限定的 | 完全 |
| **鍵のローテーション** | 手動・困難 | 自動化可能 |
| **本番環境** | ❌ 非推奨 | ✅ 推奨 |
| **開発環境** | ⚠️ 可（慎重に） | ✅ 推奨 |
| **エンタープライズ** | ❌ 不適切 | ✅ 必須 |
| **コンプライアンス** | ❌ 困難 | ✅ 対応可能 |
| **コスト** | 無料 | 無料 |
| **設定の複雑さ** | 簡単 | やや複雑 |
| **漏洩時の影響範囲** | プロジェクト全体 | 権限範囲内のみ |

---

## 🚨 インシデント対応

### API Key漏洩時の対応

1. **即座に鍵を無効化**
   ```bash
   # Google Cloud Consoleで該当のAPI Keyを削除
   ```

2. **影響範囲の調査**
   - Cloud Loggingで不正なアクセスを確認
   - 影響を受けたリソースを特定

3. **新しい鍵の生成と配布**
   - 新しいAPI Keyを生成
   - 全環境に配布

### サービスアカウントキー漏洩時の対応

1. **即座に鍵を無効化**
   ```bash
   gcloud iam service-accounts keys delete KEY_ID \
       --iam-account=manual-generator@YOUR_PROJECT_ID.iam.gserviceaccount.com
   ```

2. **影響範囲の調査**
   - Cloud Audit Logsで不正なアクセスを確認
   - 影響を受けたリソースを特定

3. **新しい鍵の生成と配布**
   ```bash
   gcloud iam service-accounts keys create gcp-credentials-new.json \
       --iam-account=manual-generator@YOUR_PROJECT_ID.iam.gserviceaccount.com
   ```

4. **権限の見直し**
   - 必要に応じて権限を縮小
   - 不要なロールを削除

---

## 📚 参考リンク

- [Google Cloud IAM Best Practices](https://cloud.google.com/iam/docs/best-practices-service-accounts)
- [Vertex AI Security Documentation](https://cloud.google.com/vertex-ai/docs/general/security)
- [Cloud Storage Security Best Practices](https://cloud.google.com/storage/docs/best-practices)
- [Service Account Key Management](https://cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys)

---

## 📞 サポート

セキュリティに関する質問や懸念事項がある場合は、セキュリティチームにお問い合わせください。

- Email: security@your-domain.com
- Slack: #security-team
