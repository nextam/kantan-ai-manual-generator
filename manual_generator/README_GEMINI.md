# Manual Generator - Gemini 2.5 Pro Enhanced

製造業向け AI駆動マニュアル自動生成システム

## 🚀 概要

Gemini 2.5 Proを中核AIエンジンとして活用し、製造業の作業マニュアルを自動生成するシステムです。熟練者と非熟練者の動画比較分析、文書統合、専門用語データベース連携により、高品質で実用的なマニュアルを作成します。

### 🎯 主要機能

#### 1. 基本マニュアル生成
- 単一動画からの作業手順抽出
- Gemini 2.5 Proによる詳細分析
- 構造化されたマニュアル出力

#### 2. 比較分析マニュアル
- 熟練者・非熟練者動画の同時分析
- 作業技術の差異検出
- 改善提案と研修ポイントの抽出

#### 3. 文書統合マニュアル
- 見積書、図面、報告書等のOCR処理
- 専門用語の自動抽出・定義
- 関連資料との相互リンク

#### 4. 高度なカスタマイズ
- 出力形式の柔軟な設定
- 画像・動画の自動挿入
- 安全性・品質重視度の調整

## 🏗️ システム構成

```
manual_generator/
├── app.py                              # Flask API（既存機能 + Gemini統合）
├── modules/                            # Gemini統合モジュール群
│   ├── gemini_service.py              # Gemini 2.5 Pro統合サービス
│   └── terminology_db.py              # 専門用語データベース管理
├── templates/
│   ├── manual_generator.html          # 既存基本UI
│   └── manual_generator_enhanced.html # Gemini統合UI
├── static/
│   └── generated_manuals/             # 生成マニュアル保存
├── data/
│   └── terminology.db                # 専門用語データベース
├── temp_uploads/                      # 一時アップロード
├── requirements.txt                   # 依存関係
├── test_gemini_integration.py         # 統合テストスクリプト
└── README_GEMINI.md                  # このファイル
```

## 🔧 セットアップ手順

### 1. 環境準備

```bash
# 作業ディレクトリに移動
cd manual_generator

# 仮想環境作成（推奨）
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Gemini統合パッケージのインストール
pip install -r requirements.txt
```

### 2. Google Cloud設定

```bash
# サービスアカウントキーの配置
# gcp-credentials.json をプロジェクトルートに配置

# .envファイルでの設定（推奨方法）
# .env ファイルを作成して以下の設定を追加:
GOOGLE_APPLICATION_CREDENTIALS=gcp-credentials.json
GOOGLE_API_KEY=your_gemini_api_key
GOOGLE_CLOUD_PROJECT_ID=career-survival

# または環境変数で直接設定
set GOOGLE_APPLICATION_CREDENTIALS=gcp-credentials.json
set GOOGLE_API_KEY=your_gemini_api_key
```

### 3. データベース初期化

```python
# 専門用語データベースの初期化
python modules/terminology_db.py
```

### 4. テスト実行

```python
# Gemini統合機能のテスト
python test_gemini_integration.py
```

### 5. アプリケーション起動

```python
# Flaskアプリケーション起動
python app.py
```

アプリケーションは http://localhost:5000 で利用可能になります。

## 📋 API エンドポイント

### 既存エンドポイント
- `GET /` - 基本UIの表示
- `POST /upload` - 動画アップロード
- `POST /generate_manual` - 基本マニュアル生成
- `GET /health` - ヘルスチェック

### 新規Gemini統合エンドポイント

#### `POST /ai_comparison_analysis`
熟練者・非熟練者動画の比較分析

```json
{
  "expert_video_uri": "gs://bucket/expert.mp4",
  "novice_video_uri": "gs://bucket/novice.mp4",
  "reference_documents": ["doc1.pdf", "doc2.jpg"]
}
```

#### `POST /ai_document_processing`
文書のOCR処理と構造化

```json
{
  "documents": [MultipartFile]  // 複数ファイル対応
}
```

#### `POST /ai_comprehensive_manual_generation`
包括的マニュアル生成

```json
{
  "expert_video_uri": "gs://bucket/expert.mp4",
  "novice_video_uri": "gs://bucket/novice.mp4",
  "output_config": {
    "format": "detailed",
    "sections": ["overview", "steps", "safety"],
    "content_length": "normal",
    "writing_style": "formal"
  },
  "include_images": true
}
```

