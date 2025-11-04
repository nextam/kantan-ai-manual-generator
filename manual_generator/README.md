# Manual Generator

**動画からマニュアルを自動生成する高機能Webアプリケーション**

Google Cloud Storage と Vertex AI (Gemini) を活用し、製造業の作業手順動画から構造化されたマニュアルを自動生成するFlaskベースのWebアプリケーションです。

## 🌟 主要機能

### 📹 動画アップロード・管理
- **ドラッグ&ドロップ対応**: 直感的な動画ファイルのアップロード
- **ファイル選択ボタン**: 従来のファイル選択インターフェース
- **クラウド直接アップロード**: Google Cloud Storage への直接アップロード
- **リアルタイムプレビュー**: 署名付きURLによる安全な動画プレビュー

### 🤖 AI マニュアル生成
- **Gemini AI 統合**: Google の最新AI モデルを活用
- **製造業特化プロンプト**: 作業手順の構造化された出力
- **構造化フォーマット**: 作業項目・内容・タイムスタンプの体系的整理

### ⚙️ 高度な生成パラメータ制御
- **Gemini バージョン選択**: 2.5 Flash / 2.5 Pro の切り替え

- **動的トークン制限**: バージョンに応じた自動制限調整
- **精密パラメータ調整**: Temperature、Top-P、出力トークン数の細かい制御
- **カスタムプロンプト**: ユースケースに応じた柔軟なプロンプト設定

### 🎨 洗練されたユーザーインターフェース
- **レスポンシブデザイン**: デスクトップ・タブレット対応
- **リアルタイム同期**: スライダー値とバージョン制限の自動同期
- **視覚的フィードバック**: ローディング・エラー・成功メッセージ
- **スムーズアニメーション**: 結果表示の自動スクロール

## 📋 技術仕様

### フロントエンド
- **HTML5**: モダンなセマンティックマークアップ
- **CSS3**: Flexbox レイアウト、カスタムアニメーション
- **Vanilla JavaScript**: フレームワーク不要の軽量実装
- **Fetch API**: 非同期通信によるシームレスなユーザー体験

### バックエンド
- **Flask 3.0.0**: Python Webフレームワーク
- **Google Cloud Storage**: スケーラブルなファイルストレージ
- **Vertex AI**: Gemini モデルによるAI処理
- **環境変数管理**: セキュアな認証情報管理

### 対応動画形式
- MP4, AVI, MOV, MKV, WebM
- 最大ファイルサイズ: 2GB
- 直接クラウドアップロードによる高速処理

## 🚀 セットアップガイド

### 前提条件
- Python 3.8+
- Google Cloud Project (Vertex AI, Cloud Storage 有効)
- Google Cloud 認証情報

### 1. 依存関係のインストール
```bash
# manual_generator ディレクトリに移動
cd manual_generator


# 依存パッケージをインストール
pip install -r requirements.txt
```

### 2. Google Cloud 設定
#### 認証ファイルの配置
```bash
# プロジェクトルートに Google Cloud 認証ファイルを配置
cp /path/to/your/credentials.json gcp-credentials.json
```

#### Cloud Storage バケットの作成
```bash
# Google Cloud CLI を使用してバケットを作成
gsutil mb gs://manual_generator

# 適切な権限を設定
gsutil iam ch serviceAccount:your-service-account@project.iam.gserviceaccount.com:objectAdmin gs://manual_generator
```

### 3. 環境変数の設定
`.env.example` をコピーして `.env` を作成：

```env
# Google Cloud 認証
GOOGLE_APPLICATION_CREDENTIALS=gcp-credentials.json
GOOGLE_API_KEY=your_actual_google_api_key_here

# Google Cloud Storage 設定
GCS_BUCKET_NAME=manual_generator
PROJECT_ID=your-google-cloud-project-id

# Vertex AI 設定
LOCATION=us-central1
```

### 4. 必要な Google Cloud API の有効化
```bash
# Vertex AI API を有効化
gcloud services enable aiplatform.googleapis.com

# Cloud Storage API を有効化
gcloud services enable storage.googleapis.com
```

## 🖥️ 使用方法

### アプリケーション起動
```bash
# Windows
start.bat

# Linux/Mac
chmod +x start.sh
./start.sh

# 直接起動
python app.py
```

### Webインターフェース操作
1. **ブラウザでアクセス**: http://localhost:5000
2. **動画アップロード**: ドラッグ&ドロップまたはファイル選択
3. **生成パラメータ調整**:
   - Gemini バージョン選択
   - 最大出力トークン数 (1000-65535)
   - Temperature (0.0-2.0): AI の創造性レベル
   - Top P (0.0-1.0): 応答の多様性制御
4. **プロンプトカスタマイズ**: 製造業向けデフォルトプロンプト使用可能
5. **マニュアル生成**: 「マニュアル作成」ボタンをクリック
6. **結果確認**: 構造化されたマニュアルが自動表示

