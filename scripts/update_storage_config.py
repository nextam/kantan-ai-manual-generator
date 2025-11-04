#!/usr/bin/env python3
import sqlite3
import json

def update_company_storage_to_gcs():
    """企業のストレージ設定をGCSに更新"""
    try:
        conn = sqlite3.connect("/app/instance/manual_generator.db")
        cursor = conn.cursor()
        
        # GCS設定
        gcs_config = {
            "bucket_name": "manual_generator",
            "credentials_path": "/app/gcp-credentials.json"
        }
        
        print("=== 企業ストレージ設定をGCSに更新 ===")
        
        # 全ての企業を取得
        cursor.execute("SELECT id, name FROM companies")
        companies = cursor.fetchall()
        
        for company_id, company_name in companies:
            # ストレージ設定を更新
            cursor.execute("""
                UPDATE companies 
                SET storage_type = ?, storage_config = ? 
                WHERE id = ?
            """, ('gcs', json.dumps(gcs_config), company_id))
            
            print(f"✅ 企業 ID {company_id} ({company_name}) のストレージをGCSに更新")
        
        # 変更を保存
        conn.commit()
        print(f"\n🎉 {len(companies)}社のストレージ設定をGCSに更新完了")
        
        # 更新後の確認
        print("\n=== 更新後の企業設定確認 ===")
        cursor.execute("SELECT id, name, storage_type, storage_config FROM companies")
        updated_companies = cursor.fetchall()
        
        for company in updated_companies:
            print(f"Company ID: {company[0]}")
            print(f"  Name: {company[1]}")
            print(f"  Storage Type: {company[2]}")
            print(f"  Storage Config: {company[3]}")
            print("---")
        
        conn.close()
        
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    update_company_storage_to_gcs()