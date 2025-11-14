"""
API経由でマニュアル生成をテストし、画像抽出を検証するスクリプト
"""
import sys
import os
import time
import json
import requests
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 設定
BASE_URL = "http://localhost:5000"
LOGIN_EMAIL = "support@career-survival.com"
LOGIN_PASSWORD = "0000"
VIDEO_PATH = r"G:\共有ドライブ\CareerSurvival-all\customer\中部電力様\オカタ産業様\動画_オカタ産業様_20250620\検証用動画\0222_ビス打ち_若手_固定カメラ_IMG_0005.MOV"

def login():
    """ログイン"""
    print("=" * 80)
    print("📝 ログイン中...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": LOGIN_EMAIL,
            "password": LOGIN_PASSWORD
        }
    )
    
    if response.status_code == 200:
        print("✅ ログイン成功")
        # Cookieからセッション情報を取得
        return response.cookies
    else:
        print(f"❌ ログイン失敗: {response.status_code}")
        print(response.text)
        return None

def upload_video(cookies):
    """動画アップロード"""
    print("=" * 80)
    print("📤 動画アップロード中...")
    
    if not os.path.exists(VIDEO_PATH):
        print(f"❌ 動画ファイルが見つかりません: {VIDEO_PATH}")
        return None
    
    file_size = os.path.getsize(VIDEO_PATH)
    print(f"📹 ファイル: {os.path.basename(VIDEO_PATH)}")
    print(f"📊 サイズ: {file_size / 1024 / 1024:.2f} MB")
    
    with open(VIDEO_PATH, 'rb') as f:
        files = {'file': (os.path.basename(VIDEO_PATH), f, 'video/quicktime')}
        response = requests.post(
            f"{BASE_URL}/api/manuals/upload-file",
            files=files,
            cookies=cookies
        )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ アップロード成功")
        print(f"📍 URI: {data.get('gcs_uri')}")
        return data.get('gcs_uri')
    else:
        print(f"❌ アップロード失敗: {response.status_code}")
        print(response.text)
        return None

def create_manual(cookies, video_uri):
    """マニュアル生成"""
    print("=" * 80)
    print("🔄 マニュアル生成リクエスト送信中...")
    
    response = requests.post(
        f"{BASE_URL}/api/manuals/generate",
        json={
            "title": "TEST - Image Extraction Debug",
            "video_uri": video_uri,
            "output_format": "text_with_images",
            "use_rag": False,
            "template_ids": []
        },
        cookies=cookies
    )
    
    if response.status_code in [200, 201, 202]:
        data = response.json()
        
        # レスポンスが配列形式の場合
        if 'manuals' in data and isinstance(data['manuals'], list) and len(data['manuals']) > 0:
            first_manual = data['manuals'][0]
            manual_id = first_manual.get('id')
            job_id = first_manual.get('job_id')
        else:
            # 単一オブジェクト形式の場合
            manual_id = data.get('manual_id')
            job_id = data.get('job_id')
        
        print(f"✅ 生成リクエスト成功")
        print(f"📋 Manual ID: {manual_id}")
        print(f"🔧 Job ID: {job_id}")
        return manual_id, job_id
    else:
        print(f"❌ 生成リクエスト失敗: {response.status_code}")
        print(response.text)
        return None, None