## 📊 出力フォーマット

### デフォルト構造化出力
```
作業項目$作業内容$タイムスタンプ

例:
部品準備$必要な工具と材料を作業台に準備する。安全メガネとグローブを着用し、部品の汚れや損傷がないか目視確認する。$00:00:30
組み立て開始$部品Aと部品Bを垂直に配置し、指定された締結トルク（10Nm）で固定ボルトを締める。締結後はボルトの緩みがないか確認する。$00:02:15
```

### カスタマイズ可能要素
- **作業項目**: 端的な作業タイトル
- **作業内容**: 詳細手順・注意点・用語説明
- **タイムスタンプ**: 動画内の該当時間
- **区切り文字**: カスタマイズ可能な出力区切り

## ⚡ パフォーマンス特徴

### Gemini バージョン比較
| バージョン | 最大トークン数 | 特徴 | 用途 |
|-----------|-------------|------|------|
| **Gemini 2.5 Flash** | 65,535 | 高速処理・標準精度 | 一般的なマニュアル生成 |
| **Gemini 2.5 Pro** | 65,535 | 高精度・詳細分析 | 複雑な作業手順・長時間動画 |

### 処理時間目安
- **動画アップロード**: 〜1分 (ファイルサイズに依存)
- **AI マニュアル生成**: 2-5分 (動画長・複雑さに依存)
- **結果表示**: 瞬時

## 🔧 高度な設定

### カスタムプロンプトテンプレート
```javascript
// JavaScript でのプロンプト動的生成例
const customPrompt = `
この動画は、${industryType}の${processType}を説明した動画です。
以下の形式でマニュアルを作成してください：

#出力形式
${outputFormat}

#追加要件
- ${additionalRequirements}
`;
```

### エラーハンドリング強化
- **認証エラー**: 詳細なGoogle Cloud 設定ガイダンス
- **ファイルサイズ制限**: プログレッシブアップロード対応
- **API制限**: レート制限とリトライ機能

## 🛠️ トラブルシューティング

### よくある問題と解決方法

#### 1. **認証関連エラー**
```bash
# 問題: "Your default credentials were not found"
# 解決: 認証ファイルのパス確認
export GOOGLE_APPLICATION_CREDENTIALS="/full/path/to/credentials.json"

# サービスアカウントキーの確認
gcloud auth application-default print-access-token
```

#### 2. **アップロードエラー**
```bash
# 問題: ファイルアップロード失敗
# 解決: バケット権限確認
gsutil iam get gs://manual_generator

# 必要権限: Storage Object Admin, Storage Legacy Bucket Writer
```

#### 3. **生成エラー**
```python
# 問題: Vertex AI API エラー
# 解決: API有効化とクォータ確認
gcloud services list --enabled | grep aiplatform

# リージョン確認
gcloud config get-value compute/region
```

#### 4. **プレビューエラー**
- 署名付きURL の有効期限確認 (1時間)
- バケットのCORS設定確認
- ブラウザキャッシュクリア

### デバッグモード
```python
# app.py でデバッグ有効化
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

ブラウザ開発者ツール（F12）のコンソールタブで詳細ログ確認可能。

## 🚦 システム要件

### 最小要件
- **CPU**: 2コア以上
- **RAM**: 4GB以上
- **ストレージ**: 10GB以上の空き容量
- **ネットワーク**: 安定したインターネット接続

### 推奨要件
- **CPU**: 4コア以上
- **RAM**: 8GB以上
- **ストレージ**: SSD 20GB以上
- **帯域**: 100Mbps以上（大容量動画処理時）

## 📈 拡張可能性

### 今後の機能拡張
- **多言語対応**: i18n による国際化
- **バッチ処理**: 複数動画の一括処理
- **結果エクスポート**: PDF・Word形式での出力
- **ユーザー認証**: マルチユーザー対応
- **履歴管理**: 過去の生成結果保存・検索

### API拡張
- **REST API**: プログラマティックアクセス
- **Webhook**: 処理完了通知
- **統合**: 他システムとのAPI連携

## 📄 ライセンス・サポート

### 依存関係ライセンス
- Flask: BSD-3-Clause
- Google Cloud SDK: Apache 2.0
- その他依存関係: 各パッケージのライセンスに準拠

### テクニカルサポート
- **GitHub Issues**: バグレポート・機能要望
- **Documentation**: 詳細なAPI仕様・設定例
- **Community**: 開発者コミュニティでの質問対応

---

## 🔐 企業認証機能

### テナント機能
- **企業ごとのデータ分離**: 企業コード + パスワードによる認証
- **企業内ユーザー管理**: 管理者・一般ユーザーの権限管理
- **データ保存**: アップロードファイル、生成マニュアル、設定の履歴管理

### ストレージ選択
- **ローカルストレージ**: EC2内でデータ完結（追加コストなし）
- **Google Cloud Storage**: スケーラブルなクラウドストレージ
- **Amazon S3**: AWS統合環境向けクラウドストレージ

### 企業管理コマンド
```bash
# データベース初期化（サンプル企業作成）
python db_manager.py init

