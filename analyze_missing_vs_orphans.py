#!/usr/bin/env python3
"""
欠損ファイルとGCS孤立ファイルの関係性分析
"""
import sqlite3
import os
import difflib

# GCSファイル一覧（手動で設定）
GCS_FILES_RAW = """
gs://manual_generator/video/0053b26c-1303-474c-9b77-8c8fe2dea457_0121____VID_20250620_110857.mp4
gs://manual_generator/video/01d793a4-6cec-4957-b666-d7502829b0f1.mp4
gs://manual_generator/video/021ae5c3-01ff-4d16-838b-972cab5bd11b_0111____VID_20250620_111337.mp4
gs://manual_generator/video/02db000d-9c44-4708-89de-277cb0109c67_VID_20250909_094335.mp4
gs://manual_generator/video/03e27e09-9de9-4181-aad0-7d20b7271a31_VID_20250909_094335.mp4
gs://manual_generator/video/07a76823-700d-4c99-9247-29b0ac03caf3_0222____IMG_0005.MOV
gs://manual_generator/video/0c431212-b91c-43be-916a-89ce5247dff7_0121____VID_20250620_110857.mp4
gs://manual_generator/video/0d262c06-bc61-43bd-837b-a18e9930db88.mp4
gs://manual_generator/video/11533816-1cb5-42d6-b60e-8e98ea04bdd1_250909_094155_sh.mp4
gs://manual_generator/video/129e144d-a5ac-406d-a95b-f5a9fa377f69_0121____VID_20250620_110857.mp4
gs://manual_generator/video/130106a6-8c67-485d-bc96-55214f722a7b.mp4
gs://manual_generator/video/13f09af5-9426-453c-90d3-449a9fe3b062_0111____VID_20250620_111337.mp4
gs://manual_generator/video/1442b937-f16a-40b1-b514-f7495653b6b5_0111____VID_20250620_111337.mp4
gs://manual_generator/video/1704ae0e-1e43-475f-806c-3053f5545489_250909_094155_sh.mp4
gs://manual_generator/video/18100ad9-a237-4a79-a2a7-0cf3ef93878d_1.mp4
gs://manual_generator/video/1b96620601694678bca91a6f6ada3ede_0121____VID_20250620_110857.mp4
gs://manual_generator/video/1d8b3dcc-c06f-4b06-b285-f4f2ef2677d6.mp4
gs://manual_generator/video/2432ff79-3ae8-4ab0-b014-fc56884b67a3_0111____VID_20250620_111337.mp4
gs://manual_generator/video/2c354383-7054-4be3-b593-aca5ce6ce07e_IMG_8499.mov
gs://manual_generator/video/2d087262-136a-444e-a3cc-b1961c158d09_2.mp4
gs://manual_generator/video/2d509e93-6e6b-4a1c-b826-1209d8c62170_2.mp4
gs://manual_generator/video/2da95857-203e-4ddb-b7cf-01d68435d048_0111____VID_20250620_111337.mp4
gs://manual_generator/video/2f4cfa9f-bdd7-4430-baaa-1ce07df87c63.mp4
gs://manual_generator/video/319ca674-957c-4be8-821a-f9fbf1621358_0111____VID_20250620_111337.mp4
gs://manual_generator/video/336b9416-89ee-4986-af91-cfe899cc9f53_250911_164049_sh.mp4
gs://manual_generator/video/3768ab0e-6243-4162-b203-d98af966208f_1.mp4
gs://manual_generator/video/3af64f02-3082-4503-9d52-a47424b4dcad.mp4
gs://manual_generator/video/3c3f93e9-d1d5-4fa6-9f2c-8ed17db555f3_1.mp4
gs://manual_generator/video/3d78e3cf-7d94-459d-a8de-e12e65c59214.mp4
gs://manual_generator/video/425d1e61-4128-4623-ac03-1714987375dd.mp4
gs://manual_generator/video/430f0c820c374b31b3071079e8fc0e4b_0121____VID_20250620_110857.mp4
gs://manual_generator/video/4433263d-b14e-465e-be3b-e66a85813fee.mp4
gs://manual_generator/video/44f7b7a7-e616-4cf3-ace1-6b540bd6f1f1_IMG_8499.mov
gs://manual_generator/video/4649b89f-f380-4093-ba75-b262dbd3b178_0121____VID_20250620_110857.mp4
gs://manual_generator/video/4bc58857-bb47-4113-aa50-1df8c24c3299.mp4
gs://manual_generator/video/4e2a8855-8b22-43ad-88ac-8f1e99bca181_0211____VID_20250620_111723.mp4
gs://manual_generator/video/4e88d17f-3485-4ba6-9c49-8008668826a0.mp4
gs://manual_generator/video/500a7a33-e97b-4fe6-8a99-0e3250f2fe9e_0112____IMG_0003.MOV
gs://manual_generator/video/5cb88d9e-b0b7-4816-9f0d-bdc930031598.mp4
gs://manual_generator/video/63582c7f-1cb4-4aa4-b4c2-7b5b780dfd61_2.mp4
gs://manual_generator/video/64571357-74c0-4e23-85d4-a2d715e13862_IMG_8559.mov
gs://manual_generator/video/64d4e334-9cb1-4770-86b5-46389a6688fa_test_video.mp4
gs://manual_generator/video/69d18996-20b3-4bae-9c5a-3d018efb6cdd_2.mp4
gs://manual_generator/video/6bca3a28-aba5-4516-a808-9a9bc96b83d0.mp4
gs://manual_generator/video/6d0ee797-0600-4823-920d-903f9d2fe284_0112____IMG_0003.MOV
gs://manual_generator/video/6e1b11f4-33a4-45d8-a1e2-f9c1301d3c10.mp4
gs://manual_generator/video/70770462-bd51-46c5-8e49-b8246d28e78a_0221____VID_20250620_111943.mp4
gs://manual_generator/video/7152ee9a-bc20-4a5f-8149-84c6a3c47dd7_0112____IMG_0003.MOV
gs://manual_generator/video/71a753f74a0a4831819d295fe8e69d4f_0111____VID_20250620_111337.mp4
gs://manual_generator/video/797dcdda-112f-42ac-a11d-3ec154a58808_0221____VID_20250620_111943.mp4
gs://manual_generator/video/7c40c879-f730-412e-8b1d-8170fb582614.mp4
gs://manual_generator/video/7f603418-a865-4a9f-85df-d69f9fe8415c.mp4
gs://manual_generator/video/80d5c3bc-527c-4e97-898b-b796498f2f16_0112____IMG_0003.MOV
gs://manual_generator/video/8107bbcc-c706-4396-856b-a2e2807f6715_0122____IMG_0002.MOV
gs://manual_generator/video/81178006-ca31-4265-bc2d-36be1222929b_0111____VID_20250620_111337.mp4
gs://manual_generator/video/8bbf2d14-a9d3-4693-bb6d-145ad6390bae_IMG_8500.mov
gs://manual_generator/video/8d604845-011a-4e83-809f-22836531225e.mp4
gs://manual_generator/video/8ff35861-2697-44df-8b6d-5a1757916b2e_0211____VID_20250620_111723.mp4
gs://manual_generator/video/92a8ea69-1b2f-47b3-8896-98781192b59a_0111____VID_20250620_111337.mp4
gs://manual_generator/video/939a1b96-2d9f-45de-bc50-66bb7855ad94.mp4
gs://manual_generator/video/99d003ce-f4fc-468a-8699-50db469dc165_0121____VID_20250620_110857.mp4
gs://manual_generator/video/9b751476-4878-45b1-acef-c67b4ab955c2_0112____IMG_0003.MOV
gs://manual_generator/video/9c70b4b3-b8e1-42e1-aff5-30a3f0c190df_0111____VID_20250620_111337.mp4
gs://manual_generator/video/9d100d06-103d-43c9-b0a6-e14eea1d5a48_0121____VID_20250620_110857.mp4
gs://manual_generator/video/9da9ffac-cba4-47e9-bd6e-9956fd536221_0112____IMG_0003.MOV
gs://manual_generator/video/9e48e9e1-54a6-4375-aede-0afe82b472bb_0111____VID_20250620_111337.mp4
gs://manual_generator/video/9f40fda8-0b36-4e23-af68-3c1ccddce5d8_0111____VID_20250620_111337.mp4
gs://manual_generator/video/a02b9303-3007-4df4-892c-3b216f935954_IMG_8500.mov
gs://manual_generator/video/a0dc9b35-2c75-4f7b-8008-454dc940f6d5_0111____VID_20250620_111337.mp4
gs://manual_generator/video/a2fe4ef2-4515-4d16-a741-7ad7ed5d6e94_0221____VID_20250620_111943.mp4
gs://manual_generator/video/a4114958-a029-4f6c-9367-caafdce5a23e_IMG_8499.mov
gs://manual_generator/video/a4a7e084-11f9-4414-9e3a-bcafd9acbd23_1.mp4
gs://manual_generator/video/a8cafeb9-e18a-422a-8bac-cb8738bd352b_0211____VID_20250620_111723.mp4
gs://manual_generator/video/a9b47408-903d-469b-857e-3ad03cd7ae49_IMG_8499.mov
gs://manual_generator/video/aaa71f88-dc27-41d8-b2f3-1b05b069ec12_0111____VID_20250620_111337.mp4
gs://manual_generator/video/ab2b5398-a1a6-41da-bc66-f1e42ee836c6_0121____VID_20250620_110857.mp4
gs://manual_generator/video/b01002a8-7e91-4908-86cf-5432aa0da8c5_0221____VID_20250620_111943.mp4
gs://manual_generator/video/b18e0b9a-2bed-46a1-98e7-003a0a6c3118_0111____VID_20250620_111337.mp4
gs://manual_generator/video/b34831e7-9355-421f-93a8-2e409cff96dd_0221____VID_20250620_111943.mp4
gs://manual_generator/video/b7041552-2811-49c0-829a-64a3940f828c.mp4
gs://manual_generator/video/b814c098-3af2-45d2-9408-931802abbbdb_2.MOV
gs://manual_generator/video/b8fb69fa-118b-4469-9f72-df06d04976ea_0221____VID_20250620_111943.mp4
gs://manual_generator/video/ba739621-209f-490e-8b3d-78882e85a794_2.mp4
gs://manual_generator/video/baf9313b-3210-4768-b778-7359ae2ef71a.mp4
gs://manual_generator/video/bb4c3233-ea8b-4e3e-8418-1cf2b85dd991_VID_20250909_094335.mp4
gs://manual_generator/video/bba4aec4-a380-4d1b-bcde-541aecf93b62_0211____VID_20250620_111723.mp4
gs://manual_generator/video/bbafd3efba8043a584789241ea4f5422_0111____VID_20250620_111337.mp4
gs://manual_generator/video/bd10e68d-416a-4476-9722-a9a8f581a2b9.mp4
gs://manual_generator/video/c2599a15-2255-4f9d-822a-4f660ef54737_VID_20250909_094335.mp4
gs://manual_generator/video/c9bcf620-1d24-4df3-bc58-b085ecb6a37f.mp4
gs://manual_generator/video/c9dcfa62-3c57-4c48-8332-429db3a470fa.mp4
gs://manual_generator/video/cb910c3a-1706-4ed2-970e-a34593cba002_VID_20250909_094335.mp4
gs://manual_generator/video/ceb945ac-9765-4a9f-b5d8-814010c7d9f9_2.mp4
gs://manual_generator/video/cf7657db-dddf-4465-92de-3e31c452dbde.mp4
gs://manual_generator/video/cf7d93b6-c304-450d-bed8-eb16db4456b6_IMG_8500.mov
gs://manual_generator/video/cf877700-5ff2-4e3a-80df-f7a652105a7f_0111____VID_20250620_111337.mp4
gs://manual_generator/video/cf91b063-6313-4165-b5af-bf4528305953_IMG_8500.mov
gs://manual_generator/video/d2a333b9-f6bd-42bf-a60d-d35c1932d0f2_IMG_8568.mov
gs://manual_generator/video/d3595455-e417-4f73-a159-3012d19cf634_0121____VID_20250620_110857.mp4
gs://manual_generator/video/d3e902b5-cadb-4553-907d-4fd86aacad20.mp4
gs://manual_generator/video/e04be334-d359-42f6-ba54-2291c8d77f6e_0111____VID_20250620_111337.mp4
gs://manual_generator/video/e36c70a3-8a30-419c-b7c6-0798258d47d2_3.mp4
gs://manual_generator/video/e854e114-2528-42ba-95a2-18619f61674f.mp4
gs://manual_generator/video/ea082dd3-eb10-48bf-801b-9ba3823f111b_0111____VID_20250620_111337.mp4
gs://manual_generator/video/ec834b39-9962-4ebc-a99d-2f234bc4bd5e.mp4
gs://manual_generator/video/f017099e-5a67-4506-a581-2fb624ff974f_0112____IMG_0003.MOV
gs://manual_generator/video/f1b34faa-de47-4905-8cb2-033ad91f9e78_1.MOV
gs://manual_generator/video/f58dfd64-b726-44ce-ad0c-75c7338f7529_0111____VID_20250620_111337.mp4
gs://manual_generator/video/f8edcb02-4381-4c0e-a785-042df5d5e46e_0112____IMG_0003.MOV
"""