def check_job_status(cookies, job_id):
    """ジョブステータス確認（タイムアウト: 2分）"""
    print("=" * 80)
    print(f"⏳ ジョブステータス確認中 (Job ID: {job_id}, タイムアウト: 120秒)...")
    
    # 初回は少し待つ（ジョブが開始されるまで）
    time.sleep(3)
    
    max_attempts = 24  # 24回 × 5秒 = 120秒（2分）
    attempt = 0
    none_count = 0  # Status が None の連続回数
    
    while attempt < max_attempts:
        try:
            response = requests.get(
                f"{BASE_URL}/api/jobs/{job_id}",
                cookies=cookies,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('job_status')
                progress = data.get('progress', 0)
                current_step = data.get('current_step', '')
                
                print(f"📊 [{attempt+1}/{max_attempts}] Status: {status} | Progress: {progress}% | Step: {current_step}")
                
                if status == 'completed':
                    print("✅ ジョブ完了")
                    return True
                elif status == 'failed':
                    print(f"❌ ジョブ失敗: {data.get('error_message')}")
                    return False
                elif status is None or status == 'pending':
                    none_count += 1
                    if none_count >= 10:  # 50秒経過してもNoneのまま
                        print(f"⚠️ ワーカーがジョブを開始していない可能性があります")
                        print(f"⚠️ Celeryワーカーが起動しているか確認してください")
                        return False
                else:
                    none_count = 0  # ステータスが変わったらリセット
                
                time.sleep(5)
                attempt += 1
            else:
                print(f"❌ ステータス取得失敗: {response.status_code}")
                return False
        except Exception as e:
            print(f"⚠️ リクエストエラー: {e}")
            time.sleep(5)
            attempt += 1
    
    print(f"❌ タイムアウト: 120秒経過 - ジョブが完了しませんでした")
    print(f"💡 ヒント: Celeryワーカーが起動していない可能性があります")
    return False

def check_manual_images(manual_id):
    """マニュアルの画像データを確認"""
    from src.core.app import app
    from src.models.models import db, Manual
    
    print("=" * 80)
    print(f"🔍 Manual ID {manual_id} の画像データを確認中...")
    
    with app.app_context():
        manual = Manual.query.get(manual_id)
        
        if not manual:
            print(f"❌ Manual ID {manual_id} が見つかりません")
            return False
        
        print(f"📋 Title: {manual.title}")
        print(f"🏷️  Type: {manual.manual_type}")
        print(f"📊 Format: {manual.output_format}")
        print(f"✅ Status: {manual.generation_status}")
        
        # content フィールド確認
        if manual.content:
            try:
                content_str = manual.content.replace("'", '"').replace('None', 'null').replace('True', 'true').replace('False', 'false')
                content_dict = json.loads(content_str)
                
                if 'analysis_result' in content_dict:
                    analysis = content_dict['analysis_result']
                    steps = analysis.get('steps', [])
                    print(f"\n📄 Content Field:")
                    print(f"  - Steps: {len(steps)}")
                    
                    frame_data_count = 0
                    for step in steps:
                        if step.get('frame_data'):
                            frame_data_count += 1
                            image_base64 = step['frame_data'].get('image_base64', '')
                            print(f"  - Step {step['step_number']}: frame_data あり ({len(image_base64)} bytes)")
                    
                    if frame_data_count > 0:
                        print(f"✅ {frame_data_count} 個のフレームに画像データあり")
                    else:
                        print(f"❌ frame_data が空です")
                        return False
            except Exception as e:
                print(f"❌ Content parse error: {e}")
                return False
        else:
            print("❌ Content is NULL")
            return False
        
        # extracted_images フィールド確認
        print(f"\n🖼️  Extracted Images Field:")
        extracted_images = manual.get_extracted_images()
        if extracted_images:
            print(f"  ✅ Count: {len(extracted_images)}")
            for idx, img in enumerate(extracted_images):
                print(f"  - Image {idx + 1}: {img.get('step_title')} (URI length: {len(img.get('image_uri', ''))})")
            return True
        else:
            print(f"  ❌ Extracted Images is NULL or empty")
            return False

def check_celery_worker():
    """Celeryワーカーが起動しているか確認"""
    print("=" * 80)
    print("🔍 Celeryワーカーの状態確認中...")
    
    try:
        # Redis接続確認（Celeryのブローカー）
        import redis
        r = redis.Redis(host='localhost', port=6379, db=1)  # Celeryは db=1 を使用
        r.ping()
        print("✅ Redis接続: OK (db=1)")
    except Exception as e:
        print(f"❌ Redis接続: NG - {e}")
        print(f"💡 Redis を起動してください: docker-compose up -d redis")
        return False
    
    # Celery inspect でワーカー確認
    try:
        from celery import Celery
        celery_app = Celery('manual_generator', broker='redis://localhost:6379/1')  # db=1
        inspect = celery_app.control.inspect(timeout=5.0)
        active_workers = inspect.active()
        
        if active_workers:
            print(f"✅ Celeryワーカー: {len(active_workers)} worker(s) 起動中")
            for worker_name in active_workers.keys():
                print(f"   - {worker_name}")
            return True
        else:
            print(f"❌ Celeryワーカー: 起動していません")
            print(f"💡 ワーカーを起動してください: start_celery_worker.bat")
            return False
    except Exception as e:
        print(f"⚠️ Celeryワーカー確認エラー: {e}")
        print(f"💡 ワーカーが起動していない可能性があります")
        return False

def main():
    """メイン処理"""
    print("🚀 マニュアル生成テスト開始")
    
    # 0. Celeryワーカー確認
    if not check_celery_worker():
        print("\n❌ テスト中止: Celeryワーカーを起動してから再実行してください")
        return
    
    # 1. ログイン
    cookies = login()
    if not cookies:
        return
    
    # 2. 動画アップロード
    video_uri = upload_video(cookies)
    if not video_uri:
        return
    
    # 3. マニュアル生成
    manual_id, job_id = create_manual(cookies, video_uri)
    if not manual_id or not job_id:
        return
    
    # 4. ジョブステータス確認
    if not check_job_status(cookies, job_id):
        return
    
    # 5. 画像データ確認
    success = check_manual_images(manual_id)
    
    print("=" * 80)
    if success:
        print("🎉 テスト成功: 画像が正常に抽出されました")
    else:
        print("❌ テスト失敗: 画像抽出に問題があります")
        print("\n🔧 デバッグ情報:")
        print(f"   - Manual ID: {manual_id}")
        print(f"   - ログファイルを確認してください")

if __name__ == '__main__':
    main()