# 新規企業作成
python db_manager.py create

# 企業一覧表示
python db_manager.py list

# データベースバックアップ
python db_manager.py backup

# 孤立ファイル清掃
python db_manager.py clean
```

### サンプル企業
初期化時に自動作成される企業アカウント：
- **企業1**: サンプル製造業株式会社 (コード: `sample001`, パスワード: `password123`)
- **企業2**: テスト工業有限会社 (コード: `test002`, パスワード: `test123456`)

### 認証API
- `POST /auth/login` - ログイン
- `POST /auth/logout` - ログアウト
- `GET /auth/status` - 認証状態確認
- `GET /company/settings` - 企業設定取得
- `POST /company/settings` - 企業設定更新

### セキュリティ
- **bcryptパスワードハッシュ化**: 安全なパスワード保存
- **セッショントークン認証**: セキュアな認証維持
- **データ分離**: 企業間の完全なデータ隔離

---

## 🎨 Favicon機能

### アイコンファイル
製造業マニュアル生成システム専用のfaviconを実装：
- `favicon.ico` - 標準favicon（16x16, 32x32, 48x48, 64x64サイズ）
- `favicon-16x16.png` から `favicon-256x256.png` - 各サイズPNG
- `apple-touch-icon.png` - 180×180 Apple Touch Icon

### デザイン要素
- **背景**: 青色グラデーション（#2196F3 → #1976D2）
- **モチーフ**: 📄 文書、⚙️ ギア、🔧 レンチアイコン
- **配色**: Material Design準拠

### HTMLテンプレート適用状況
全テンプレートファイルに以下のタグが追加済み：
```html
<link rel="icon" type="image/x-icon" href="/static/icons/favicon.ico">
<link rel="icon" type="image/png" sizes="32x32" href="/static/icons/favicon-32x32.png">
<link rel="apple-touch-icon" sizes="180x180" href="/static/icons/apple-touch-icon.png">
<meta name="theme-color" content="#2196F3">
```

### ファイル配置
```
manual_generator/static/icons/
├── favicon.ico
├── favicon-{16,32,48,64,128,256}x{16,32,48,64,128,256}.png
├── apple-touch-icon.png
└── manual-icon.svg
```

---

## 🤖 Gemini AI 高度な機能

### 包括的マニュアル生成
Gemini 2.5 Proを活用した高度なマニュアル生成機能：

#### 1. 基本マニュアル生成
- 単一動画からの作業手順抽出
- 構造化されたマニュアル出力
- 製造業特化プロンプト

#### 2. 比較分析マニュアル
- 熟練者・非熟練者動画の同時分析
- 作業技術の差異検出
- 改善提案と研修ポイント抽出

#### 3. 文書統合マニュアル
- 見積書、図面、報告書のOCR処理
- 専門用語の自動抽出・定義
- 関連資料との相互リンク

#### 4. 高度なカスタマイズ
- 出力形式の柔軟な設定
- 画像・動画の自動挿入
- 安全性・品質重視度の調整

### API エンドポイント

#### 比較分析
```bash
POST /ai_comparison_analysis
{
  "expert_video_uri": "gs://bucket/expert.mp4",
  "novice_video_uri": "gs://bucket/novice.mp4",
  "reference_documents": ["doc1.pdf", "doc2.jpg"]
}
```

#### 文書処理
```bash
POST /ai_document_processing
{
  "documents": [MultipartFile]  # 複数ファイル対応
}
```

#### 包括的マニュアル生成
```bash
POST /ai_comprehensive_manual_generation
{
  "expert_video_uri": "gs://bucket/expert.mp4",
  "output_config": {
    "format": "detailed",
    "sections": ["overview", "steps", "safety"],
    "content_length": "normal",
    "writing_style": "formal"
  },
  "include_images": true
}
```

#### 重要フレーム抽出
```bash
POST /ai_extract_key_frames
{
  "video_uri": "gs://bucket/video.mp4",
  "manual_content": "マニュアル内容..."
}
```

### Function Calling活用
- `extract_work_steps`: 作業手順の構造化抽出
- `compare_work_techniques`: 技術比較分析
- `extract_document_data`: 文書データ抽出
- `identify_key_frames`: 重要フレーム特定

### マルチモーダル処理
- 動画・画像・テキストの同時処理
- 大容量コンテキスト（65,535トークン）活用
- 一貫性のある高品質出力

### 期待される効果
- **マニュアル作成時間**: 70%短縮（20時間→6時間）
- **用語統一率**: 95%以上
- **動作認識精度**: 95%以上
- **文書理解精度**: 98%以上

---

**Manual Generator** - 製造業の未来を支えるAI駆動マニュアル生成システム
