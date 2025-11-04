# Favicon Documentation - Manual Generator System

## 概要
製造業向けマニュアル自動生成システム用のfaviconを作成しました。
無料でライセンスフリーのアイコンとして使用できます。

## 生成されたファイル

### アイコンファイル
- `favicon.ico` - 標準的なfaviconファイル（16x16, 32x32, 48x48, 64x64サイズを含む）
- `favicon-16x16.png` - 16×16ピクセルのPNG
- `favicon-32x32.png` - 32×32ピクセルのPNG
- `favicon-48x48.png` - 48×48ピクセルのPNG
- `favicon-64x64.png` - 64×64ピクセルのPNG
- `favicon-128x128.png` - 128×128ピクセルのPNG
- `favicon-256x256.png` - 256×256ピクセルのPNG
- `apple-touch-icon.png` - 180×180ピクセルのApple Touch Icon

### 設計要素
- **背景色**: 青色グラデーション（#2196F3 → #1976D2）
- **主要モチーフ**: 
  - 📄 文書アイコン（マニュアルを表現）
  - ⚙️ ギアアイコン（製造業を表現）
  - 🔧 レンチアイコン（工具・作業を表現）
- **配色**: Material Design準拠（青・オレンジ・緑）

## HTMLテンプレートへの適用状況

以下のテンプレートファイルにfaviconタグが追加されています：

✅ **更新済み**
- `edit_manual.html`
- `error.html`
- `login.html`
- `manual_create.html`
- `manual_create_with_images.html`
- `manual_detail.html`
- `manual_list.html`
- `super_admin_dashboard.html`
- `super_admin_login.html`

## HTMLタグ
各テンプレートの `<head>` セクションに以下のタグが追加されています：

```html
<!-- Favicon -->
<link rel="icon" type="image/x-icon" href="/static/icons/favicon.ico">
<link rel="icon" type="image/png" sizes="16x16" href="/static/icons/favicon-16x16.png">
<link rel="icon" type="image/png" sizes="32x32" href="/static/icons/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="48x48" href="/static/icons/favicon-48x48.png">
<link rel="icon" type="image/png" sizes="64x64" href="/static/icons/favicon-64x64.png">
<link rel="apple-touch-icon" sizes="180x180" href="/static/icons/apple-touch-icon.png">
<meta name="theme-color" content="#2196F3">
```

## ライセンス・使用権
- **完全無料**: 商用・非商用問わず無料で使用可能
- **ライセンスフリー**: 著作権表示不要
- **改変可能**: 必要に応じて色やデザインの変更可能
- **再配布可能**: アイコンファイルの再配布も可能

## 技術仕様
- **作成ツール**: Python + Pillow（PIL）
- **ファイル形式**: PNG, ICO
- **最適化**: 各サイズに応じて最適化済み
- **ブラウザ対応**: 全モダンブラウザ対応（Chrome, Firefox, Safari, Edge）

## ファイル配置
```
manual_generator/
└── static/
    └── icons/
        ├── favicon.ico
        ├── favicon-16x16.png
        ├── favicon-32x32.png
        ├── favicon-48x48.png
        ├── favicon-64x64.png
        ├── favicon-128x128.png
        ├── favicon-256x256.png
        ├── apple-touch-icon.png
        ├── favicon_html_tags.txt
        └── manual-icon.svg
```

## 更新・再生成方法
アイコンのデザインを変更したい場合：

1. `simple_favicon_generator.py` の `create_manual_icon()` 関数を編集
2. スクリプトを実行: `python simple_favicon_generator.py`
3. 新しいHTMLタグが必要な場合は `add_favicon_to_templates.py` を実行

## 確認方法
1. ブラウザで `http://localhost:5000` にアクセス
2. ブラウザのタブに青い文書アイコンが表示されることを確認
3. ブックマークバーに追加してアイコンが正しく表示されることを確認