#### `POST /ai_extract_key_frames`
重要フレームの自動抽出

```json
{
  "video_uri": "gs://bucket/video.mp4",
  "manual_content": "マニュアル内容..."
}
```

#### `GET /download_manual/<manual_id>`
生成されたマニュアルのダウンロード

## 🎨 ユーザーインターフェース

### タブベースUI
1. **基本マニュアル生成**: 単一動画からの簡単生成
2. **比較分析マニュアル**: 熟練者・非熟練者比較
3. **文書統合マニュアル**: 関連資料との統合
4. **高度な設定**: 詳細なカスタマイズオプション

### 主要機能
- ドラッグ&ドロップ対応
- リアルタイム動画プレビュー
- 進捗表示と非同期処理
- レスポンシブデザイン
- 詳細結果のアコーディオン表示

## 🤖 Gemini 2.5 Pro活用戦略

### Function Calling活用
- `extract_work_steps`: 作業手順の構造化抽出
- `compare_work_techniques`: 技術比較分析
- `extract_document_data`: 文書データ抽出
- `identify_key_frames`: 重要フレーム特定

### マルチモーダル処理
- 動画・画像・テキストの同時処理
- 大容量コンテキスト（65,535トークン）の活用
- 一貫性のある高品質出力

### 専門特化プロンプト
- 製造業特有の用語・概念理解
- 安全性・品質重視の分析
- 実践的な改善提案生成

## 📊 期待される効果

### 定量的効果
- **マニュアル作成時間**: 70%短縮（20時間→6時間）
- **用語統一率**: 95%以上
- **動作認識精度**: 95%以上
- **文書理解精度**: 98%以上

### 定性的効果
- 作業手順の標準化促進
- 熟練者ノウハウの体系化
- 安全性意識の向上
- 継続的改善サイクルの確立

## 🔍 トラブルシューティング

### よくある問題

#### 1. Geminiパッケージのインポートエラー
```bash
# 解決方法
pip install --upgrade google-generativeai vertexai
```

#### 2. Google Cloud認証エラー
```bash
# サービスアカウントキーの確認
# 環境変数の設定確認
echo %GOOGLE_APPLICATION_CREDENTIALS%
```

#### 3. 動画アップロードエラー
- ファイルサイズ制限: 2GB以下
- 対応形式: MP4, AVI, MOV, MKV, WebM
- GCSバケットの権限確認

#### 4. メモリ不足エラー
```python
# 大容量動画の場合は分割処理を実装
# または処理解像度の調整
```

### ログ確認
```bash
# Flaskアプリケーションログ
tail -f app.log

# Geminiサービスログ
# modules/gemini_service.py内のロガー出力を確認
```

## 🛠️ 開発者向け情報

### 新機能追加方法

#### 1. Function Calling関数追加
```python
# modules/gemini_service.py の _setup_function_definitions() に追加
{
    "name": "new_function_name",
    "description": "関数の説明",
    "parameters": {
        "type": "object",
        "properties": {
            "param_name": {"type": "string", "description": "パラメータ説明"}
        }
    }
}
```

#### 2. API エンドポイント追加
```python
# app.py に新しいルート追加
@app.route('/new_endpoint', methods=['POST'])
def new_endpoint():
    # 実装コード
    pass
```

#### 3. UI要素追加
```html
<!-- templates/manual_generator_enhanced.html に追加 -->
<div class="new-feature">
    <!-- 新機能のHTML -->
</div>
```

### テスト追加
```python
# test_gemini_integration.py に新しいテスト関数追加
async def test_new_feature():
    # テストコード
    pass
```

## 📄 ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

## 🤝 コントリビューション

1. フォークを作成
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチをプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📞 サポート

問題や質問がある場合は、GitHubのIssuesまたは以下に連絡してください：

- プロジェクト責任者: [連絡先]
- テクニカルサポート: [サポート連絡先]

---

## 🎉 次のステップ

1. **環境セットアップ**: 必要なパッケージとAPIキーの設定
2. **基本テスト**: `test_gemini_integration.py` の実行
3. **サンプル動画テスト**: 実際の製造業動画でのテスト
4. **カスタマイズ**: 企業固有の要求に合わせた調整
5. **本格運用**: 製造現場での実用的活用

Gemini 2.5 Proの高度なAI機能を活用して、製造業の生産性向上と安全性確保に貢献します！
