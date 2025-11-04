#!/usr/bin/env python3
import os
import sys
sys.path.append('/app')

def test_jst_conversion():
    """JST変換をテスト"""
    try:
        print("=== JST変換テスト ===")
        
        from models import utc_to_jst_isoformat
        from datetime import datetime, timezone
        
        # テストデータ（UTC時刻）
        utc_time = datetime(2025, 9, 24, 3, 0, 0, tzinfo=timezone.utc)
        
        # JST変換テスト
        jst_str = utc_to_jst_isoformat(utc_time)
        print(f"UTC: {utc_time}")
        print(f"JST: {jst_str}")
        
        # 実際のマニュアルデータでテスト
        print("\n=== 実データテスト ===")
        
        from app import app
        from models import Manual
        
        with app.app_context():
            # 最新のマニュアルを1件取得
            manual = Manual.query.order_by(Manual.created_at.desc()).first()
            
            if manual:
                print(f"マニュアルID: {manual.id}")
                print(f"タイトル: {manual.title}")
                print(f"作成日時（UTC）: {manual.created_at}")
                print(f"作成日時（JST）: {utc_to_jst_isoformat(manual.created_at)}")
                
                # to_dict_summary の出力確認
                summary = manual.to_dict_summary()
                print(f"to_dict_summary created_at: {summary['created_at']}")
            else:
                print("マニュアルデータが見つかりません")
                
    except Exception as e:
        print(f"テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_jst_conversion()