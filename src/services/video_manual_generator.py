"""
動画解析マニュアル生成システム
Gemini (Vertex AI) を使用して動画から作業手順マニュアルを自動生成
"""

import os
import cv2
import json
import base64
import tempfile
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
from dotenv import load_dotenv
import logging
import sys

# Load environment variables
load_dotenv()

# Import GCP config helper
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.gcp_config import get_gcp_project_id

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part
    from google.auth import default
    from google.auth.exceptions import DefaultCredentialsError
    import google.auth.transport.requests
    HAS_VERTEX_AI = True
except ImportError as e:
    HAS_VERTEX_AI = False
    VERTEX_AI_ERROR = str(e)

logger = logging.getLogger(__name__)

def diagnose_vertex_ai_setup(project_id: str = None) -> Dict[str, Any]:
    """
    Vertex AI設定の診断を実行
    
    Args:
        project_id: Google Cloud Project ID
        
    Returns:
        診断結果の辞書
    """
    diagnosis = {
        "timestamp": datetime.now().isoformat(),
        "vertex_ai_available": HAS_VERTEX_AI,
        "project_id": project_id or os.getenv('GOOGLE_CLOUD_PROJECT_ID'),
        "environment_variables": {},
        "authentication": {},
        "credentials_file": {},
        "errors": [],
        "recommendations": []
    }
    
    if not HAS_VERTEX_AI:
        diagnosis["errors"].append(f"Vertex AI libraries not available: {VERTEX_AI_ERROR}")
        diagnosis["recommendations"].append("pip install google-cloud-aiplatform vertexai")
        return diagnosis
    
    # 環境変数チェック
    env_vars = [
        'GOOGLE_APPLICATION_CREDENTIALS',
        'GOOGLE_CLOUD_PROJECT_ID',
        'GOOGLE_CLOUD_PROJECT'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        diagnosis["environment_variables"][var] = {
            "set": value is not None,
            "value": value if value else None,
            "file_exists": False
        }
        
        if value and os.path.isfile(value):
            diagnosis["environment_variables"][var]["file_exists"] = True
            try:
                with open(value, 'r') as f:
                    creds_data = json.load(f)
                    diagnosis["credentials_file"] = {
                        "path": value,
                        "type": creds_data.get("type", "unknown"),
                        "project_id": creds_data.get("project_id", "not_found"),
                        "client_email": creds_data.get("client_email", "not_found"),
                        "has_private_key": "private_key" in creds_data
                    }
            except Exception as e:
                diagnosis["errors"].append(f"Cannot read credentials file {value}: {e}")
    
    # 認証テスト
    try:
        credentials, auth_project = default()
        diagnosis["authentication"]["default_credentials_found"] = True
        diagnosis["authentication"]["project_from_credentials"] = auth_project
        
        # 認証情報の詳細
        if hasattr(credentials, 'service_account_email'):
            diagnosis["authentication"]["service_account_email"] = credentials.service_account_email
        
        # トークン取得テスト
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        diagnosis["authentication"]["token_refresh_success"] = True
        
    except DefaultCredentialsError as e:
        diagnosis["authentication"]["default_credentials_found"] = False
        diagnosis["errors"].append(f"Default credentials not found: {e}")
        diagnosis["recommendations"].append("Set up Google Cloud credentials using 'gcloud auth application-default login' or service account key")
    except Exception as e:
        diagnosis["authentication"]["error"] = str(e)
        diagnosis["errors"].append(f"Authentication error: {e}")
    
    # Vertex AI初期化テスト
    try:
        if diagnosis["project_id"]:
            location = os.getenv('VERTEX_AI_LOCATION', 'us-central1')
            vertexai.init(project=diagnosis["project_id"], location=location)
            diagnosis["vertex_ai_init"] = {"success": True, "location": location}
            
            # モデル初期化テスト
            try:
                model = GenerativeModel("gemini-2.5-pro")
                diagnosis["model_init"] = {"success": True, "model": "gemini-2.5-pro"}
            except Exception as e:
                diagnosis["model_init"] = {"success": False, "error": str(e)}
                diagnosis["errors"].append(f"Model initialization failed: {e}")
        else:
            diagnosis["errors"].append("Project ID not available for Vertex AI initialization")
            
    except Exception as e:
        diagnosis["vertex_ai_init"] = {"success": False, "error": str(e)}
        diagnosis["errors"].append(f"Vertex AI initialization failed: {e}")
    
    # 推奨事項の追加
    if not diagnosis["environment_variables"]["GOOGLE_APPLICATION_CREDENTIALS"]["set"]:
        diagnosis["recommendations"].append("Set GOOGLE_APPLICATION_CREDENTIALS environment variable to service account key file path")
    
    if not diagnosis["project_id"]:
        diagnosis["recommendations"].append("Set GOOGLE_CLOUD_PROJECT_ID environment variable")
    
    return diagnosis

class VideoManualGenerator:
    """動画解析マニュアル生成クラス"""
    
    def __init__(self, project_id: str = None, location: str = None):
        """
        初期化
        
        Args:
            project_id: Google Cloud Project ID (optional, auto-detected from credentials if not provided)
            location: Vertex AI の場所 (optional, reads from env if not provided)
        """
        if not HAS_VERTEX_AI:
            raise RuntimeError(f"Vertex AI libraries are required but not available: {VERTEX_AI_ERROR}")
        
        # Get configuration from environment variables or credentials file
        if project_id:
            self.project_id = project_id
        else:
            try:
                self.project_id = get_gcp_project_id()
            except ValueError as e:
                raise ValueError(f"Failed to determine GCP project ID: {e}")
        
        self.location = location or os.getenv('VERTEX_AI_LOCATION', 'us-central1')
        
        try:
            vertexai.init(project=self.project_id, location=self.location)
            self.model = GenerativeModel("gemini-2.5-pro")
            logger.info(f"Vertex AI初期化成功: project={self.project_id}, location={self.location}")
        except Exception as e:
            if "IAM_PERMISSION_DENIED" in str(e) or "Permission" in str(e):
                raise RuntimeError(
                    f"Vertex AI権限エラー: {e}\n\n"
                    "解決方法:\n"
                    f"1. Google Cloud Consoleでプロジェクト '{self.project_id}' にアクセス\n"
                    "2. Vertex AI APIが有効化されているか確認\n"
                    "3. IAM > サービスアカウントで適切な権限を確認\n"
                    "4. 必要な権限: 'Vertex AI User' または 'aiplatform.endpoints.predict'\n"
                    "5. サービスアカウントキーが正しく設定されているか確認\n"
                    "6. 環境変数 GOOGLE_APPLICATION_CREDENTIALS が正しく設定されているか確認"
                )
            else:
                raise RuntimeError(f"Vertex AI初期化失敗: {e}")

    def extract_key_frames(self, video_path: str, max_frames: int = 12) -> List[Dict]:
        """
        動画からキーフレームを抽出
        
        Args:
            video_path: 動画ファイルパス
            max_frames: 最大フレーム数
            
        Returns:
            フレーム情報のリスト [{"timestamp": float, "frame": np.array, "frame_number": int}]
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"動画ファイルを開けません: {video_path}")
        
        # 動画情報取得
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps
        
        # フレーム間隔計算（均等分割）
        frame_interval = max(1, total_frames // max_frames)
        
        frames = []
        for i in range(0, total_frames, frame_interval):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if ret:
                timestamp = i / fps
                frames.append({
                    "timestamp": timestamp,
                    "frame": frame,
                    "frame_number": i
                })
            
            if len(frames) >= max_frames:
                break
        
        cap.release()
        return frames

    def frame_to_base64(self, frame: np.array) -> str:
        """OpenCVフレームをBase64エンコード（色空間修正付き）"""
        # BGRからRGBに変換してからエンコード
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # エンコード時はBGRに戻す（JPEGエンコードのため）
        _, buffer = cv2.imencode('.jpg', cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
        return base64.b64encode(buffer).decode('utf-8')

    def analyze_video_with_gemini(self, frames: List[Dict]) -> Dict[str, Any]:
        """
        Geminiを使用して動画フレームを解析し、作業手順を抽出
        
        Args:
            frames: フレーム情報のリスト
            
        Returns:
            解析結果 {"steps": [...], "summary": "...", "total_duration": float}
        """
        if not self.model:
            raise RuntimeError("Gemini モデルが初期化されていません")
        
        # フレーム画像をPart形式に変換
        image_parts = []
        for i, frame_info in enumerate(frames):
            base64_image = self.frame_to_base64(frame_info["frame"])
            part = Part.from_data(
                data=base64.b64decode(base64_image),
                mime_type="image/jpeg"
            )
            image_parts.append(part)

        # プロンプト作成
        prompt = """
あなたは製造業の作業手順分析の専門家です。提供された動画フレーム画像から、作業手順を詳細に分析してください。

**重要**: 必ず以下のJSONフォーマットで回答してください。他のテキストは含めず、JSONのみを返してください。

{
  "title": "動画マニュアルのタイトル",
  "steps": [
    {
      "step_number": 1,
      "title": "作業項目名",
      "description": "作業内容の詳細説明",
      "timestamp_start": 0.0,
      "timestamp_end": 5.2,
      "key_points": ["重要ポイント1", "重要ポイント2"],
      "frame_index": 0,
      "safety_notes": "安全上の注意点（あれば）"
    }
  ],
  "summary": "全体作業の概要説明",
  "total_duration": 30.5,
  "work_type": "作業の種類（組立、検査、など）",
  "difficulty_level": "初級",
  "estimated_workers": 1,
  "required_tools": ["必要な工具リスト"]
}

**指示**:
1. 各作業ステップを時系列順に整理
2. 作業内容を具体的かつ分かりやすく記述
3. 安全上重要なポイントを特定
4. 製造業の現場で実際に使用されるマニュアルの品質で作成
5. 日本語で回答
6. **JSONフォーマットを厳密に守り、他のテキストは一切含めない**
"""

        try:
            # Geminiで解析実行
            contents = [prompt] + image_parts
            response = self.model.generate_content(contents)
            
            # レスポンステキストからJSONを抽出
            response_text = response.text.strip() if response.text else ""
            
            # デバッグ：レスポンス内容をログに出力
            logger.info(f"Gemini生レスポンス長: {len(response_text)}")
            logger.info(f"Gemini生レスポンス（最初の500文字）: {response_text[:500]}")
            
            if not response_text:
                logger.error("Geminiからの空のレスポンス")
                raise ValueError("Empty response from Gemini")
            
            # JSONマーカーを除去
            original_text = response_text
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # JSON解析前のログ
            logger.info(f"JSON解析対象テキスト長: {len(response_text)}")
            logger.info(f"JSON解析対象テキスト（最初の200文字）: {response_text[:200]}")
            
            result = json.loads(response_text)
            
            # フレーム情報と結合（JSON serializable形式に変換）
            for step in result.get("steps", []):
                frame_idx = step.get("frame_index", 0)
                if 0 <= frame_idx < len(frames):
                    # numpy arrayをbase64エンコードされた画像に変換
                    frame_image = frames[frame_idx]
                    if frame_image is not None:
                        try:
                            # OpenCVでエンコード（JPEGフォーマット）
                            _, buffer = cv2.imencode('.jpg', frame_image)
                            frame_base64 = base64.b64encode(buffer).decode('utf-8')
                            step["frame_data"] = {
                                "image_base64": frame_base64,
                                "format": "jpeg",
                                "shape": frame_image.shape if hasattr(frame_image, 'shape') else None
                            }
                        except Exception as e:
                            logger.warning(f"フレーム画像の変換に失敗: {e}")
                            step["frame_data"] = None
                    else:
                        step["frame_data"] = None
            
            logger.info("Gemini解析完了")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析エラー: {e}")
            logger.error(f"問題のあるレスポンステキスト: {response_text[:1000] if 'response_text' in locals() else 'No response text'}")
            
            # フォールバック: 基本的なマニュアル構造を返す
            return {
                "title": "動画マニュアル",
                "steps": [
                    {
                        "step_number": 1,
                        "title": "手順1",
                        "description": "Gemini解析でエラーが発生しました。手動で内容を確認してください。",
                        "frame_index": 0,
                        "timestamp": "0:00"
                    }
                ],
                "error": f"JSON解析失敗: {e}"
            }
            
        except Exception as e:
            logger.error(f"Gemini解析エラー: {e}")
            
            # レスポンス内容をログに出力（デバッグ用）
            if 'response_text' in locals():
                logger.error(f"エラー時のレスポンステキスト: {response_text[:1000]}")
            
            # Vertex AI権限エラーの詳細メッセージ
            if "IAM_PERMISSION_DENIED" in str(e) or "Permission" in str(e):
                raise RuntimeError(
                    f"Vertex AI権限エラー: {e}\n\n"
                    "解決方法:\n"
                    f"1. Google Cloud Consoleでプロジェクト '{self.project_id}' にアクセス\n"
                    "2. IAM > サービスアカウントで適切な権限を確認\n"
                    "3. 必要な権限: 'Vertex AI User' または 'aiplatform.endpoints.predict'\n"
                    "4. サービスアカウントキーが正しく設定されているか確認\n"
                    "5. 環境変数 GOOGLE_APPLICATION_CREDENTIALS が正しく設定されているか確認"
                )
            else:
                raise RuntimeError(f"Gemini分析に失敗しました: {e}")

    def generate_manual_data(self, video_path: str) -> Dict[str, Any]:
        """
        動画からマニュアルデータを生成
        
        Args:
            video_path: 動画ファイルパス
            
        Returns:
            マニュアルデータ
        """
        try:
            # 1. キーフレーム抽出
            logger.info(f"動画解析開始: {video_path}")
            frames = self.extract_key_frames(video_path)
            logger.info(f"フレーム抽出完了: {len(frames)}フレーム")
            
            # 2. Gemini解析
            analysis_result = self.analyze_video_with_gemini(frames)
            logger.info("Gemini解析完了")
            
            # 3. メタデータ追加
            manual_data = {
                "video_path": video_path,
                "generated_at": datetime.now().isoformat(),
                "total_frames_extracted": len(frames),
                "analysis_result": analysis_result,
                "status": "success"
            }
            
            return manual_data
            
        except Exception as e:
            logger.error(f"マニュアル生成エラー: {e}")
            return {
                "video_path": video_path,
                "generated_at": datetime.now().isoformat(),
                "error": str(e),
                "status": "error"
            }

    def save_frame_images(self, manual_data: Dict[str, Any], output_dir: str) -> Dict[str, str]:
        """
        フレーム画像をファイルに保存
        
        Args:
            manual_data: マニュアルデータ
            output_dir: 出力ディレクトリ
            
        Returns:
            {"step_number": "image_path", ...}
        """
        os.makedirs(output_dir, exist_ok=True)
        image_paths = {}
        
        steps = manual_data.get("analysis_result", {}).get("steps", [])
        for step in steps:
            frame_data = step.get("frame_data")
            if frame_data and "frame" in frame_data:
                step_num = step["step_number"]
                image_path = os.path.join(output_dir, f"step_{step_num:02d}.jpg")
                
                # フレーム画像を保存
                cv2.imwrite(image_path, frame_data["frame"])
                image_paths[step_num] = image_path
                
                # メタデータに画像パスを追加
                step["image_path"] = image_path
        
        return image_paths