def parse_gcs_files():
    """GCSファイル一覧をパース"""
    gcs_files = []
    for line in GCS_FILES_RAW.strip().split('\n'):
        if line.strip() and 'gs://manual_generator/' in line:
            relative_path = line.replace('gs://manual_generator/', '')
            gcs_files.append(relative_path)
    return gcs_files

def analyze_missing_files_vs_orphans():
    """欠損ファイルとGCS孤立ファイルの関係性を詳細分析"""
    print("=== 欠損ファイル vs GCS孤立ファイル 関係性分析 ===")
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
    gcs_files = parse_gcs_files()
    
    # データベースのパスセット
    db_paths = {file_record[3] for file_record in all_files if file_record[3]}
    
    # 欠損ファイルと孤立ファイルを特定
    missing_files = []
    orphaned_files = []
    
    for file_record in all_files:
        file_id, original_name, stored_name, file_path, file_size, upload_date = file_record
        if file_path not in gcs_files:
            missing_files.append({
                'id': file_id,
                'original': original_name,
                'stored': stored_name,
                'path': file_path,
                'size': file_size,
                'date': upload_date
            })
    
    for gcs_path in gcs_files:
        if gcs_path not in db_paths:
            orphaned_files.append(gcs_path)
    
    print(f"📊 欠損ファイル: {len(missing_files)}件")
    print(f"📊 GCS孤立ファイル: {len(orphaned_files)}件")
    print()
    
    # 欠損ファイルの詳細分析
    print("=" * 60)
    print("❌ 欠損ファイル詳細分析")
    print("=" * 60)
    
    for missing in missing_files:
        print(f"\n🔍 ID {missing['id']}: {missing['original']}")
        print(f"   想定パス: {missing['path']}")
        print(f"   サイズ: {missing['size']} bytes")
        print(f"   日付: {missing['date']}")
        
        # パス分析
        missing_path = missing['path']
        missing_filename = missing_path.split('/')[-1] if '/' in missing_path else missing_path
        
        print(f"   ファイル名: {missing_filename}")
        
        # UUIDと拡張子を分離
        if '_' in missing_filename:
            uuid_part = missing_filename.split('_')[0]
            print(f"   UUID: {uuid_part}")
        
        # 拡張子問題の確認
        if missing_filename.endswith('_mp4'):
            corrected_filename = missing_filename.replace('_mp4', '.mp4')
            corrected_path = missing_path.replace('_mp4', '.mp4')
            print(f"   🔧 拡張子修正候補: {corrected_filename}")
            print(f"   🔧 修正パス: {corrected_path}")
            
            # GCSに修正版が存在するか確認
            if corrected_path in gcs_files:
                print(f"   ✅ 修正版がGCSに存在します！")
            else:
                print(f"   ❌ 修正版もGCSに存在しません")
        
        # 類似ファイル検索
        print(f"   🔍 類似ファイル検索:")
        uuid_part = missing_filename.split('_')[0] if '_' in missing_filename else missing_filename[:10]
        
        similar_files = []
        for gcs_file in gcs_files:
            gcs_filename = gcs_file.split('/')[-1] if '/' in gcs_file else gcs_file
            if uuid_part in gcs_filename:
                similar_files.append(gcs_file)
        
        if similar_files:
            print(f"      UUID一致ファイル:")
            for sim_file in similar_files:
                print(f"        - {sim_file}")
        else:
            print(f"      UUID一致ファイルなし")
        
        # 原始ファイル名での検索
        original_part = missing['original'].replace('.mp4', '').replace('.MOV', '').replace('.mov', '')
        partial_matches = []
        
        for gcs_file in gcs_files:
            gcs_filename = gcs_file.split('/')[-1] if '/' in gcs_file else gcs_file
            if any(part in gcs_filename for part in original_part.split('_') if len(part) > 3):
                partial_matches.append(gcs_file)
        
        if partial_matches and not similar_files:
            print(f"      元ファイル名部分一致:")
            for match in partial_matches[:3]:  # 最初の3件
                print(f"        - {match}")
    
    print()
    print("=" * 60)
    print("🔸 GCS孤立ファイル分析（サンプル）")
    print("=" * 60)
    
    # 孤立ファイルのパターン分析
    orphan_patterns = {}
    for orphan in orphaned_files[:20]:  # 最初の20件を分析
        orphan_filename = orphan.split('/')[-1] if '/' in orphan else orphan
        
        # パターン抽出
        if '_' in orphan_filename:
            pattern_parts = orphan_filename.split('_')[1:]  # UUIDを除く
            pattern = '_'.join(pattern_parts)
        else:
            pattern = orphan_filename
        
        if pattern not in orphan_patterns:
            orphan_patterns[pattern] = []
        orphan_patterns[pattern].append(orphan)
    
    print("孤立ファイルのパターン（上位10件）:")
    for pattern, files in sorted(orphan_patterns.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
        print(f"   {pattern}: {len(files)}件")
        for file in files[:2]:  # 最初の2件を表示
            print(f"      - {file}")
        if len(files) > 2:
            print(f"      ... 他 {len(files) - 2}件")
    
    conn.close()

if __name__ == "__main__":
    analyze_missing_files_vs_orphans()