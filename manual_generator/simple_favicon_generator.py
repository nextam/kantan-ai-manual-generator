#!/usr/bin/env python3
"""
Simple Favicon Generator
Pillowのみを使用してfaviconを生成するスクリプト
"""

import os
from PIL import Image, ImageDraw

def create_manual_icon():
    """製造業のマニュアル生成システム用アイコンを作成"""
    # 64x64のベースイメージを作成
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 背景の円（青いグラデーション風）
    draw.ellipse([2, 2, 62, 62], fill=(33, 150, 243), outline=(21, 118, 210), width=2)
    
    # 内側の明るい円（立体感）
    draw.ellipse([6, 6, 58, 58], outline=(66, 165, 245), width=1)
    
    # 文書アイコン（白背景）
    draw.rectangle([16, 12, 48, 52], fill=(255, 255, 255), outline=(224, 224, 224), width=1)
    
    # 文書の折り返し部分
    draw.polygon([(40, 12), (48, 12), (48, 20), (40, 12)], fill=(240, 240, 240))
    draw.line([(40, 12), (40, 20), (48, 20)], fill=(200, 200, 200), width=1)
    
    # テキストライン（濃い青）
    draw.rectangle([20, 22, 36, 24], fill=(25, 118, 210))
    draw.rectangle([20, 27, 32, 29], fill=(25, 118, 210))
    draw.rectangle([20, 32, 34, 34], fill=(25, 118, 210))
    draw.rectangle([20, 37, 30, 39], fill=(25, 118, 210))
    
    # ギアアイコン（製造業らしさ）- 右下
    gear_x, gear_y = 38, 42
    gear_size = 6
    
    # ギアの外周
    draw.ellipse([gear_x-gear_size, gear_y-gear_size, 
                  gear_x+gear_size, gear_y+gear_size], 
                 fill=(255, 152, 0), outline=(245, 124, 0), width=1)
    
    # ギアの歯（8方向）
    for i in range(8):
        angle_deg = i * 45
        if i % 2 == 0:  # 主要な4方向に歯を作る
            if angle_deg == 0:    # 右
                draw.rectangle([gear_x+gear_size-1, gear_y-1, gear_x+gear_size+2, gear_y+1], fill=(245, 124, 0))
            elif angle_deg == 90:  # 下
                draw.rectangle([gear_x-1, gear_y+gear_size-1, gear_x+1, gear_y+gear_size+2], fill=(245, 124, 0))
            elif angle_deg == 180: # 左
                draw.rectangle([gear_x-gear_size-2, gear_y-1, gear_x-gear_size+1, gear_y+1], fill=(245, 124, 0))
            elif angle_deg == 270: # 上
                draw.rectangle([gear_x-1, gear_y-gear_size-2, gear_x+1, gear_y-gear_size+1], fill=(245, 124, 0))
    
    # ギアの中心の穴
    draw.ellipse([gear_x-2, gear_y-2, gear_x+2, gear_y+2], fill=(230, 100, 0))
    
    # 小さなレンチ（左下）
    wrench_x, wrench_y = 26, 42
    # レンチの柄
    draw.rectangle([wrench_x-6, wrench_y-1, wrench_x+2, wrench_y+1], fill=(76, 175, 80))
    # レンチの頭部
    draw.rectangle([wrench_x-8, wrench_y-2, wrench_x-6, wrench_y+2], fill=(76, 175, 80))
    draw.rectangle([wrench_x-7, wrench_y-3, wrench_x-5, wrench_y-2], fill=(76, 175, 80))
    
    return img

def generate_favicons():
    """各種サイズのfaviconを生成"""
    # ベースアイコンを作成
    base_icon = create_manual_icon()
    
    # 出力ディレクトリ
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(current_dir, 'static', 'icons')
    os.makedirs(output_dir, exist_ok=True)
    
    # 各種サイズを生成
    sizes = [16, 32, 48, 64, 128, 256]
    
    for size in sizes:
        resized = base_icon.resize((size, size), Image.Resampling.LANCZOS)
        output_path = os.path.join(output_dir, f'favicon-{size}x{size}.png')
        resized.save(output_path, 'PNG', optimize=True)
        print(f"Generated: favicon-{size}x{size}.png")
    
    # .ico ファイル作成（複数サイズを含む）
    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64)]
    ico_images = []
    
    for width, height in ico_sizes:
        resized = base_icon.resize((width, height), Image.Resampling.LANCZOS)
        ico_images.append(resized)
    
    ico_path = os.path.join(output_dir, 'favicon.ico')
    ico_images[0].save(ico_path, format='ICO', sizes=ico_sizes)
    print(f"Generated: favicon.ico")
    
    # Apple touch icon (180x180)
    apple_icon = base_icon.resize((180, 180), Image.Resampling.LANCZOS)
    apple_path = os.path.join(output_dir, 'apple-touch-icon.png')
    apple_icon.save(apple_path, 'PNG', optimize=True)
    print(f"Generated: apple-touch-icon.png")
    
    return output_dir

def create_html_favicon_tags(icon_dir):
    """HTMLに追加するfaviconタグを生成"""
    tags = [
        '<!-- Favicon -->',
        '<link rel="icon" type="image/x-icon" href="/static/icons/favicon.ico">',
        '<link rel="icon" type="image/png" sizes="16x16" href="/static/icons/favicon-16x16.png">',
        '<link rel="icon" type="image/png" sizes="32x32" href="/static/icons/favicon-32x32.png">',
        '<link rel="icon" type="image/png" sizes="48x48" href="/static/icons/favicon-48x48.png">',
        '<link rel="icon" type="image/png" sizes="64x64" href="/static/icons/favicon-64x64.png">',
        '<link rel="icon" type="image/png" sizes="128x128" href="/static/icons/favicon-128x128.png">',
        '<link rel="icon" type="image/png" sizes="256x256" href="/static/icons/favicon-256x256.png">',
        '<link rel="apple-touch-icon" sizes="180x180" href="/static/icons/apple-touch-icon.png">',
        '<meta name="theme-color" content="#2196F3">',
    ]
    
    # HTMLファイルに保存
    html_tags_path = os.path.join(icon_dir, 'favicon_html_tags.txt')
    with open(html_tags_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(tags))
    
    print(f"\nHTML tags saved to: favicon_html_tags.txt")
    print("Add these tags to your HTML <head> section:")
    print('\n'.join(tags))

def main():
    print("Generating favicons for Manual Generator System...")
    
    # Faviconを生成
    icon_dir = generate_favicons()
    
    # HTMLタグを生成
    create_html_favicon_tags(icon_dir)
    
    print(f"\n✅ Favicon generation completed!")
    print(f"📁 Files saved to: {icon_dir}")
    print("\n📋 Next steps:")
    print("1. Copy the HTML tags from favicon_html_tags.txt")
    print("2. Add them to your HTML template <head> section")
    print("3. Restart your server to see the new favicon")

if __name__ == "__main__":
    main()
