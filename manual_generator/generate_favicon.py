#!/usr/bin/env python3
"""
Favicon Generator Script
無料でライセンスフリーのfaviconを生成するスクリプト

必要なライブラリ:
pip install Pillow cairosvg

使用方法:
python generate_favicon.py
"""

import os
from PIL import Image, ImageDraw, ImageFont
import cairosvg
from io import BytesIO

def create_simple_favicon():
    """シンプルなfaviconを作成"""
    # 64x64のベースイメージを作成
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 背景の円
    draw.ellipse([2, 2, 62, 62], fill=(33, 150, 243), outline=(21, 118, 210), width=2)
    
    # 文書アイコン
    draw.rectangle([18, 14, 46, 50], fill=(255, 255, 255), outline=(227, 242, 253), width=1)
    
    # テキストライン
    draw.rectangle([22, 20, 42, 22], fill=(25, 118, 210))
    draw.rectangle([22, 25, 38, 27], fill=(25, 118, 210))
    draw.rectangle([22, 30, 40, 32], fill=(25, 118, 210))
    
    # ギア（製造業らしさ）
    center_x, center_y = 32, 40
    gear_radius = 4
    
    # ギアの中心
    draw.ellipse([center_x-gear_radius, center_y-gear_radius, 
                  center_x+gear_radius, center_y+gear_radius], 
                 fill=(255, 152, 0))
    
    # ギアの歯
    for i in range(8):
        angle = i * 45
        # 簡単な歯の表現
        if i % 2 == 0:
            x_offset = 2 if i < 4 else -2
            y_offset = 2 if i in [1, 2, 5, 6] else -2
            draw.rectangle([center_x + x_offset - 1, center_y + y_offset - 1,
                           center_x + x_offset + 1, center_y + y_offset + 1], 
                          fill=(245, 124, 0))
    
    return img

def create_favicons_from_svg(svg_path, output_dir):
    """SVGファイルから各種サイズのfaviconを生成"""
    sizes = [16, 32, 48, 64, 128, 256]
    
    # SVGを読み込み
    with open(svg_path, 'rb') as svg_file:
        svg_data = svg_file.read()
    
    for size in sizes:
        # SVGをPNGに変換
        png_data = cairosvg.svg2png(bytestring=svg_data, output_width=size, output_height=size)
        
        # PILで開く
        img = Image.open(BytesIO(png_data))
        
        # ファイル保存
        output_path = os.path.join(output_dir, f'favicon-{size}x{size}.png')
        img.save(output_path, 'PNG')
        print(f"Generated: {output_path}")
    
    # .icoファイルも作成（複数サイズを含む）
    ico_sizes = [(16, 16), (32, 32), (48, 48)]
    ico_images = []
    
    for width, height in ico_sizes:
        png_data = cairosvg.svg2png(bytestring=svg_data, output_width=width, output_height=height)
        img = Image.open(BytesIO(png_data))
        ico_images.append(img)
    
    ico_path = os.path.join(output_dir, 'favicon.ico')
    ico_images[0].save(ico_path, format='ICO', sizes=ico_sizes)
    print(f"Generated: {ico_path}")

def create_fallback_favicon(output_dir):
    """SVG変換ライブラリがない場合のフォールバック"""
    img = create_simple_favicon()
    
    sizes = [16, 32, 48, 64, 128, 256]
    
    for size in sizes:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        output_path = os.path.join(output_dir, f'favicon-{size}x{size}.png')
        resized.save(output_path, 'PNG')
        print(f"Generated: {output_path}")
    
    # .ico file
    ico_sizes = [(16, 16), (32, 32), (48, 48)]
    ico_images = [img.resize(size, Image.Resampling.LANCZOS) for size in ico_sizes]
    
    ico_path = os.path.join(output_dir, 'favicon.ico')
    ico_images[0].save(ico_path, format='ICO', sizes=ico_sizes)
    print(f"Generated: {ico_path}")

def main():
    # 出力ディレクトリ
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(current_dir, 'static', 'icons')
    
    # ディレクトリが存在しない場合は作成
    os.makedirs(output_dir, exist_ok=True)
    
    # SVGファイルのパス
    svg_path = os.path.join(output_dir, 'manual-icon.svg')
    
    try:
        # SVGからfaviconを生成
        if os.path.exists(svg_path):
            create_favicons_from_svg(svg_path, output_dir)
        else:
            print("SVG file not found, creating fallback favicon...")
            create_fallback_favicon(output_dir)
    except ImportError:
        print("cairosvg not available, creating fallback favicon...")
        create_fallback_favicon(output_dir)
    except Exception as e:
        print(f"Error with SVG conversion: {e}")
        print("Creating fallback favicon...")
        create_fallback_favicon(output_dir)
    
    # Web manifest用のアイコンも作成
    create_web_manifest(output_dir)
    
    print("\nFavicon generation completed!")
    print(f"Files saved to: {output_dir}")

def create_web_manifest(output_dir):
    """PWA用のweb manifest作成"""
    manifest = {
        "name": "マニュアル生成システム",
        "short_name": "Manual Generator",
        "description": "製造業向けマニュアル自動生成システム",
        "icons": [
            {
                "src": "/static/icons/favicon-16x16.png",
                "sizes": "16x16",
                "type": "image/png"
            },
            {
                "src": "/static/icons/favicon-32x32.png",
                "sizes": "32x32",
                "type": "image/png"
            },
            {
                "src": "/static/icons/favicon-128x128.png",
                "sizes": "128x128",
                "type": "image/png"
            },
            {
                "src": "/static/icons/favicon-256x256.png",
                "sizes": "256x256",
                "type": "image/png"
            }
        ],
        "theme_color": "#2196F3",
        "background_color": "#ffffff",
        "display": "standalone",
        "start_url": "/"
    }
    
    import json
    manifest_path = os.path.join(output_dir, 'manifest.json')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    print(f"Generated: {manifest_path}")

if __name__ == "__main__":
    main()
