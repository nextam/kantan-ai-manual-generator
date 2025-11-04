## プロジェクト概要

製造業に特化した以下2つの独立MVPを同一リポジトリで開発・検証するためのプロジェクトです。

- 作業分析システム（Operation Analysis System, OAS）
- マニュアル自動生成システム（Manual Generator, MG）

両者は単体で動作可能ですが、将来的な連携（OASの分析結果をMGへ流用）も想定します。

### 本番環境URL
- マニュアル自動生成システム: https://manual-generator.chuden-demoapp.com
- 作業分析システム: https://operation-analysis.chuden-demoapp.com

### 目的（MVP）
- OAS: 現場動画/ログから基本作業の抽出・時間計測・簡易レポートを最短経路で提供
- MG: 作業定義やテンプレートから、現場で使える手順書（PDF/HTML）を半自動生成

## リポジトリ構成（提案）
- `SPECIFICATION_OPERATION_ANALYSIS.md` … 作業分析システムの仕様書
- `SPECIFICATION_MANUAL_GENERATOR.md` … マニュアル自動生成システムの仕様書
- `oas/` … 作業分析MVPのソース（後日作成）
- `mg/` … マニュアル生成MVPのソース（後日作成）
- `docs/` … 画面モック、設計補足、議事録等（任意）

## 技術スタック（初期案）
- Backend: FastAPI または Node.js（Express）
- Frontend: React または Vue（小規模MVPは簡易UIでも可）
- ML/分析（任意）: Python（OpenCV, Mediapipe など）
- データ: SQLite/JSONファイルで開始（将来はPostgreSQL）

## 進め方（軽量）
1. 仕様書のMVPスコープを確定（本README末尾のリンク参照）
2. 最小ユースケースの通しデモを最優先で実装
3. KPI/受け入れ条件を満たすまで改善（2週間スプリント想定）

## セットアップ（後日）
- 各サブディレクトリに `README` と簡易起動スクリプトを配置予定
- まずは仕様確定→スケルトン作成→通しデモ実装の順でコミット

## リンク
- 作業分析システム仕様: `SPECIFICATION_OPERATION_ANALYSIS.md`
- マニュアル自動生成システム仕様: `SPECIFICATION_MANUAL_GENERATOR.md`

## 用語
- 工程/作業/手順: 工程を構成する最小作業単位を「手順」と呼称
- 作業定義: 手順の並び、所要時間、使用資材/工具、注意点などの構造化情報

## ライセンス / 権利
- TBD（社内/委託条件に合わせて追記）

