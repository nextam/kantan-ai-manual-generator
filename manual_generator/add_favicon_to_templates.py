#!/usr/bin/env python3
"""
HTMLテンプレートにfaviconタグを一括追加するスクリプト
"""

import os
import re
import glob

def add_favicon_to_html(file_path):
    """HTMLファイルにfaviconタグを追加"""
    
    favicon_tags = """    
    <!-- Favicon -->
    <link rel="icon" type="image/x-icon" href="/static/icons/favicon.ico">
    <link rel="icon" type="image/png" sizes="16x16" href="/static/icons/favicon-16x16.png">
    <link rel="icon" type="image/png" sizes="32x32" href="/static/icons/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="48x48" href="/static/icons/favicon-48x48.png">
    <link rel="icon" type="image/png" sizes="64x64" href="/static/icons/favicon-64x64.png">
    <link rel="apple-touch-icon" sizes="180x180" href="/static/icons/apple-touch-icon.png">
    <meta name="theme-color" content="#2196F3">
    """
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 既にfaviconタグが存在するかチェック
        if 'favicon' in content.lower():
            print(f"⏭️  {os.path.basename(file_path)} - Already has favicon tags")
            return False
        
        # <title>タグの後にfaviconタグを挿入
        title_pattern = r'(<title>.*?</title>)'
        match = re.search(title_pattern, content, re.IGNORECASE | re.DOTALL)
        
        if match:
            # <title>タグの後に挿入
            new_content = content.replace(match.group(1), match.group(1) + favicon_tags)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"✅ {os.path.basename(file_path)} - Favicon tags added")
            return True
        else:
            print(f"❌ {os.path.basename(file_path)} - No <title> tag found")
            return False
            
    except Exception as e:
        print(f"❌ {os.path.basename(file_path)} - Error: {str(e)}")
        return False

def main():
    print("Adding favicon tags to HTML templates...")
    
    # templatesディレクトリのパス
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    
    # HTMLファイルを検索
    html_files = glob.glob(os.path.join(templates_dir, '*.html'))
    
    if not html_files:
        print("No HTML files found in templates directory")
        return
    
    updated_count = 0
    for html_file in html_files:
        if add_favicon_to_html(html_file):
            updated_count += 1
    
    print(f"\n📊 Summary:")
    print(f"   Total files: {len(html_files)}")
    print(f"   Updated: {updated_count}")
    print(f"   Skipped: {len(html_files) - updated_count}")
    
    if updated_count > 0:
        print(f"\n🔄 Please restart your server to see the favicon changes")

if __name__ == "__main__":
    main()
