## マニュアル自動生成システム（Manual Generator, MG）仕様（MVP）

### 1. 目的
- 作業定義（手順、注意点、画像など）から、現場配布可能な手順書（PDF/HTML）を半自動で生成し、更新コストを下げる。

### 2. スコープ（MVP）
- 入力: JSON/CSVの作業定義、画像ファイル（任意）
- 出力: PDF/HTMLの手順書（A4縦想定・1カラム/2カラム）
- ターゲット: 単一作業の手順書（多品種展開はテンプレ差し替えで対応）

### 3. ユースケース
1. 作業定義JSONをアップロード
2. テンプレートを選択（標準/シンプル）
3. 表紙・版数・発行日・責任者などのメタ情報を入力
4. プレビュー確認→PDF/HTMLとして出力

### 4. 機能要件
- F1: 作業定義の取り込み（JSON/CSV→内部モデル）
- F2: テンプレート適用（Handlebars/EJS等）
- F3: 画像取込・リサイズ・キャプション
- F4: 目次・自動番号付与・注意/警告表示
- F5: PDF生成（ヘッダ/フッタ、ページ番号）
- F6: 設定の保存/読込（JSON）

### 5. 非機能要件
- N1: ローカルで完結（オフライン可）
- N2: 20手順・画像10枚程度で即時プレビュー（<2秒目標）
- N3: 生成物の再現性（テンプレ+データで同一結果）

### 6. 画面/API（初期案）
- 画面: データ入力、テンプレ選択、プレビュー、エクスポート
- API: `/import`, `/template`, `/preview`, `/export`, `/config`

### 7. データモデル（簡易）
```
Manual {
	id: string,
	title: string,
	version: string,
	issuedAt: string,
	owner: string,
	steps: ManualStep[],
	assets: Asset[]
}
ManualStep {
	id: string,
	title: string,
	description: string,
	imageId?: string,
	caution?: string,
	tools?: string[]
}
Asset { id: string, path: string, alt?: string }
```

### 8. テンプレート設計（MVP）
- HTMLテンプレ + CSS（印刷用）でレイアウト固定
- プレースホルダ: 表紙情報、目次、手順繰り返し、注意枠

### 9. KPI/評価
- JSON入力→PDF出力まで5分以内に完了
- レイアウト崩れがない（ページ切れ、孤立行の最小化）

### 10. リスクと制約
- 画像解像度のばらつきによる見栄え差
- PDF化エンジン依存の差異（Chromium/ wkhtmltopdf 等）

### 11. 受け入れ条件
- サンプルJSONから、テンプレ標準でPDF/HTMLを生成できる
- 設定の保存/読込が機能する

### 12. 今後の拡張
- 多言語対応、QRコード差し込み、改訂履歴の自動化
- OASからの手順データ連携

