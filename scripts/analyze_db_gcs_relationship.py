#!/usr/bin/env python3
"""
データベース内ファイルとGCS存在状況の詳細調査
"""
import sqlite3
import os
import subprocess
import json

def check_gcs_file_existence():
    """データベース内の全ファイルのGCS存在状況を調査"""
    print("=== データベース vs GCS ファイル存在状況調査 ===")
    print()
    
    # データベース接続
    db_path = r"manual_generator\instance\manual_generator.db"
    if not os.path.exists(db_path):
        print(f"❌ データベースファイルが見つかりません: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 全ファイルを取得
    cursor.execute("""
        SELECT id, original_filename, stored_filename, file_path, file_size, uploaded_at
        FROM uploaded_files 
        ORDER BY id
    """)
    
    all_files = cursor.fetchall()
    print(f"データベース内総ファイル数: {len(all_files)}")
    print()
    
    # GCS上の全ファイルを取得
    print("📁 GCS上の全ファイル一覧を取得中...")
    try:
        # gcloud storage ls を使用
        result = subprocess.run([
            'gcloud', 'storage', 'ls', 'gs://manual_generator/video/', '--recursive'
        ], capture_output=True, text=True, check=True)
        
        gcs_files = []
        for line in result.stdout.strip().split('\n'):
            if line.strip() and not line.endswith(':'):
                # gs://manual_generator/video/filename.mp4 -> video/filename.mp4
                if 'gs://manual_generator/' in line:
                    relative_path = line.replace('gs://manual_generator/', '')
                    gcs_files.append(relative_path)
        
        print(f"GCS上のファイル数: {len(gcs_files)}")
        print()
        
    except subprocess.CalledProcessError as e:
        print(f"❌ GCS ファイル一覧取得エラー: {e}")
        return
    except FileNotFoundError:
        print("❌ gcloud コマンドが見つかりません。Google Cloud CLIがインストールされていない可能性があります。")
        return
    
    # 詳細分析
    analysis_results = {
        'exact_matches': [],      # 完全一致
        'missing_files': [],      # データベースにあるがGCSにない
        'orphaned_files': [],     # GCSにあるがデータベースにない
        'duplicate_originals': {},  # 同じ元ファイル名の複数バージョン
        'size_groups': {}         # 同じサイズのファイルグループ
    }
    
    print("🔍 詳細分析開始...")
    
    # データベースファイルの分析
    for file_record in all_files:
        file_id, original_name, stored_name, file_path, file_size, upload_date = file_record
        
        # 完全一致確認
        if file_path in gcs_files:
            analysis_results['exact_matches'].append({
                'id': file_id,
                'original': original_name,
                'stored': stored_name,
                'path': file_path,
                'size': file_size,
                'date': upload_date
            })
        else:
            analysis_results['missing_files'].append({
                'id': file_id,
                'original': original_name,
                'stored': stored_name,
                'path': file_path,
                'size': file_size,
                'date': upload_date
            })
        
        # 元ファイル名でグループ化
        if original_name not in analysis_results['duplicate_originals']:
            analysis_results['duplicate_originals'][original_name] = []
        analysis_results['duplicate_originals'][original_name].append({
            'id': file_id,
            'stored': stored_name,
            'path': file_path,
            'size': file_size,
            'date': upload_date,
            'exists_in_gcs': file_path in gcs_files
        })
        
        # サイズでグループ化
        if file_size not in analysis_results['size_groups']:
            analysis_results['size_groups'][file_size] = []
        analysis_results['size_groups'][file_size].append({
            'id': file_id,
            'original': original_name,
            'stored': stored_name,
            'path': file_path,
            'date': upload_date,
            'exists_in_gcs': file_path in gcs_files
        })
    
    # GCS上の孤立ファイルを特定
    db_paths = {file_record[3] for file_record in all_files if file_record[3]}
    for gcs_path in gcs_files:
        if gcs_path not in db_paths:
            analysis_results['orphaned_files'].append(gcs_path)
    
    # 結果出力
    print_analysis_results(analysis_results)
    
    conn.close()
    return analysis_results

def print_analysis_results(results):
    """分析結果を整理して出力"""
    
    print("=" * 80)
    print("📊 分析結果サマリー")
    print("=" * 80)
    
    print(f"✅ 完全一致ファイル: {len(results['exact_matches'])}件")
    print(f"❌ 欠損ファイル: {len(results['missing_files'])}件")
    print(f"🔸 孤立ファイル（GCSのみ）: {len(results['orphaned_files'])}件")
    print()
    
    # 1. 完全一致ファイル
    if results['exact_matches']:
        print("✅ 完全一致ファイル（データベース ⇔ GCS）:")
        for file_info in results['exact_matches'][:10]:  # 最初の10件
            print(f"   ID {file_info['id']}: {file_info['original']}")
            print(f"      -> {file_info['path']}")
        if len(results['exact_matches']) > 10:
            print(f"   ... 他 {len(results['exact_matches']) - 10}件")
        print()
    
    # 2. 欠損ファイル
    if results['missing_files']:
        print("❌ 欠損ファイル（データベースにあるがGCSにない）:")
        for file_info in results['missing_files']:
            print(f"   ID {file_info['id']}: {file_info['original']}")
            print(f"      DB想定パス: {file_info['path']}")
            print(f"      サイズ: {file_info['size']} bytes, 日付: {file_info['date']}")
        print()
    
    # 3. 孤立ファイル
    if results['orphaned_files']:
        print("🔸 孤立ファイル（GCSにあるがデータベースにない）:")
        for gcs_path in results['orphaned_files'][:10]:  # 最初の10件
            print(f"   {gcs_path}")
        if len(results['orphaned_files']) > 10:
            print(f"   ... 他 {len(results['orphaned_files']) - 10}件")
        print()
    
    # 4. 重複ファイル分析
    print("🔄 重複ファイル分析（同じ元ファイル名）:")
    duplicates = {k: v for k, v in results['duplicate_originals'].items() if len(v) > 1}
    
    for original_name, versions in duplicates.items():
        print(f"\n📄 元ファイル名: {original_name}")
        print(f"   バージョン数: {len(versions)}")
        
        existing_versions = [v for v in versions if v['exists_in_gcs']]
        missing_versions = [v for v in versions if not v['exists_in_gcs']]
        
        print(f"   GCS存在: {len(existing_versions)}件, 欠損: {len(missing_versions)}件")
        
        if existing_versions:
            print("   ✅ GCS存在バージョン:")
            for v in existing_versions:
                print(f"      ID {v['id']}: {v['path']} ({v['date']})")
        
        if missing_versions:
            print("   ❌ GCS欠損バージョン:")
            for v in missing_versions:
                print(f"      ID {v['id']}: {v['path']} ({v['date']})")
    
    print()
    
    # 5. サイズ分析
    print("📏 ファイルサイズ分析:")
    size_duplicates = {k: v for k, v in results['size_groups'].items() if len(v) > 1}
    
    for file_size, files_with_size in sorted(size_duplicates.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
        print(f"\n📦 サイズ: {file_size} bytes ({len(files_with_size)}件)")
        
        existing_files = [f for f in files_with_size if f['exists_in_gcs']]
        missing_files = [f for f in files_with_size if not f['exists_in_gcs']]
        
        print(f"   GCS存在: {len(existing_files)}件, 欠損: {len(missing_files)}件")
        
        # 元ファイル名を確認
        original_names = list(set(f['original'] for f in files_with_size))
        if len(original_names) == 1:
            print(f"   → 同一ファイル: {original_names[0]}")
        else:
            print(f"   → 異なるファイル: {len(original_names)}種類")

def find_potential_matches():
    """欠損ファイルに対する潜在的な代替候補を検索"""
    print("\n" + "=" * 80)
    print("🔍 欠損ファイルの代替候補検索")
    print("=" * 80)
    
    # この機能は後で実装
    print("（実装中...）")

if __name__ == "__main__":
    results = check_gcs_file_existence()
    if results:
        find_potential_matches()