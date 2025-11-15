"""
企業認証対応版 Manual Generator アプリケーション
"""

import json
import os
import uuid
import time
import asyncio
import logging
import requests
import threading
import tempfile
import base64
import io
from pathlib import Path
from datetime import datetime, timezone, timedelta

from flask import Flask, request, render_template, jsonify, send_from_directory, session, g, redirect, url_for, Response, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from PIL import Image

# ロギング設定
import os
from datetime import datetime
log_dir = os.getenv('LOG_DIR', 'logs')
os.makedirs(log_dir, exist_ok=True)
# サーバー起動ごとに新しいログファイルを作成
log_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
# 環境変数に保存してCeleryワーカーと共有
os.environ['LOG_TIMESTAMP'] = log_timestamp
log_file_path = os.path.join(log_dir, f'app_{log_timestamp}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Google Cloud(Storage) と Gemini(API) のみを使用 (VertexAI SDK は非採用)
print("=== GCS & Gemini ライブラリインポート開始 ===")
try:
    from google.cloud import storage  # type: ignore
    from google import genai  # type: ignore  # new google-genai library
    from google.genai import types  # type: ignore
    print("[OK] google.cloud.storage import successful")
    print("[OK] google-genai (google.genai) import successful")
    HAS_GOOGLE_CLOUD = True
except ImportError as e:
    print(f"❌ 必要ライブラリ不足: {e}")
    HAS_GOOGLE_CLOUD = False

# 新しい認証・データベースシステム
try:
    from src.models.models import db, Company, User, UploadedFile, Manual, ManualSourceFile, SuperAdmin, ActivityLog
    from sqlalchemy import func
    from src.middleware.auth import AuthManager, CompanyManager, require_role, init_auth_routes
    from src.infrastructure.file_manager import create_file_manager  
    from flask_login import current_user, login_required, login_user, logout_user
    HAS_AUTH_SYSTEM = True
    logger.info("認証システムのインポートが成功しました")
except Exception as e:
    logger.error(f"設定エラー: {e}")
    HAS_AUTH_SYSTEM = False
    # 代替定義
    class Manual:
        def __init__(self):
            self.id = None
            self.title = ""
            self.content = ""
            self.created_at = datetime.now()
            self.updated_at = datetime.now()
    
    class UploadedFile:
        def __init__(self):
            self.id = None
            self.filename = ""
            self.file_path = ""
            self.created_at = datetime.now()
    
    current_user = None
    def login_required(f):
        return f
    HAS_AUTH_SYSTEM = False
    # 代替定義
    class Manual:
        def __init__(self):
            self.id = None
            self.title = ""
            self.content = ""
            self.created_at = datetime.now()
            self.updated_at = datetime.now()
    
    class UploadedFile:
        def __init__(self):
            self.id = None
            self.filename = ""
            self.file_path = ""
            self.created_at = datetime.now()
    
    current_user = None
    def login_required(f):
        return f

# Gemini統合サービスをインポート
try:
    from src.services.gemini_service import GeminiUnifiedService
    HAS_GEMINI_SERVICE = True
except ImportError:
    print("Warning: Gemini統合サービスをインポートできませんでした。基本機能のみ利用可能です。")
    HAS_GEMINI_SERVICE = False

# 動画マニュアル生成システムをインポート
try:
    from src.services.video_manual_with_images_generator import ManualWithImagesGenerator
    HAS_VIDEO_MANUAL = True
    print("[OK] Video manual generation system import successful (relative import)")
except ImportError as e:
    print(f"❌ 動画マニュアル生成システムをインポートできませんでした: {e}")
    HAS_VIDEO_MANUAL = False
    VIDEO_MANUAL_ERROR = str(e)

# 日本時間変換ユーティリティ
JST = timezone(timedelta(hours=9))

def utc_to_jst(utc_dt):
    """UTC日時を日本時間に変換"""
    if utc_dt is None:
        return None
    
    if isinstance(utc_dt, str):
        # ISO形式の文字列をdatetimeオブジェクトに変換
        utc_dt = datetime.fromisoformat(utc_dt.replace('Z', '+00:00'))
    
    if utc_dt.tzinfo is None:
        # タイムゾーン情報がない場合はUTCとして扱う
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    
    # JSTに変換（UTC+9時間）
    jst_dt = utc_dt.astimezone(JST)
    return jst_dt

def datetime_to_jst_isoformat(dt):
    """日本時間のISO形式文字列を返す"""
    if dt is None:
        return None
    
    # UTCからJSTに変換
    jst_dt = utc_to_jst(dt)
    if jst_dt is None:
        return None
    
    # 確実にタイムゾーン情報付きの文字列を生成
    # もしタイムゾーン情報がない場合は手動で追加
    iso_str = jst_dt.strftime('%Y-%m-%dT%H:%M:%S.%f+09:00')
    return iso_str

def rotate_image_data_url(data_url, rotation_degrees):
    """
    Data URLの画像を指定した角度で回転し、新しいData URLを返す
    
    Args:
        data_url (str): 元画像のdata URL (data:image/...;base64,...)
        rotation_degrees (int): 回転角度 (0, 90, 180, 270)
    
    Returns:
        str: 回転後の画像のdata URL
    """
    logger.info(f"画像回転関数開始: rotation_degrees={rotation_degrees}")
    
    if rotation_degrees % 90 != 0 or rotation_degrees < 0 or rotation_degrees >= 360:
        raise ValueError("回転角度は0, 90, 180, 270度のいずれかである必要があります")
    
    if rotation_degrees == 0:
        logger.info("回転角度が0度のため、そのまま返却")
        return data_url  # 回転なしの場合はそのまま返す
    
    try:
        # Data URLから画像データを抽出
        if not data_url.startswith('data:image/'):
            raise ValueError("無効なdata URL形式です")
        
        # MIMEタイプとbase64データを分離
        header, base64_data = data_url.split(',', 1)
        mime_type = header.split(';')[0].split(':')[1]
        logger.info(f"画像MIME type: {mime_type}")
        
        # Base64デコード
        image_data = base64.b64decode(base64_data)
        logger.info(f"画像データサイズ: {len(image_data)} bytes")
        
        # PIL Imageで開く
        image = Image.open(io.BytesIO(image_data))
        logger.info(f"元画像サイズ: {image.size}, モード: {image.mode}")
        
        # 回転処理 (時計回りで回転)
        # PILのrotateメソッドは反時計回りなので、マイナス値にする
        rotated_image = image.rotate(-rotation_degrees, expand=True)
        logger.info(f"回転後画像サイズ: {rotated_image.size}")
        
        # 回転後の画像をBase64エンコード
        output_buffer = io.BytesIO()
        
        # 元の画像形式を維持
        image_format = 'JPEG'
        if mime_type == 'image/png':
            image_format = 'PNG'
        elif mime_type == 'image/webp':
            image_format = 'WEBP'
        logger.info(f"保存形式: {image_format}")
        
        # RGBAモードの画像をJPEGで保存する場合は、RGBに変換
        if image_format == 'JPEG' and rotated_image.mode in ['RGBA', 'LA']:
            logger.info("RGBAからRGBに変換")
            # 白い背景で合成
            background = Image.new('RGB', rotated_image.size, (255, 255, 255))
            if rotated_image.mode == 'RGBA':
                background.paste(rotated_image, mask=rotated_image.split()[-1])  # alphaチャンネルでマスク
            else:
                background.paste(rotated_image)
            rotated_image = background
        
        rotated_image.save(output_buffer, format=image_format, quality=95)
        logger.info(f"保存完了、サイズ: {len(output_buffer.getvalue())} bytes")
        
        # 新しいdata URLを生成
        rotated_base64 = base64.b64encode(output_buffer.getvalue()).decode()
        new_data_url = f"data:{mime_type};base64,{rotated_base64}"
        logger.info("新しいdata URL生成完了")
        
        return new_data_url
        
    except Exception as e:
        logger.error(f"画像回転エラー: {e}")
        raise Exception(f"画像回転に失敗しました: {str(e)}")

# Flaskアプリケーション初期化
# テンプレートとstaticフォルダのパスを明示的に指定
import os
from pathlib import Path

# src/core/app.pyから見たsrcディレクトリのパスを取得
src_dir = Path(__file__).parent.parent
template_folder = str(src_dir / 'templates')
static_folder = str(src_dir / 'static')

app = Flask(__name__, 
            template_folder=template_folder,
            static_folder=static_folder)
CORS(app)

# 設定
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

# Template context processor
@app.context_processor
def inject_user_info():
    """
    Inject user authentication info into all templates
    """
    from flask import session
    
    user_info = {
        'is_super_admin': session.get('is_super_admin', False),
        'super_admin_username': session.get('super_admin_username'),
        'company_id': session.get('company_id'),
        'company_name': session.get('company_name'),
        'username': session.get('username'),
        'user_role': session.get('user_role'),
        'user_id': session.get('user_id')
    }
    
    return dict(user_info=user_info)
# 最大リクエストサイズを10GBに増やす（画像付きマニュアル対応）
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024  # 10GB制限
logger.info(f"Flask MAX_CONTENT_LENGTH設定: {app.config['MAX_CONTENT_LENGTH'] / 1024 / 1024 / 1024:.1f} GB")

# Werkzeug用の追加設定
try:
    from werkzeug.serving import WSGIRequestHandler
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    
    # Werkzeugの413エラーを根本的に解決
    import werkzeug.formparser
    import werkzeug.exceptions
    
    # MultiPartParser.parseをパッチ
    original_multipart_parse = werkzeug.formparser.MultiPartParser.parse
    
    def bypass_413_parse(self, stream, boundary, content_length):
        """413エラーをバイパスするparseメソッド"""
        try:
            # オリジナルのparse実行
            return original_multipart_parse(self, stream, boundary, content_length)
        except werkzeug.exceptions.RequestEntityTooLarge:
            logger.warning(f"Werkzeugの413制限をバイパス中 - content_length: {content_length}")
            
            # 手動でフォームデータをパース
            from werkzeug.formparser import parse_form_data
            from werkzeug.datastructures import MultiDict, FileStorage
            import io
            
            # ストリームを読み取り
            if hasattr(stream, 'seek'):
                stream.seek(0)
            data = stream.read()
            stream = io.BytesIO(data)
            
            # 境界線を使ってマニュアル解析
            boundary_bytes = boundary.encode() if isinstance(boundary, str) else boundary
            parts = data.split(b'--' + boundary_bytes)
            
            form = MultiDict()
            files = MultiDict()
            
            for part in parts[1:-1]:  # 最初と最後の部分をスキップ
                if b'\r\n\r\n' in part:
                    headers_section, content = part.split(b'\r\n\r\n', 1)
                    headers_str = headers_section.decode('utf-8', errors='ignore')
                    
                    # Content-Dispositionヘッダーを解析
                    if 'Content-Disposition: form-data' in headers_str:
                        name_match = headers_str.split('name="')[1].split('"')[0] if 'name="' in headers_str else None
                        if name_match:
                            # 改行を除去
                            content_clean = content.rstrip(b'\r\n')
                            form[name_match] = content_clean.decode('utf-8', errors='ignore')
            
            return form, files
    
    # パッチ適用
    werkzeug.formparser.MultiPartParser.parse = bypass_413_parse
    
    # デフォルトストリームファクトリも大容量対応
    def large_stream_factory(total_content_length=None, content_type=None, filename=None, content_length=None):
        import tempfile
        return tempfile.SpooledTemporaryFile(max_size=10*1024*1024*1024, mode='w+b')
    
    werkzeug.formparser.default_stream_factory = large_stream_factory
    
    logger.info("Werkzeug設定を大容量対応に変更しました")
except Exception as werkzeug_config_error:
    logger.warning(f"Werkzeug設定変更に失敗: {werkzeug_config_error}")

# セッション設定
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# 413エラー（Request Entity Too Large）のカスタムハンドラー
@app.errorhandler(413)
def request_entity_too_large(error):
    """413エラーのカスタムハンドラー"""
    content_length = request.content_length
    max_content_length = app.config.get('MAX_CONTENT_LENGTH', 'Unknown')
    
    logger.error(f"413 Request Entity Too Large エラー発生")
    logger.error(f"リクエストサイズ: {content_length} bytes ({content_length / 1024 / 1024:.2f} MB)" if content_length else "リクエストサイズ: Unknown")
    logger.error(f"設定されている最大サイズ: {max_content_length / 1024 / 1024 / 1024:.1f} GB" if isinstance(max_content_length, int) else f"最大サイズ設定: {max_content_length}")
    logger.error(f"リクエストURL: {request.url}")
    logger.error(f"リクエストメソッド: {request.method}")
    logger.error(f"Content-Type: {request.content_type}")
    
    return jsonify({
        'success': False,
        'error': f'アップロードサイズが大きすぎます。最大{max_content_length / 1024 / 1024 / 1024:.1f}GBまでです。' if isinstance(max_content_length, int) else 'アップロードサイズが大きすぎます。'
    }), 413

# データベース設定
# データベース設定
# 環境変数から直接パスを取得するか、コンテナ/ローカル環境に応じてパスを設定
database_path_env = os.getenv('DATABASE_PATH')
if database_path_env:
    # 環境変数で指定されている場合 - 絶対パスに変換
    db_path = os.path.abspath(database_path_env)
    instance_dir = os.path.dirname(db_path)
elif os.path.exists('/app'):
    # コンテナ環境
    instance_dir = '/instance'
    db_path = '/instance/manual_generator.db'
    base_dir = '/app'
else:
    # ローカル環境
    instance_dir = os.path.join(os.getcwd(), 'instance')
    db_path = os.path.abspath(os.path.join(instance_dir, 'manual_generator.db'))
    base_dir = os.getcwd()

os.makedirs(instance_dir, exist_ok=True)  # instanceディレクトリを確実に作成
print(f"Instance directory: {instance_dir}")
print(f"Instance directory exists: {os.path.exists(instance_dir)}")
print(f"Instance directory is writable: {os.access(instance_dir, os.W_OK)}")

# Database Configuration: Use DATABASE_URL from environment or default to SQLite
database_url = os.getenv('DATABASE_URL', f'sqlite:///{db_path}')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 認証システム初期化
if HAS_AUTH_SYSTEM:
    db.init_app(app)
    auth_manager = AuthManager(app)
    app.auth_manager = auth_manager  # アプリケーションにauth_managerを設定

# リクエストサイズログ用ミドルウェア
@app.before_request
def log_request_info():
    """リクエスト前のログ出力"""
    if request.endpoint and 'edit' in request.endpoint and request.method == 'POST':
        content_length = request.content_length
        logger.info(f"=== POST Request to {request.endpoint} ===")
        logger.info(f"Content-Length: {content_length} bytes ({content_length / 1024 / 1024:.2f} MB)" if content_length else "Content-Length: Unknown")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
        logger.info(f"Flask MAX_CONTENT_LENGTH: {app.config.get('MAX_CONTENT_LENGTH', 'Not set')}")

# 環境変数の読み込み
load_dotenv()

# Google Cloud設定（条件付き）
if HAS_GOOGLE_CLOUD:
    # 環境変数をクリアして.envファイルから再読み込み
    if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
        del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
    
    # .envファイルから認証ファイルパスを取得（デフォルトは正しいファイル名）
    credentials_file = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'gcp-credentials.json')
    
    # 相対パスの場合はプロジェクトルートからの絶対パスに変換
    if not os.path.isabs(credentials_file):
        # src/core/app.py から見たプロジェクトルートは2階層上
        project_root = Path(__file__).parent.parent.parent
        credentials_path = str(project_root / credentials_file)
    else:
        credentials_path = credentials_file
    
    # 環境変数に絶対パスを強制的に設定（既存の値があっても上書き）
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
    
    # Google Cloud Project IDを.envから取得して設定
    project_id = os.getenv('PROJECT_ID') or os.getenv('GOOGLE_CLOUD_PROJECT_ID')
    if project_id:
        os.environ['GOOGLE_CLOUD_PROJECT_ID'] = project_id
        os.environ['PROJECT_ID'] = project_id
    
    # 設定確認ログ
    print(f"[CONFIG] Google Cloud credentials file (forced): {credentials_path}")
    print(f"[CHECK] File exists: {os.path.exists(credentials_path)}")
    print(f"[INFO] PROJECT_ID: {os.environ.get('PROJECT_ID')}")
    
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    # google-genai では従来の genai.configure は存在しないため呼び出さない。
    # APIキーは get_gemini_client() 内で Client(api_key=...) 生成時に使用する。
    # ここではキー存在のみログ出力（セキュリティ上マスク）。
    if GOOGLE_API_KEY:
        logger.info("GOOGLE_API_KEY 検出 (値はマスク済) - get_gemini_client で使用予定")
    else:
        logger.warning("GOOGLE_API_KEY 未設定: 生成機能はフォールバック動作になります")
    
    # Google Cloud設定
    # Environment-based bucket selection: development → -dev, production → -live
    environment = os.getenv('ENVIRONMENT', 'development')
    if environment == 'production':
        GCS_BUCKET_NAME = 'kantan-ai-manual-generator-live'
    else:
        GCS_BUCKET_NAME = 'kantan-ai-manual-generator-dev'
    
    PROJECT_ID = os.getenv('PROJECT_ID', 'kantan-ai-database')
    
    logger.info(f"GCS Configuration: environment={environment}, bucket={GCS_BUCKET_NAME}")
    
    # GCSをデフォルトストレージとして設定
    DEFAULT_STORAGE_TYPE = 'gcs'
    DEFAULT_STORAGE_CONFIG = {
        'bucket_name': GCS_BUCKET_NAME,
        'credentials_path': credentials_path
    }
else:
    # ローカルストレージをフォールバック
    DEFAULT_STORAGE_TYPE = 'local'
    DEFAULT_STORAGE_CONFIG = {
        'base_path': 'uploads'
    }
    print("Google Cloud機能は無効です - ローカルストレージを使用")

def get_max_tokens_for_version(version):
    """Geminiバージョンに応じた最大出力トークン数を返す"""
    if version == "gemini-2.5-pro":
        return 65535
    else:  # gemini-2.5-flash or default
        return 65535

# === Gemini (google-genai) ヘルパー ===
_GENAI_CLIENT = None
_GENAI_FILE_CACHE = {}  # { original_uri_or_path: uploaded_file_name }

def find_alternative_video_file(video_path):
    """存在しないビデオファイルの代替候補を検索する"""
    try:
        # パスからファイル名を抽出
        if '/' in video_path:
            filename = video_path.split('/')[-1]
        else:
            filename = video_path
        
        # UUIDとファイル名部分を分離
        if '_' in filename:
            parts = filename.split('_', 1)
            if len(parts) > 1:
                original_part = parts[1]
                
                # 同じ元ファイル名の最新版を検索
                from src.models.models import UploadedFile
                
                # 元ファイル名を推測（UUIDプレフィックスを除去）
                # 例: "0111____VID_20250620_111337.mp4" -> "0111_ボルト締結_熟練者_スマートグラス_VID_20250620_111337.mp4"
                if original_part.startswith('0111____'):
                    original_name = "0111_ボルト締結_熟練者_スマートグラス_VID_20250620_111337.mp4"
                    
                    alternatives = UploadedFile.query.filter(
                        UploadedFile.original_filename == original_name
                    ).order_by(UploadedFile.uploaded_at.desc()).all()
                    
                    # ファイルマネージャーで実際に存在するファイルを確認
                    file_manager = get_file_manager()
                    
                    for alt in alternatives:
                        if alt.file_path and file_manager.file_exists(alt.file_path):
                            logger.info(f"Alternative file found and verified: {alt.file_path}")
                            return alt.file_path
                    
                    logger.warning(f"No existing alternative found for 0111 pattern: {filename}")
                
                # 一般的なパターンマッチング（存在確認付き）
                alternatives = UploadedFile.query.filter(
                    UploadedFile.stored_filename.like(f"%{original_part}")
                ).order_by(UploadedFile.uploaded_at.desc()).all()
                
                file_manager = get_file_manager()
                
                for alt in alternatives:
                    if alt.file_path and file_manager.file_exists(alt.file_path):
                        logger.info(f"Alternative file found and verified: {alt.file_path}")
                        return alt.file_path
        
        logger.warning(f"No alternative found for: {video_path}")
        return None
        
    except Exception as e:
        logger.error(f"Error finding alternative file: {e}")
        return None


def get_gemini_client():
    """Vertex モードを強制して google-genai Client を返す。

    優先順位:
      1. Vertex モード (サービスアカウント / GOOGLE_CLOUD_PROJECT_ID & LOCATION)
      2. フォールバック: APIキー (Developer API) ※基本は使用しない想定
    """
    global _GENAI_CLIENT
    if not HAS_GOOGLE_CLOUD:
        return None
    if _GENAI_CLIENT is not None:
        return _GENAI_CLIENT

    project = os.getenv('GOOGLE_CLOUD_PROJECT_ID') or os.getenv('PROJECT_ID') or os.getenv('GOOGLE_CLOUD_PROJECT')
    location = os.getenv('VERTEX_AI_LOCATION', 'us-central1')

    try:
        if project:
            logger.info(f"Vertexモードで Gemini クライアント初期化: project={project} location={location}")
            _GENAI_CLIENT = genai.Client(vertexai=True, project=project, location=location)
            return _GENAI_CLIENT
        else:
            logger.warning("Vertex用 project が未設定のため APIキーモードへフォールバック")
    except Exception as ve:
        logger.error(f"Vertex モード初期化失敗 (APIキーへフォールバック): {ve}")

    # フォールバック: APIキー
    api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("Vertex も APIキー も設定が無いため Gemini クライアント初期化不可")
        return None
    try:
        _GENAI_CLIENT = genai.Client(api_key=api_key)
        logger.info("Developer API (APIキー) モードで Gemini クライアント初期化 (フォールバック)")
        return _GENAI_CLIENT
    except Exception as e:
        logger.error(f"Developer API モード初期化失敗: {e}")
        return None

def map_model_name(version: str) -> str:
    """常に最新版 gemini-2.5-pro を使用 (要件により強制)。"""
    return 'gemini-2.5-pro'

def generate_text_from_video(video_uri: str, prompt: str, config: dict) -> str:
    """動画/gs:// URI からテキスト生成 (google-genai)。

    ポリシー変更: Gemini Developer API は任意 private GCS 動画の直接参照 (gs:// ... MOV/MP4) を現状サポートしないため、常にローカルへダウンロードして files.upload 方式に統一する。
    これにより "Unsupported file uri" 400 を排除する。

    改善点:
      - files.upload 引数名を正しく file= に変更 (以前の path= は無効でエラー発生)。
      - 簡易 MIME 推定 (mp4 -> video/mp4 など)。
      - アップロード失敗時 1 回リトライ。
    """
    client = get_gemini_client()
    if client is None:
        return "(生成SDK未初期化: APIキー未設定または初期化失敗)"

    model_name = map_model_name(config.get('version', 'gemini-2.5-pro'))
    max_tokens = int(config.get('max_output_tokens', 4096))
    temperature = float(config.get('temperature', 0.7))
    top_p = float(config.get('top_p', 0.9))

    # キャッシュヒットなら: 既に upload した file.name を再利用 -> client.files.get する必要はなく file_name を Part.from_uri でなく file オブジェクト再利用不可なので
    # キャッシュに格納しているのは uploaded_file.name (files/xxx)。generate_content では list の中に "file" オブジェクトそのものでも OK だが、
    # 取得していないのでここでは Part.from_uri 相当で参照できないため再アップロードを避けるために file_name を special dict で扱うよりは、キャッシュ時に uploaded_file オブジェクトを保存するのが良い。
    cached_entry = _GENAI_FILE_CACHE.get(video_uri)

    part_or_file = None

    def guess_mime(uri_or_path: str) -> str:
        ext = uri_or_path.lower().split('.')[-1]
        if ext in ('mp4', 'm4v'): return 'video/mp4'
        if ext in ('mov',): return 'video/quicktime'
        if ext in ('webm',): return 'video/webm'
        if ext in ('avi',): return 'video/x-msvideo'
        return 'application/octet-stream'

    # 1) キャッシュヒット (アップロード済 name 保持ケース)
    if cached_entry:
        # Vertexモードでキャッシュしているのは Part か name。Developer API では name を再取得。
        if isinstance(cached_entry, dict) and cached_entry.get('mode') == 'part':
            part_or_file = cached_entry['value']
        else:
            uploaded_file_name = cached_entry if isinstance(cached_entry, str) else cached_entry.get('value')
            if uploaded_file_name and not getattr(client, 'vertexai', False):
                try:
                    part_or_file = client.files.get(name=uploaded_file_name)
                except Exception:
                    part_or_file = None

    vertex_mode = getattr(client, 'vertexai', False)

    if part_or_file is None:
        if vertex_mode:
            # Vertex モード: gs:// を直接参照
            if video_uri.startswith('gs://'):
                mime = guess_mime(video_uri)
                try:
                    part_or_file = types.Part.from_uri(file_uri=video_uri, mime_type=mime)
                    _GENAI_FILE_CACHE[video_uri] = {'mode': 'part', 'value': part_or_file}
                except Exception as e:
                    return f"(Vertexモードでの gs:// 参照失敗: {e})"
            else:
                return "(Vertexモードではローカル動画は gs:// に配置してから使用してください)"
        else:
            # Developer API: アップロード方式
            local_path = None
            cleanup_tmp = False
            if video_uri.startswith('gs://'):
                if not HAS_GOOGLE_CLOUD:
                    return "(GCS未利用環境で gs:// 動画を処理できません)"
                try:
                    bucket_name_path = video_uri[5:]
                    bucket_name, blob_path = bucket_name_path.split('/', 1)
                    storage_client = storage.Client()
                    bucket = storage_client.bucket(bucket_name)
                    blob = bucket.blob(blob_path)
                    fd, tmp_path = tempfile.mkstemp(suffix='_'+os.path.basename(blob_path))
                    os.close(fd)
                    blob.download_to_filename(tmp_path)
                    local_path = tmp_path
                    cleanup_tmp = True
                except Exception as d_err:
                    logger.error(f"GCS ダウンロード失敗: {d_err}")
                    return f"(動画取得失敗: {d_err})"
            else:
                if os.path.exists(video_uri):
                    local_path = video_uri
                else:
                    return f"(ローカル動画パスが存在しません: {video_uri})"

            display_name = os.path.basename(video_uri)[:64]
            attempt = 0
            last_err = None
            while attempt < 2:
                try:
                    logger.info(f"google-genai へ動画アップロード開始 attempt={attempt+1}: {video_uri}")
                    uploaded_file = client.files.upload(file=local_path, config={"display_name": display_name})
                    uploaded_name = getattr(uploaded_file, 'name', None)
                    if not uploaded_name:
                        raise RuntimeError('upload 応答に name がありません')
                    _GENAI_FILE_CACHE[video_uri] = uploaded_name
                    part_or_file = uploaded_file
                    logger.info(f"動画アップロード完了 name={uploaded_name}")
                    break
                except Exception as up_err:
                    last_err = up_err
                    logger.error(f"動画アップロード失敗 attempt={attempt+1}: {up_err}")
                    attempt += 1
                    time.sleep(1)
            if part_or_file is None:
                return f"(動画アップロード失敗: {last_err})"
            if cleanup_tmp and local_path and os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except Exception:
                    pass

    # 3) generate_content 呼び出し
    contents = [prompt, part_or_file]
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config={
                "temperature": temperature,
                "top_p": top_p,
                "max_output_tokens": max_tokens,
            }
        )
        if hasattr(response, 'text') and response.text:
            return response.text
        candidates = getattr(response, 'candidates', [])
        if candidates:
            first = candidates[0]
            content = getattr(first, 'content', None)
            if content and getattr(content, 'parts', None):
                collected = []
                for p in content.parts:
                    t = getattr(p, 'text', None)
                    if t:
                        collected.append(t)
                if collected:
                    return '\n'.join(collected)
        return "(生成結果空: テキストが抽出できませんでした)"
    except Exception as e:
        logger.error(f"generate_text_from_video エラー: {e}")
        return f"(生成失敗: {e})"

def generate_text_from_videos(video_uris, prompt: str, config: dict) -> str:
    """複数動画 (expert + novice 等) を同一リクエストで解析してテキスト生成。

    ポイント:
      - プロンプト本文は変更せず、最初の要素として渡す。
      - Vertex モードでは各 gs:// を Part.from_uri で直接参照。
      - Developer API フォールバック時は順次アップロードし、複数 file part をまとめて generate_content へ。
      - キャッシュ (_GENAI_FILE_CACHE) を個別 URI キーで再利用。
    """
    if not video_uris:
        return "(動画URIが提供されていません)"
    # 重複除去（順序維持）
    seen = set()
    ordered_uris = []
    for u in video_uris:
        if u and u not in seen:
            ordered_uris.append(u)
            seen.add(u)

    client = get_gemini_client()
    if client is None:
        return "(生成SDK未初期化: APIキー未設定または初期化失敗)"

    model_name = map_model_name(config.get('version', 'gemini-2.5-pro'))
    max_tokens = int(config.get('max_output_tokens', 4096))
    temperature = float(config.get('temperature', 0.7))
    top_p = float(config.get('top_p', 0.9))

    vertex_mode = getattr(client, 'vertexai', False)

    def guess_mime(uri_or_path: str) -> str:
        ext = uri_or_path.lower().split('.')[-1]
        if ext in ('mp4', 'm4v'): return 'video/mp4'
        if ext in ('mov',): return 'video/quicktime'
        if ext in ('webm',): return 'video/webm'
        if ext in ('avi',): return 'video/x-msvideo'
        return 'application/octet-stream'

    parts = []

    for video_uri in ordered_uris:
        cached_entry = _GENAI_FILE_CACHE.get(video_uri)
        part_or_file = None
        if cached_entry:
            if isinstance(cached_entry, dict) and cached_entry.get('mode') == 'part':
                part_or_file = cached_entry['value']
            else:
                uploaded_file_name = cached_entry if isinstance(cached_entry, str) else cached_entry.get('value')
                if uploaded_file_name and not vertex_mode:
                    try:
                        part_or_file = client.files.get(name=uploaded_file_name)
                    except Exception:
                        part_or_file = None

        if part_or_file is None:
            if vertex_mode:
                if video_uri.startswith('gs://'):
                    mime = guess_mime(video_uri)
                    try:
                        part_or_file = types.Part.from_uri(file_uri=video_uri, mime_type=mime)
                        _GENAI_FILE_CACHE[video_uri] = {'mode': 'part', 'value': part_or_file}
                    except Exception as e:
                        return f"(Vertexモードでの gs:// 参照失敗: {e})"
                else:
                    return "(Vertexモードではローカル動画は gs:// に配置してから使用してください)"
            else:
                # Developer API: アップロード方式 (generate_text_from_video と同様ロジック)
                local_path = None
                cleanup_tmp = False
                if video_uri.startswith('gs://'):
                    if not HAS_GOOGLE_CLOUD:
                        return "(GCS未利用環境で gs:// 動画を処理できません)"
                    try:
                        bucket_name_path = video_uri[5:]
                        bucket_name, blob_path = bucket_name_path.split('/', 1)
                        storage_client = storage.Client()
                        bucket = storage_client.bucket(bucket_name)
                        blob = bucket.blob(blob_path)
                        fd, tmp_path = tempfile.mkstemp(suffix='_'+os.path.basename(blob_path))
                        os.close(fd)
                        blob.download_to_filename(tmp_path)
                        local_path = tmp_path
                        cleanup_tmp = True
                    except Exception as d_err:
                        logger.error(f"GCS ダウンロード失敗: {d_err}")
                        return f"(動画取得失敗: {d_err})"
                else:
                    if os.path.exists(video_uri):
                        local_path = video_uri
                    else:
                        return f"(ローカル動画パスが存在しません: {video_uri})"

                display_name = os.path.basename(video_uri)[:64]
                attempt = 0
                last_err = None
                while attempt < 2:
                    try:
                        logger.info(f"google-genai へ動画アップロード開始 attempt={attempt+1}: {video_uri}")
                        uploaded_file = client.files.upload(file=local_path, config={"display_name": display_name})
                        uploaded_name = getattr(uploaded_file, 'name', None)
                        if not uploaded_name:
                            raise RuntimeError('upload 応答に name がありません')
                        _GENAI_FILE_CACHE[video_uri] = uploaded_name
                        part_or_file = uploaded_file
                        logger.info(f"動画アップロード完了 name={uploaded_name}")
                        break
                    except Exception as up_err:
                        last_err = up_err
                        logger.error(f"動画アップロード失敗 attempt={attempt+1}: {up_err}")
                        attempt += 1
                        time.sleep(1)
                if part_or_file is None:
                    return f"(動画アップロード失敗: {last_err})"
                if cleanup_tmp and local_path and os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                    except Exception:
                        pass
        parts.append(part_or_file)

    contents = [prompt] + parts
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config={
                "temperature": temperature,
                "top_p": top_p,
                "max_output_tokens": max_tokens,
            }
        )
        if hasattr(response, 'text') and response.text:
            return response.text
        candidates = getattr(response, 'candidates', [])
        if candidates:
            first = candidates[0]
            content = getattr(first, 'content', None)
            if content and getattr(content, 'parts', None):
                collected = []
                for p in content.parts:
                    t = getattr(p, 'text', None)
                    if t:
                        collected.append(t)
                if collected:
                    return '\n'.join(collected)
        return "(生成結果空: テキストが抽出できませんでした)"
    except Exception as e:
        logger.error(f"generate_text_from_videos エラー: {e}")
        return f"(生成失敗: {e})"

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

_global_file_manager_cache = {}

def get_file_manager():
    """ファイルマネージャーを取得（常にGCS使用に統一）"""
    # 企業設定に関係なく常にGCSを使用
    if HAS_GOOGLE_CLOUD:
        storage_type = DEFAULT_STORAGE_TYPE
        storage_config = DEFAULT_STORAGE_CONFIG
        logger.info(f"GCS統一使用: storage_type={storage_type}, bucket={storage_config.get('bucket_name')}")
    else:
        storage_type = 'local'
        storage_config = {'base_path': 'uploads'}
        logger.warning("Google Cloud未利用環境: ローカルストレージを使用")

    # キー生成（バケット名 or base_path を含める）
    bucket_or_base = None
    if storage_type == 'gcs':
        bucket_or_base = storage_config.get('bucket_name')
    else:
        bucket_or_base = storage_config.get('base_path')
    
    # 企業に関係なく統一キーを使用
    key = ('unified', storage_type, bucket_or_base)

    fm = _global_file_manager_cache.get(key)
    if fm:
        return fm

    fm = create_file_manager(storage_type, storage_config)
    _global_file_manager_cache[key] = fm
    logger.debug(f"FileManager created and cached key={key}")
    return fm

@app.route('/')
def index():
    """メインページ - ログイン状態チェック後マニュアル一覧にリダイレクト"""
    if HAS_AUTH_SYSTEM:
        if not current_user.is_authenticated:
            return redirect('/login')
        # 認証済みの場合のみマニュアル一覧へ
        return redirect('/manual/list')
    return redirect('/manual/list')

@app.route('/health')
def health():
    """ヘルスチェックエンドポイント - データベース接続も確認"""
    try:
        # 基本的なステータス
        status = {"status": "OK", "timestamp": datetime.now(JST).isoformat()}
        
        # データベース接続テスト
        if HAS_AUTH_SYSTEM:
            try:
                # 簡単なクエリでデータベース接続を確認
                db.session.execute(db.text('SELECT 1'))
                status["database"] = "OK"
            except Exception as db_error:
                logger.error(f"Database health check failed: {db_error}")
                status["database"] = f"ERROR: {str(db_error)}"
                status["status"] = "DEGRADED"
        else:
            status["database"] = "DISABLED"
            
        return jsonify(status)
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({"status": "ERROR", "error": str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_video():
    """動画アップロード"""
    logger.info("=== アップロード処理開始 ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request files keys: {list(request.files.keys())}")
    logger.info(f"Request form keys: {list(request.form.keys())}")
    logger.info(f"Session: {dict(session)}")
    
    try:
        if HAS_AUTH_SYSTEM and not current_user.is_authenticated:
            logger.warning("認証なしのアクセス試行")
            return jsonify({'error': 'ログインが必要です'}), 401
        
        if 'video' not in request.files:
            logger.error("'video'キーがrequest.filesに存在しません")
            return jsonify({'error': '動画ファイルが選択されていません'}), 400
        
        file = request.files['video']
        logger.info(f"受信ファイル: filename={file.filename}, content_type={file.content_type}")
        
        if file.filename == '':
            logger.error("ファイル名が空です")
            return jsonify({'error': '動画ファイルが選択されていません'}), 400
        
        if file and allowed_file(file.filename):
            logger.info(f"ファイル形式チェック通過: {file.filename}")
            
            # ファイルマネージャーを使用してファイル保存
            file_manager = get_file_manager()
            logger.info(f"ファイルマネージャー取得完了: {type(file_manager)}")
            
            file_info = file_manager.save_file(file, file.filename, 'video')
            logger.info(f"ファイル保存完了: {file_info}")
            
            if HAS_AUTH_SYSTEM and current_user.is_authenticated:
                logger.info("認証済みユーザーによるアップロード - データベースに記録")
                # データベースに記録
                uploaded_file = UploadedFile(
                    original_filename=file.filename,
                    stored_filename=file_info['filename'],
                    file_type='video',
                    file_path=file_info['file_path'],
                    file_size=file_info.get('file_size'),
                    mime_type=file.content_type,
                    company_id=current_user.company_id,
                    uploaded_by=current_user.id
                )
                
                # メタデータ設定（GCS URIを含む）
                metadata = {
                    'storage_type': file_info.get('storage_type', 'local'),
                    'upload_timestamp': datetime.now(JST).isoformat()
                }
                
                # GCS URIを取得してメタデータに保存（file_infoから直接取得）
                if 'gcs_uri' in file_info:
                    metadata['gcs_uri'] = file_info['gcs_uri']
                    logger.info(f"GCS URI設定: {file_info['gcs_uri']}")
                
                uploaded_file.set_metadata(metadata)
                
                db.session.add(uploaded_file)
                db.session.commit()
                logger.info(f"データベース記録完了: file_id={uploaded_file.id}")
                
                # レスポンス用のファイルURLを決定（GCS URIを優先）
                file_url = file_manager.get_file_url(file_info['file_path'])
                if 'gcs_uri' in file_info:
                    # Gemini API用にはGCS URIを使用
                    gemini_uri = file_info['gcs_uri']
                else:
                    gemini_uri = file_url
                
                response_data = {
                    'success': True,
                    'file_id': uploaded_file.id,
                    'filename': file_info['file_path'],
                    'original_filename': file.filename,
                    'file_url': file_url,
                    'gemini_uri': gemini_uri  # AI分析用URI
                }
                logger.info(f"レスポンス準備完了: {response_data}")
                return jsonify(response_data)
            else:
                # 認証システムがない場合は従来の方式
                response_data = {
                    'success': True,
                    'filename': file_info['file_path'],
                    'original_filename': file.filename,
                    'file_url': file_manager.get_file_url(file_info['file_path'])
                }
                logger.info(f"認証なしレスポンス準備完了: {response_data}")
                return jsonify(response_data)
        else:
            logger.error(f"許可されていないファイル形式: {file.filename}")
            return jsonify({'error': '許可されていないファイル形式です'}), 400
            
    except Exception as e:
        logger.error(f"アップロード処理でエラー発生: {str(e)}", exc_info=True)
        return jsonify({'error': f'アップロード中にエラーが発生しました: {str(e)}'}), 500

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """アップロードされたファイルの配信"""
    import os
    from flask import send_from_directory
    
    # セキュリティ: パス traversal攻撃を防ぐ
    if '..' in filename or filename.startswith('/'):
        return jsonify({'error': '不正なファイルパスです'}), 400
    
    upload_dir = os.path.join(os.getcwd(), 'uploads')
    
    try:
        return send_from_directory(upload_dir, filename)
    except FileNotFoundError:
        logger.warning(f"ファイルが見つかりません: {filename}")
        return jsonify({'error': 'ファイルが見つかりません'}), 404
    except Exception as e:
        logger.error(f"ファイル配信エラー: {str(e)}")
        return jsonify({'error': 'ファイル配信中にエラーが発生しました'}), 500

@app.route('/components/<path:filename>')
def serve_component(filename):
    """Serve component files (CSS, HTML, JS)"""
    import os
    from flask import send_from_directory
    
    # Security: prevent path traversal attacks
    if '..' in filename or filename.startswith('/'):
        return jsonify({'error': 'Invalid file path'}), 400
    
    components_dir = os.path.join(os.getcwd(), 'src', 'components')
    
    try:
        return send_from_directory(components_dir, filename)
    except FileNotFoundError:
        logger.warning(f"Component file not found: {filename}")
        return jsonify({'error': 'Component not found'}), 404
    except Exception as e:
        logger.error(f"Component serve error: {str(e)}")
        return jsonify({'error': 'Error serving component'}), 500

@app.route('/video_preview/<int:file_id>')
def video_preview_by_id(file_id):
    """ファイルIDによる動画プレビュー"""
    if HAS_AUTH_SYSTEM:
        if not current_user.is_authenticated:
            return jsonify({'error': 'ログインが必要です'}), 401
        
        # 企業データ分離
        uploaded_file = UploadedFile.query.filter_by(
            id=file_id,
            company_id=current_user.company_id
        ).first()
        
        if not uploaded_file:
            return jsonify({'error': 'ファイルが見つかりません'}), 404
        
        file_manager = get_file_manager()
        preview_url = file_manager.get_file_url(uploaded_file.file_path)
        
        return jsonify({'preview_url': preview_url})
    
    return jsonify({'error': '認証システムが必要です'}), 400

@app.route('/video_preview/<path:filename>')
def video_preview(filename):
    """従来のファイル名による動画プレビュー（後方互換性）"""
    try:
        file_manager = get_file_manager()
        preview_url = file_manager.get_file_url(filename)
        return jsonify({'preview_url': preview_url})
    except Exception as e:
        return jsonify({'error': f'プレビューURL生成エラー: {str(e)}'}), 500

# Legacy endpoints removed - use modern API endpoints instead:
# - /files -> /api/materials
# - /manuals -> /api/manuals
# - /get_version_limits -> removed (not used)
# - /generate_manual -> /api/manuals/generate
# - /ai_comparison_analysis -> removed (not used)
# - /generate_manual_multi_stage -> /api/video-manual/three-stage/async-generate


# Legacy endpoint route removed - not used by frontend
def generate_manual():
    """基本マニュアル生成"""
    if HAS_AUTH_SYSTEM and not current_user.is_authenticated:
        return jsonify({'error': 'ログインが必要です'}), 401
    
    try:
        print("=== generate_manual called ===")
        data = request.get_json()
        print(f"Request data: {data}")

        # パラメータを取得
        filename = data.get('filename')
        file_id = data.get('file_id')
        max_output_tokens = data.get('max_output_tokens', 65535)
        temperature = data.get('temperature', 1.0)
        top_p = data.get('top_p', 0.95)
        prompt = data.get('prompt', 'この動画の内容を詳しく説明してください。')
        version = data.get('version', 'gemini-2.5-pro')
        
        # ファイル取得
        video_file_uri = None
        uploaded_file = None
        
        if HAS_AUTH_SYSTEM and current_user.is_authenticated and file_id:
            # ファイルIDからファイル情報取得
            uploaded_file = UploadedFile.query.filter_by(
                id=file_id,
                company_id=current_user.company_id
            ).first()
            
            if not uploaded_file:
                return jsonify({'error': 'ファイルが見つかりません'}), 404
            
            # GCS URIを優先的に使用（ローカルパスは使用しない）
            metadata = uploaded_file.get_metadata()
            if 'gcs_uri' in metadata:
                video_file_uri = metadata['gcs_uri']
                print(f"GCS URIを使用: {video_file_uri}")
            elif uploaded_file.file_path.startswith('gs://'):
                video_file_uri = uploaded_file.file_path
                print(f"ファイルパスからGCS URIを使用: {video_file_uri}")
            else:
                # ローカルファイルの場合はGCS URIを構築
                if DEFAULT_STORAGE_TYPE == 'gcs' and DEFAULT_STORAGE_CONFIG:
                    bucket_name = DEFAULT_STORAGE_CONFIG.get('bucket_name')
                    if bucket_name:
                        video_file_uri = f"gs://{bucket_name}/{uploaded_file.stored_filename}"
                        print(f"GCS URIを構築: {video_file_uri}")
                    else:
                        return jsonify({'error': 'GCS設定でバケット名が見つかりません'}), 400
                else:
                    return jsonify({'error': 'GCSストレージが必要です。ローカルファイルはサイズが大きすぎるため使用できません。'}), 400
        
        elif filename:
            # 従来の方式（後方互換性）
            if filename.startswith('gs://'):
                video_file_uri = filename
            else:
                video_file_uri = f"gs://{GCS_BUCKET_NAME}/{filename}"
        
        if not video_file_uri:
            return jsonify({'error': 'ファイルが指定されていません'}), 400
        
        print(f"Parameters: video_uri={video_file_uri}, version={version}")
        
        # バージョン別の最大トークン数チェック
        max_allowed_tokens = get_max_tokens_for_version(version)
        if int(max_output_tokens) > max_allowed_tokens:
            return jsonify({
                'error': f'{version}の最大出力トークン数は{max_allowed_tokens}です。現在の設定: {max_output_tokens}'
            }), 400

        # google-genai による実際の生成
        gen_config = {
            'max_output_tokens': max_output_tokens,
            'temperature': temperature,
            'top_p': top_p,
            'version': version
        }
        responses_text = generate_text_from_video(video_file_uri, prompt, gen_config)
        
        # データベースに保存（認証システムがある場合）
        if HAS_AUTH_SYSTEM and current_user.is_authenticated:
            manual = Manual(
                title=f"基本マニュアル - {uploaded_file.original_filename if uploaded_file else filename}",
                content=responses_text,
                manual_type='basic',
                generation_status='completed',  # 基本マニュアルは即座に完了
                generation_progress=100,
                company_id=current_user.company_id,
                created_by=current_user.id
            )
            
            config = {
                'max_output_tokens': max_output_tokens,
                'temperature': temperature,
                'top_p': top_p,
                'version': version,
                'prompt': prompt
            }
            manual.set_generation_config(config)
            
            db.session.add(manual)
            
            # ソースファイル関連付け
            if uploaded_file:
                source_file = ManualSourceFile(
                    manual_id=manual.id,
                    file_id=uploaded_file.id,
                    role='primary'
                )
                db.session.add(source_file)
            
            db.session.commit()
        
        print("Generation completed successfully!")
        return jsonify({
            'success': True,
            'manual_text': responses_text,
            'parameters_used': {
                'max_output_tokens': max_output_tokens,
                'temperature': temperature,
                'top_p': top_p,
                'version': version
            }
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in generate_manual: {error_details}")
        return jsonify({
            'error': f'マニュアル生成中にエラーが発生しました: {str(e)}',
            'details': error_details
        }), 500


# Legacy endpoint route removed - not used by frontend
def ai_comparison_analysis():
    """Gemini AIによる熟練者・非熟練者比較分析"""
    logger.info("=== AI比較分析処理開始 ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request content type: {request.content_type}")
    
    if HAS_AUTH_SYSTEM and not current_user.is_authenticated:
        logger.warning("未認証ユーザーによるAI比較分析リクエスト")
        return jsonify({'error': 'ログインが必要です'}), 401
    
    try:
        data = request.get_json()
        logger.info(f"受信データ: {data}")
        
        if data is None:
            logger.error("JSONデータが空またはNullです")
            return jsonify({'error': 'JSONデータが必要です'}), 400
        
        required_fields = ['expert_video_uri', 'novice_video_uri']
        for field in required_fields:
            if field not in data:
                logger.error(f"必須フィールド不足: {field}")
                return jsonify({'error': f'必須パラメータが不足: {field}'}), 400
        
        logger.info("必須フィールドチェック通過")
        
        try:
            logger.info("Geminiサービス初期化開始")
            gemini_service = GeminiUnifiedService()
            logger.info("Geminiサービス初期化完了")
        except Exception as e:
            logger.error(f"Geminiサービス初期化エラー: {str(e)}", exc_info=True)
            return jsonify({'error': f'Geminiサービス初期化エラー: {str(e)}'}), 500
        
        logger.info("非同期処理開始")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            logger.info(f"AI比較分析実行開始 - expert_video_uri: {data['expert_video_uri']}, novice_video_uri: {data['novice_video_uri']}")
            result = loop.run_until_complete(
                gemini_service.analyze_expert_novice_comparison(
                    expert_video_uri=data['expert_video_uri'],
                    novice_video_uri=data['novice_video_uri'],
                    context_docs=data.get('reference_documents', [])
                )
            )
            logger.info("AI比較分析実行完了")
        except Exception as e:
            logger.error(f"AI比較分析実行エラー: {str(e)}", exc_info=True)
            raise
        finally:
            loop.close()
        
        response_data = {
            'success': True,
            'analysis_result': result,
            'ai_engine': 'gemini-2.5-pro',
            'timestamp': time.time()
        }
        logger.info(f"AI比較分析レスポンス準備完了: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"AI比較分析でエラー発生: {str(e)}", exc_info=True)
        return jsonify({'error': f'AI分析エラー: {str(e)}'}), 500


# Legacy endpoint route removed - function kept as internal helper for /api/manual/create
def generate_manual_multi_stage():
    """マニュアル生成（画像あり）: 非同期処理版"""
    if HAS_AUTH_SYSTEM and not current_user.is_authenticated:
        return jsonify({'error': 'ログインが必要です'}), 401
    
    try:
        print("=== マニュアル生成（画像あり）開始（非同期版） ===")
        data = request.get_json()
        print(f"Request data: {data}")
        
        # パラメータを取得
        expert_file_id = data.get('expert_file_id')
        novice_file_id = data.get('novice_file_id')
        title = data.get('title', 'マニュアル（画像あり）')
        description = data.get('description', '')  # マニュアル説明文
        max_output_tokens = data.get('max_output_tokens', 8192)
        temperature = data.get('temperature', 0.7)
        top_p = data.get('top_p', 0.9)
        version = data.get('version', 'gemini-2.5-pro')
        
        if not expert_file_id:
            return jsonify({'error': 'メイン動画が必要です'}), 400
        
        # ファイル情報取得
        expert_file = UploadedFile.query.filter_by(
            id=expert_file_id,
            company_id=current_user.company_id
        ).first()
        
        novice_file = None
        if novice_file_id:
            novice_file = UploadedFile.query.filter_by(
                id=novice_file_id,
                company_id=current_user.company_id
            ).first()
        
        if not expert_file:
            return jsonify({'error': 'メイン動画ファイルが見つかりません'}), 404
        
        # GCS URIのみを取得（Gemini用）- 実際にGCSに存在することを確認
        def get_video_uri(uploaded_file):
            metadata = uploaded_file.get_metadata()
            # GCS URIがメタデータにある場合（実際にGCSにアップロード済み）
            if 'gcs_uri' in metadata:
                return metadata['gcs_uri']
            # ファイルパスがGCS URI形式の場合
            elif uploaded_file.file_path.startswith('gs://'):
                return uploaded_file.file_path
            else:
                # ローカルファイルの場合はファイルサイズをチェック
                file_size_mb = (uploaded_file.file_size or 0) / (1024 * 1024)
                if file_size_mb > 2048:  # 2GB制限に変更
                    return None  # 大きなファイルはGCS必須
                else:
                    # 小さなファイルの場合、警告してローカルパスを返す（テスト用）
                    print(f"警告: ローカルファイルを使用 (サイズ: {file_size_mb:.1f}MB)")
                    # フルパスを構築
                    import os
                    return os.path.abspath(os.path.join('uploads', uploaded_file.file_path))
        
        expert_uri = get_video_uri(expert_file)
        novice_uri = get_video_uri(novice_file) if novice_file else None
        
        if not expert_uri:
            expert_file_size = (expert_file.file_size or 0) / (1024 * 1024)
            return jsonify({'error': f'メイン動画ファイル（{expert_file_size:.1f}MB）が大きすぎます。2GB以下のファイルか、GCSアップロードが必要です。'}), 400
        
        if novice_file and not novice_uri:
            novice_file_size = (novice_file.file_size or 0) / (1024 * 1024)
            return jsonify({'error': f'比較動画ファイル（{novice_file_size:.1f}MB）が大きすぎます。2GB以下のファイルか、GCSアップロードが必要です。'}), 400
        
        print(f"Expert URI: {expert_uri}")
        print(f"Novice URI: {novice_uri}")
        
        # マニュアルレコードを先に作成（処理中ステータス）
        manual = Manual(
            title=title,
            description=description,  # マニュアル説明文を保存
            content='生成中...',  # 仮のコンテンツ
            manual_type='multi_stage',
            generation_status='pending',
            generation_progress=0,
            company_id=current_user.company_id,
            created_by=current_user.id
        )
        
        config = {
            'max_output_tokens': max_output_tokens,
            'temperature': temperature,
            'top_p': top_p,
            'version': version,
            'generation_type': 'multi_stage'
        }
        manual.set_generation_config(config)
        
        db.session.add(manual)
        db.session.flush()  # IDを取得するためにflush
        
        # ソースファイル関連付け
        expert_source = ManualSourceFile(
            manual_id=manual.id,
            file_id=expert_file.id,
            role='expert'
        )
        db.session.add(expert_source)
        
        if novice_file:
            novice_source = ManualSourceFile(
                manual_id=manual.id,
                file_id=novice_file.id,
                role='novice'
            )
            db.session.add(novice_source)
        
        db.session.commit()
        
        # バックグラウンドで生成処理を開始
        thread = threading.Thread(
            target=run_multi_stage_generation_background,
            args=(manual.id, expert_uri, novice_uri, config)
        )
        thread.daemon = True
        thread.start()
        
        print(f"バックグラウンド処理開始: manual_id={manual.id}")
        
        # 即座にレスポンスを返す
        return jsonify({
            'success': True,
            'manual_id': manual.id,
            'message': 'マニュアル生成を開始しました。処理完了まで数分かかります。',
            'status': 'processing'
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in generate_manual_multi_stage: {error_details}")
        return jsonify({
            'error': f'マニュアル生成（画像あり）エラー: {str(e)}',
            'details': error_details
        }), 500

def run_multi_stage_generation_background(manual_id, expert_uri, novice_uri, config):
    """バックグラウンドでマニュアル（画像あり）生成を実行する関数"""
    try:
        print(f"バックグラウンド生成開始: manual_id={manual_id}")
        print(f"比較動画あり: {novice_uri is not None}")
        
        # アプリケーションコンテキストを作成
        with app.app_context():
            manual = Manual.query.get(manual_id)
            if not manual:
                print(f"マニュアルが見つかりません: {manual_id}")
                return
            
            # ステータスを処理中に更新
            manual.generation_status = 'processing'
            manual.generation_progress = 10
            db.session.commit()
            
            # 進捗初期化
            manual.generation_progress = 25
            db.session.commit()
            
            # ユーザー入力情報を含めたプロンプト生成
            title = manual.title or ''
            description = manual.description or ''
            title_section = f"対象作業: {title}\n" if title else ""
            description_section = f"作業説明: {description}\n" if description else ""
            
            stage1_prompt = f"""
{title_section}{description_section}この動画を分析し、以下の内容をマークダウン形式で詳細に出力してください：

# 作業内容・手順分析

## 作業の概要
- 何の作業を行っているか
- 作業の目的と重要性
- 作業環境や使用ツール

## 詳細な手順
1. 各ステップの具体的な動作
2. 使用する道具や材料
3. 重要なポイントや注意事項
4. 品質基準や確認項目

## 作業のコツと要点
- 効率的な進め方
- よくある間違いの防止方法
- 時間短縮のテクニック
"""
            
            try:
                # Stage1: 熟練 + (あれば) 非熟練を同時投入し包括的分析
                if novice_uri:
                    manual.stage1_content = generate_text_from_videos([expert_uri, novice_uri], stage1_prompt, config)
                else:
                    manual.stage1_content = generate_text_from_video(expert_uri, stage1_prompt, config)
                manual.generation_progress = 50
                db.session.commit()
            except Exception as e:
                err = str(e)
                print(f"Stage 1 エラー: {err}")
                manual.error_message = f"Stage 1 分析エラー: {err}"
                manual.generation_status = 'error'
                db.session.commit()
                return
            
            # Stage 2: 差異比較分析（比較動画がある場合のみ）
            if novice_uri:
                print("=== Stage 2: 差異比較分析 ===")
                manual.generation_progress = 75
                db.session.commit()
                
                stage2_prompt = f"""
{title_section}{description_section}以下の作業分析結果を踏まえて、熟練者動画と非熟練者動画を比較し、差異をマークダウンの表形式で詳細に分析してください：

【前段階の分析結果】
{manual.stage1_content}

# 熟練者vs非熟練者 差異比較分析

| 比較項目 | 熟練者 | 非熟練者 | 差異の要因 | 改善ポイント |
|---------|--------|----------|------------|-------------|
| 作業前準備 | | | | |
| ツールの使い方 | | | | |
| 手順の流れ | | | | |

## 重要な気づき
- 最も影響の大きい差異
- 改善優先度の高いポイント
- 習熟に必要な要素
"""
                
                # Stage2: 差異比較 → 両動画を同一コンテキストで投入
                manual.stage2_content = generate_text_from_videos([expert_uri, novice_uri], stage2_prompt, config)
                manual.generation_progress = 90
                db.session.commit()
                print("Stage 2 完了")
            else:
                # 比較動画がない場合はStage 2をスキップ
                print("Stage 2 スキップ（比較動画なし）")
                manual.stage2_content = "比較動画がアップロードされていないため、差異比較分析はスキップされました。"
                manual.generation_progress = 90
                db.session.commit()
            
            # Stage 3: 最終マニュアル統合
            print("=== Stage 3: 最終マニュアル統合 ===")
            manual.generation_progress = 95
            db.session.commit()
            
            stage3_prompt = f"""
{title_section}{description_section}以下の分析結果を基に、非熟練者が熟練者レベルに到達するための包括的な作業マニュアルをマークダウン形式で作成してください：

【作業内容・手順分析】
{manual.stage1_content}

【差異比較分析】
{manual.stage2_content}

# 最終統合マニュアル: {title if title else '[作業名]'}

## 1. 作業概要と目的
## 2. 事前準備チェックリスト
## 3. 詳細作業手順
## 4. 品質確認ポイント
## 5. よくある失敗と対策
## 6. 上達のためのコツ
## 7. 安全上の注意点

各セクションで具体的で実践的な内容を記載し、非熟練者でも確実に実行できるレベルまで詳細化してください。
"""
            
            try:
                # Stage3: 最終統合（熟練動画中心で安定性優先）
                manual.stage3_content = generate_text_from_video(expert_uri, stage3_prompt, config)
                manual.content = manual.stage3_content  # HTMLマニュアルの内容
                manual.generation_progress = 100
                manual.generation_status = 'completed'
                db.session.commit()
                print("Stage 3 完了 - マニュアル生成（画像あり）完了")
            except Exception as e:
                err = str(e)
                print(f"Stage 3 エラー: {err}")
                manual.error_message = f"Stage 3 統合エラー: {err}"
                manual.generation_status = 'error'
                db.session.commit()
                return
                
    except Exception as e:
        print(f"バックグラウンド処理全体エラー: {str(e)}")
        with app.app_context():
            manual = Manual.query.get(manual_id)
            if manual:
                manual.error_message = f"処理エラー: {str(e)}"
                manual.generation_status = 'error'
                db.session.commit()


# 企業管理エンドポイント
if HAS_AUTH_SYSTEM:
    
    @app.route('/admin/create_company', methods=['POST'])
    def create_company():
        """企業作成（管理者用）"""
        data = request.get_json()
        
        required_fields = ['company_name', 'company_code', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'必須フィールドが不足: {field}'}), 400
        
        result = CompanyManager.create_company(
            name=data['company_name'],
            company_code=data['company_code'],
            password=data['password'],
            admin_username=data.get('admin_username', 'admin'),
            admin_email=data.get('admin_email')
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'company_id': result['company'].id,
                'message': '企業が正常に作成されました'
            })
        else:
            return jsonify({'error': result['error']}), 400
    
    @app.route('/company/settings', methods=['GET', 'POST'])
    @login_required
    def company_settings():
        """企業設定管理"""
        if request.method == 'GET':
            company = current_user.company
            return jsonify({
                'company': {
                    'id': company.id,
                    'name': company.name,
                    'code': company.company_code,
                    'storage_type': company.storage_type,
                    'settings': company.get_settings(),
                    'storage_config': company.get_storage_config()
                }
            })
        
        elif request.method == 'POST':
            if current_user.role != 'admin':
                return jsonify({'error': 'アクセス権限がありません'}), 403
            
            data = request.get_json()
            
            # 一般設定更新
            if 'settings' in data:
                success = CompanyManager.update_company_settings(
                    current_user.company_id,
                    data['settings']
                )
                if not success:
                    return jsonify({'error': '設定更新に失敗しました'}), 500
            
            # ストレージ設定更新
            if 'storage_type' in data and 'storage_config' in data:
                success = CompanyManager.update_storage_config(
                    current_user.company_id,
                    data['storage_type'],
                    data['storage_config']
                )
                if not success:
                    return jsonify({'error': 'ストレージ設定更新に失敗しました'}), 500
            
            return jsonify({'success': True})
    
    # Legacy /company/stats removed - use /api/company/dashboard instead
    
    # 認証ルート初期化
    init_auth_routes(app)
    
    # テストエンドポイント登録 (Phase 1)
    try:
        from src.api.test_routes import test_bp
        app.register_blueprint(test_bp)
        logger.info("Test routes registered successfully")
    except Exception as e:
        logger.warning(f"Failed to register test routes: {e}")
    
    # スーパー管理者用本番APIエンドポイント登録 (Phase 2)
    try:
        from src.api.admin_routes import admin_bp
        app.register_blueprint(admin_bp)
        logger.info("Admin routes (production API) registered successfully")
    except Exception as e:
        logger.warning(f"Failed to register admin routes: {e}")
    
    # 企業管理者用本番APIエンドポイント登録 (Phase 3)
    try:
        from src.api.company_routes import company_bp
        app.register_blueprint(company_bp)
        logger.info("Company routes (production API) registered successfully")
    except Exception as e:
        logger.warning(f"Failed to register company routes: {e}")
    
    # 学習資料管理APIエンドポイント登録 (Phase 4)
    try:
        from src.api.material_routes import material_bp
        app.register_blueprint(material_bp)
        logger.info("Material routes (RAG system API) registered successfully")
    except Exception as e:
        logger.warning(f"Failed to register material routes: {e}")
    
    # Enhanced Manual Generation APIエンドポイント登録 (Phase 5)
    try:
        from src.api.manual_routes import manual_bp
        app.register_blueprint(manual_bp)
        logger.info("Enhanced manual generation routes (Phase 5) registered successfully")
    except Exception as e:
        logger.warning(f"Failed to register enhanced manual routes: {e}")
    
    # PDF Export APIエンドポイント登録 (Phase 6)
    try:
        from src.api.pdf_routes import pdf_bp
        app.register_blueprint(pdf_bp)
        logger.info("PDF export routes (Phase 6) registered successfully")
    except Exception as e:
        logger.warning(f"Failed to register PDF routes: {e}")
    
    # Translation APIエンドポイント登録 (Phase 7)
    try:
        from src.api.translation_routes import translation_bp
        app.register_blueprint(translation_bp)
        logger.info("Translation routes (Phase 7) registered successfully")
    except Exception as e:
        logger.warning(f"Failed to register translation routes: {e}")
    
    # Job Management APIエンドポイント登録 (Phase 8)
    try:
        from src.api.job_routes import job_bp
        app.register_blueprint(job_bp)
        logger.info("Job management routes (Phase 8) registered successfully")
    except Exception as e:
        logger.warning(f"Failed to register job routes: {e}")
    
    # Media Library APIエンドポイント登録
    try:
        from src.api.media_routes import media_bp
        app.register_blueprint(media_bp)
        logger.info("Media library routes registered successfully")
    except Exception as e:
        logger.warning(f"Failed to register media routes: {e}")
    
    # UI Routes for Admin and Company Dashboards
    try:
        from src.routes.ui_routes import super_admin_ui_bp, company_ui_bp, ui_bp
        app.register_blueprint(super_admin_ui_bp)
        app.register_blueprint(company_ui_bp)
        app.register_blueprint(ui_bp)
        logger.info("UI routes registered successfully")
    except Exception as e:
        logger.warning(f"Failed to register UI routes: {e}")
    
    # UI/UX Testing APIエンドポイント登録 (Phase 9)
    try:
        import sys
        from pathlib import Path
        # Add scripts directory to path
        scripts_dir = Path(__file__).parent.parent.parent / 'scripts'
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from test_ui_phase9 import test_ui_bp
        app.register_blueprint(test_ui_bp)
        logger.info("UI/UX testing routes (Phase 9) registered successfully")
    except Exception as e:
        logger.warning(f"Failed to register UI testing routes: {e}")
        import traceback
        logger.error(f"Phase 9 blueprint registration traceback: {traceback.format_exc()}")

    # スーパー管理者用デコレーター
    def require_super_admin(f):
        """スーパー管理者認証が必要なエンドポイントのデコレーター"""
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is authenticated and has super_admin role
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            
            if not current_user.is_super_admin():
                return redirect(url_for('index'))
            
            # Set super admin info in g
            g.current_super_admin = current_user
            return f(*args, **kwargs)
        return decorated_function

    # スーパー管理者マネージャー
    class SuperAdminManager:
        """スーパー管理者管理システム（User.role='super_admin'を使用）"""
        
        @staticmethod
        def authenticate_super_admin(username: str, password: str):
            """スーパー管理者認証（User.role='super_admin'をチェック）"""
            # Try to find user by username or email
            admin = User.query.filter(
                (User.username == username) | (User.email == username),
                User.role == 'super_admin',
                User.is_active == True
            ).first()
            
            if admin and admin.check_password(password):
                return admin
            return None
        
        @staticmethod
        def get_system_overview():
            """システム概要取得"""
            try:
                from datetime import datetime, timedelta
                
                companies = Company.query.all()
                users = User.query.all()
                manuals = Manual.query.all()
                
                # Calculate total storage usage from uploaded files
                total_storage_bytes = db.session.query(
                    func.sum(UploadedFile.file_size)
                ).scalar() or 0
                storage_used_gb = round(total_storage_bytes / (1024 ** 3), 2)
                
                # Today's statistics
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                companies_created_today = Company.query.filter(Company.created_at >= today_start).count()
                files_uploaded_today = UploadedFile.query.filter(UploadedFile.uploaded_at >= today_start).count()
                manuals_created_today = Manual.query.filter(Manual.created_at >= today_start).count()
                
                return {
                    'success': True,
                    'stats': {
                        'companies_total': len(companies),
                        'companies_active': sum(1 for c in companies if c.is_active),
                        'users_total': len(users),
                        'manuals_total': len(manuals),
                        'companies_created_today': companies_created_today,
                        'files_uploaded_today': files_uploaded_today,
                        'manuals_created_today': manuals_created_today,
                        'storage_used_gb': storage_used_gb
                    },
                    'companies': [
                        {
                            'id': c.id,
                            'name': c.name,
                            'company_code': c.company_code,
                            'is_active': c.is_active,
                            'created_at': c.created_at.isoformat() if c.created_at else None,
                            'users_count': User.query.filter_by(company_id=c.id).count(),
                            'files_count': UploadedFile.query.filter_by(company_id=c.id).count(),
                            'manuals_count': Manual.query.filter_by(company_id=c.id).count()
                        } for c in companies
                    ]
                }
            except Exception as e:
                logger.error(f"System overview error: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }
        
        @staticmethod
        def delete_company(company_id: int):
            """企業削除"""
            try:
                company = Company.query.get(company_id)
                if not company:
                    return {
                        'success': False,
                        'error': '企業が見つかりません'
                    }
                
                # 関連データを削除
                User.query.filter_by(company_id=company_id).delete()
                Manual.query.filter_by(company_id=company_id).delete()
                UploadedFile.query.filter_by(company_id=company_id).delete()
                
                db.session.delete(company)
                db.session.commit()
                
                return {
                    'success': True,
                    'message': f'企業「{company.name}」を削除しました'
                }
            except Exception as e:
                db.session.rollback()
                logger.error(f"Company deletion error: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }
        
        @staticmethod
        def update_company_status(company_id: int, is_active: bool):
            """企業ステータス更新"""
            try:
                company = Company.query.get(company_id)
                if not company:
                    return {
                        'success': False,
                        'error': '企業が見つかりません'
                    }
                
                company.is_active = is_active
                company.updated_at = datetime.utcnow()
                db.session.commit()
                
                return {
                    'success': True,
                    'message': f'企業「{company.name}」のステータスを更新しました',
                    'is_active': is_active
                }
            except Exception as e:
                db.session.rollback()
                logger.error(f"Company status update error: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }
        
        @staticmethod
        def get_company_details(company_id: int):
            """企業詳細取得"""
            try:
                company = Company.query.get(company_id)
                if not company:
                    return {
                        'success': False,
                        'error': '企業が見つかりません'
                    }
                
                users = User.query.filter_by(company_id=company_id).all()
                manuals = Manual.query.filter_by(company_id=company_id).all()
                
                return {
                    'success': True,
                    'company': {
                        'id': company.id,
                        'name': company.name,
                        'code': company.company_code,
                        'is_active': company.is_active,
                        'created_at': company.created_at.isoformat() if company.created_at else None,
                        'updated_at': company.updated_at.isoformat() if company.updated_at else None,
                        'settings': company.get_settings() if hasattr(company, 'get_settings') else {},
                        'users': [
                            {
                                'id': u.id,
                                'username': u.username,
                                'email': u.email,
                                'role': u.role,
                                'is_active': u.is_active,
                                'last_login': u.last_login.isoformat() if u.last_login else None
                            } for u in users
                        ],
                        'manuals': [
                            {
                                'id': m.id,
                                'title': m.title,
                                'created_at': m.created_at.isoformat() if m.created_at else None,
                                'generation_status': m.generation_status
                            } for m in manuals[:10]  # 最新10件
                        ]
                    }
                }
            except Exception as e:
                logger.error(f"Company details error: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }
        
        @staticmethod
        def get_system_logs(limit: int = 100):
            """システムログ取得"""
            try:
                # ログファイルから取得（実装例）
                log_file = os.path.join(os.getcwd(), 'logs', 'app.log')
                logs = []
                
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        # 最新のログから取得
                        for line in reversed(lines[-limit:]):
                            logs.append(line.strip())
                
                return {
                    'success': True,
                    'logs': logs,
                    'count': len(logs)
                }
            except Exception as e:
                logger.error(f"System logs error: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'logs': []
                }


    # スーパー管理者ルート（User.role='super_admin'を使用）
    @app.route('/super-admin/login', methods=['GET', 'POST'])
    def super_admin_login():
        """スーパー管理者ログイン（通常の/loginにリダイレクト推奨）"""
        if request.method == 'POST':
            username = request.form.get('username', '')
            password = request.form.get('password', '')
            
            if username and password:
                super_admin = SuperAdminManager.authenticate_super_admin(username, password)
                if super_admin:
                    # Use normal login process
                    login_user(super_admin, remember=True)
                    
                    # Set session info
                    session['is_super_admin'] = True
                    session['super_admin_id'] = super_admin.id
                    session['super_admin_username'] = super_admin.username
                    session['username'] = super_admin.username
                    session['company_id'] = super_admin.company_id
                    session['user_role'] = super_admin.role
                    
                    if super_admin.company:
                        session['company_name'] = super_admin.company.name
                    
                    return redirect(url_for('super_admin_dashboard'))
            
            return render_template('super_admin_login.html', 
                                 error='ユーザー名またはパスワードが間違っています')
        
        return render_template('super_admin_login.html')

    @app.route('/super-admin/logout')
    def super_admin_logout():
        """スーパー管理者ログアウト"""
        session.clear()
        logout_user()
        return redirect(url_for('login'))

    @app.route('/super-admin/dashboard')
    @require_super_admin
    def super_admin_dashboard():
        """スーパー管理者ダッシュボード"""
        return render_template('super_admin_dashboard.html', 
                             current_super_admin=g.current_super_admin)

    @app.route('/super-admin/companies')
    @require_super_admin
    def super_admin_companies():
        """企業管理画面"""
        return render_template('super_admin_companies.html',
                             current_super_admin=g.current_super_admin)

    @app.route('/super-admin/users')
    @require_super_admin
    def super_admin_users():
        """ユーザー管理画面"""
        return render_template('super_admin_users.html',
                             current_super_admin=g.current_super_admin)

    @app.route('/super-admin/activity-logs')
    @require_super_admin
    def super_admin_logs():
        """Activity Logs画面"""
        return render_template('super_admin_logs.html',
                             current_super_admin=g.current_super_admin)

    # スーパー管理者API
    @app.route('/api/super-admin/overview', methods=['GET'])
    @require_super_admin
    def api_super_admin_overview():
        """システム概要データAPI"""
        result = SuperAdminManager.get_system_overview()
        return jsonify(result)

    @app.route('/api/super-admin/companies', methods=['POST'])
    @require_super_admin
    def api_create_company():
        """企業作成API"""
        data = request.get_json()
        
        # CompanyManagerを使用
        comp_manager = CompanyManager()
        result = comp_manager.create_company(
            name=data.get('company_name', ''),
            company_code=data.get('company_code', ''),
            password=data.get('password', ''),
            admin_username='admin',
            admin_email='admin@company.local'
        )
        
        return jsonify(result)

    @app.route('/api/super-admin/companies/<int:company_id>', methods=['DELETE'])
    @require_super_admin
    def api_delete_company(company_id):
        """企業削除API"""
        result = SuperAdminManager.delete_company(company_id)
        return jsonify(result)

    @app.route('/api/super-admin/companies/<int:company_id>/status', methods=['POST'])
    @require_super_admin
    def api_update_company_status(company_id):
        """企業ステータス更新API"""
        data = request.get_json()
        is_active = data.get('is_active', True)
        
        result = SuperAdminManager.update_company_status(company_id, is_active)
        return jsonify(result)

    @app.route('/api/super-admin/companies/<int:company_id>', methods=['GET'])
    @require_super_admin
    def api_company_details(company_id):
        """企業詳細API"""
        result = SuperAdminManager.get_company_details(company_id)
        return jsonify(result)

    @app.route('/api/super-admin/logs', methods=['GET'])
    @require_super_admin
    def api_system_logs():
        """システムログAPI"""
        limit = request.args.get('limit', 100, type=int)
        result = SuperAdminManager.get_system_logs(limit)
        return jsonify(result)

    @app.route('/api/super-admin/users', methods=['GET'])
    @require_super_admin
    def api_super_admin_users():
        """全ユーザー取得API"""
        try:
            users = User.query.all()
            return jsonify({
                'success': True,
                'users': [{
                    'id': u.id,
                    'username': u.username,
                    'email': u.email,
                    'role': u.role,
                    'company_id': u.company_id,
                    'company_name': u.company.name if u.company else None,
                    'is_active': u.is_active if hasattr(u, 'is_active') else True,
                    'created_at': u.created_at.isoformat() if u.created_at else None
                } for u in users]
            })
        except Exception as e:
            logger.error(f"Users fetch error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/super-admin/users/<int:user_id>', methods=['DELETE'])
    @require_super_admin
    def api_delete_user(user_id):
        """ユーザー削除API"""
        try:
            user = User.query.get(user_id)
            if not user:
                return jsonify({'success': False, 'error': 'ユーザーが見つかりません'}), 404
            
            db.session.delete(user)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'ユーザー「{user.username}」を削除しました'
            })
        except Exception as e:
            db.session.rollback()
            logger.error(f"User deletion error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/super-admin/activity-logs', methods=['GET'])
    @require_super_admin
    def api_activity_logs():
        """Activity Logs取得API"""
        try:
            company_id = request.args.get('company_id', type=int)
            user_id = request.args.get('user_id', type=int)
            action_type = request.args.get('action_type')
            limit = request.args.get('limit', 100, type=int)
            
            query = ActivityLog.query
            
            if company_id:
                query = query.filter_by(company_id=company_id)
            if user_id:
                query = query.filter_by(user_id=user_id)
            if action_type:
                query = query.filter_by(action_type=action_type)
            
            logs = query.order_by(ActivityLog.created_at.desc()).limit(limit).all()
            
            return jsonify({
                'success': True,
                'logs': [{
                    'id': log.id,
                    'company_id': log.company_id,
                    'user_id': log.user_id,
                    'action_type': log.action_type,
                    'description': log.description,
                    'created_at': log.created_at.isoformat() if log.created_at else None
                } for log in logs]
            })
        except Exception as e:
            logger.error(f"Activity logs fetch error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/super-admin/activity-logs/export', methods=['GET'])
    @require_super_admin
    def api_export_activity_logs():
        """Activity Logsエクスポート"""
        try:
            logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(1000).all()
            
            result = {
                'success': True,
                'logs': [{
                    'id': log.id,
                    'company_id': log.company_id,
                    'user_id': log.user_id,
                    'action_type': log.action_type,
                    'description': log.description,
                    'created_at': log.created_at.isoformat() if log.created_at else None
                } for log in logs]
            }
            
            response = jsonify(result)
            response.headers['Content-Disposition'] = f'attachment; filename=activity_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            return response
        except Exception as e:
            logger.error(f"Activity logs export error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/super-admin/export', methods=['GET'])
    @require_super_admin
    def api_export_system_data():
        """システムデータ出力API"""
        result = SuperAdminManager.get_system_overview()
        if result['success']:
            response = jsonify(result)
            response.headers['Content-Disposition'] = f'attachment; filename=system_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            return response
        return jsonify(result), 500

# 新しいマニュアル管理ルート
@app.route('/manual/list')
def manual_list():
    """マニュアル一覧画面"""
    return render_template('manual_list.html')

@app.route('/manual/create')
def manual_create():
    """マニュアル作成画面"""
    if HAS_AUTH_SYSTEM and not current_user.is_authenticated:
        return redirect('/login')
    return render_template('manual_create.html')

@app.route('/manual/view/<manual_id>')
def manual_detail(manual_id):
    """マニュアル詳細画面"""
    import re
    from urllib.parse import quote
    
    # Fetch manual data for template rendering
    manual = Manual.query.get_or_404(manual_id)
    
    # Authorization check
    if HAS_AUTH_SYSTEM and current_user.is_authenticated:
        if manual.company_id != current_user.company_id:
            return "アクセス権限がありません", 403
    
    # Use to_dict_with_sources() to include source_videos array for video display
    manual_data = manual.to_dict_with_sources()
    
    # Convert gs:// URLs to /api/video/ URLs for browser playback
    def replace_gs_url(match):
        gs_url = match.group(1)
        # Extract path after gs://bucket_name/
        if gs_url.startswith('gs://'):
            # Remove gs:// and bucket name, get the file path
            path_parts = gs_url.replace('gs://', '').split('/', 1)
            if len(path_parts) > 1:
                file_path = path_parts[1]
                # Remove fragment (#t=start,end) temporarily
                if '#' in file_path:
                    file_path, fragment = file_path.split('#', 1)
                    encoded_path = quote(f'gs://{path_parts[0]}/{file_path}', safe='')
                    return f'/api/video/{encoded_path}#{fragment}'
                else:
                    encoded_path = quote(f'gs://{path_parts[0]}/{file_path}', safe='')
                    return f'/api/video/{encoded_path}'
        return gs_url
    
    # Replace all gs:// URLs in src attributes for all content fields
    for field in ['content', 'content_html', 'content_text']:
        if manual_data.get(field):
            original_content = manual_data[field]
            manual_data[field] = re.sub(
                r'src="(gs://[^"]+)"',
                lambda m: f'src="{replace_gs_url(m)}"',
                manual_data[field]
            )
            # Log conversion for debugging
            if original_content != manual_data[field]:
                gs_urls = re.findall(r'gs://[^\s"\'<>]+', original_content)
                logger.info(f"Converted {len(gs_urls)} gs:// URLs in {field} field for manual {manual_id}")
    
    return render_template('manual_detail.html', manual_id=manual_id, manual=manual_data)

@app.route('/manual/<int:manual_id>/edit', methods=['GET'])
def manual_edit(manual_id):
    """マニュアル編集画面"""
    if HAS_AUTH_SYSTEM and not current_user.is_authenticated:
        return redirect('/login')
    
    # マニュアルデータを取得してテンプレートに渡す
    manual = Manual.query.get_or_404(manual_id)
    
    # 権限チェック
    if HAS_AUTH_SYSTEM and current_user.is_authenticated:
        if manual.company_id != current_user.company_id:
            return "アクセス権限がありません", 403
            
    return render_template('manual_edit.html', manual=manual.to_dict())

@app.route('/manual/<int:manual_id>/edit', methods=['POST'])
def manual_update(manual_id):
    """マニュアル更新処理"""
    try:
        logger.info(f"=== マニュアル更新処理開始: manual_id={manual_id} ===")
        
        # 現在のFlask設定をログ出力
        logger.info(f"Flask MAX_CONTENT_LENGTH設定: {app.config.get('MAX_CONTENT_LENGTH', 'Not set')}")
        
        # リクエストサイズを取得してログ出力
        content_length = request.content_length
        logger.info(f"リクエストサイズ: {content_length} bytes ({content_length / 1024 / 1024:.2f} MB)" if content_length else "リクエストサイズ: Unknown")
        
        # リクエストヘッダー情報
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
        
        if HAS_AUTH_SYSTEM and not current_user.is_authenticated:
            logger.warning("認証なしでマニュアル更新を試行")
            return redirect('/login')
        
        # リクエストデータの取得
        logger.info("フォームデータの取得を開始")
        
        # JSONとFormDataの両方に対応
        content = ''
        
        try:
            # Content-Typeを確認
            content_type = request.content_type or ''
            logger.info(f"Content-Type: {content_type}")
            
            if 'application/json' in content_type:
                # JSON形式の場合
                logger.info("JSON形式のリクエストを処理")
                json_data = request.get_json(silent=True)
                if json_data and 'content' in json_data:
                    content = json_data['content']
                    logger.info(f"JSONから取得したコンテンツサイズ: {len(content)} 文字")
                else:
                    logger.warning("JSONデータまたはcontentフィールドが見つかりません")
                    
            else:
                # multipart/form-data形式の場合（従来の処理）
                logger.info("multipart/form-data形式のリクエストを処理")
                
                # まず通常の方法を試行
                content = request.form.get('content', '')
                logger.info(f"request.form.get()で取得したコンテンツサイズ: {len(content)} 文字")
                
                if not content:
                    logger.warning("request.form.get()でコンテンツが空 - request.values を試行")
                    content = request.values.get('content', '')
                    logger.info(f"request.values.get()で取得したコンテンツサイズ: {len(content)} 文字")
                    
                if not content:
                    logger.warning("request.values.get()でもコンテンツが空 - request.files確認")
                    
                    # request.files.get()も試してみる
                    if 'content' in request.files:
                        file_content = request.files['content'].read()
                        content = file_content.decode('utf-8', errors='replace')
                        logger.info(f"request.files.get()で取得したコンテンツサイズ: {len(content)} 文字")
                    
                if not content:
                    logger.warning("request.files.get()でもコンテンツが空 - rawデータ確認")
                    raw_data = request.get_data()
                    logger.info(f"Raw データサイズ: {len(raw_data)} bytes")
                    
                    if len(raw_data) > 0:
                        try:
                            raw_str = raw_data.decode('utf-8', errors='replace')
                            logger.info(f"Raw データの先頭200文字: {raw_str[:200]}")
                            
                            # より簡単なパターンでcontentを検索
                            content_start = raw_str.find('name="content"')
                            if content_start != -1:
                                logger.info(f"contentフィールドを発見: position={content_start}")
                                
                                # contentフィールドの開始位置を見つける
                                value_start = raw_str.find('\r\n\r\n', content_start)
                                if value_start != -1:
                                    value_start += 4  # \r\n\r\n をスキップ
                                    
                                    # 次のboundaryまでを取得
                                    boundary_pos = raw_str.find('\r\n--', value_start)
                                    if boundary_pos != -1:
                                        content = raw_str[value_start:boundary_pos]
                                        logger.info(f"手動パースで取得したコンテンツサイズ: {len(content)} 文字")
                                    else:
                                        logger.error("境界文字列が見つかりませんでした")
                                else:
                                    logger.error("コンテンツ値の開始位置が見つかりませんでした")
                            else:
                                logger.error("name='content'フィールドが見つかりませんでした")
                                
                        except UnicodeDecodeError as decode_error:
                            logger.error(f"Raw データのデコードエラー: {str(decode_error)}")
                    else:
                        logger.error("Raw データが空です")
                    
        except Exception as parse_error:
            logger.error(f"フォームデータパースエラー: {str(parse_error)}", exc_info=True)
            
        logger.info(f"最終取得コンテンツサイズ: {len(content)} 文字 ({len(content.encode('utf-8')) / 1024 / 1024:.2f} MB)")
        
        if not content:
            logger.warning("コンテンツが空です")
            return jsonify({
                'success': False,
                'error': 'コンテンツが空です'
            }), 400
        
        # マニュアルの取得
        logger.info(f"マニュアル取得: manual_id={manual_id}")
        manual = Manual.query.get_or_404(manual_id)
        logger.info(f"マニュアル情報: title='{manual.title}', type='{manual.manual_type}'")
        
        # アクセス権限チェック
        if HAS_AUTH_SYSTEM and current_user.is_authenticated:
            logger.info(f"権限チェック: user_company_id={current_user.company_id}, manual_company_id={manual.company_id}")
            if manual.company_id != current_user.company_id:
                logger.error("アクセス権限がありません")
                return jsonify({
                    'success': False,
                    'error': 'アクセス権限がありません'
                }), 403
        
        # マニュアルタイプに応じて適切なフィールドを更新
        logger.info("マニュアル更新開始")
        if manual.manual_type == 'manual_with_images' and manual.stage3_content:
            # 画像ありマニュアルの場合はstage3_contentを更新
            logger.info("画像ありマニュアルのstage3_content更新")
            manual.stage3_content = content
        elif manual.manual_type == 'multi_stage' and manual.stage3_content:
            # 画像なしマニュアルの場合もstage3_contentを更新
            logger.info("マルチステージマニュアルのstage3_content更新")
            manual.stage3_content = content
        else:
            # 基本マニュアルの場合はcontentを更新
            logger.info("基本マニュアルのcontent更新")
            manual.content = content
        
        manual.updated_at = datetime.utcnow()
        
        # データベース更新
        logger.info("データベースへのコミット開始")
        db.session.commit()
        logger.info("データベースへのコミット完了")
        
        logger.info(f"マニュアル {manual_id} が正常に更新されました")
        
        # 詳細画面にリダイレクト
        return redirect(url_for('manual_detail', manual_id=manual_id))
        
    except Exception as e:
        logger.error(f"マニュアル更新エラー: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'マニュアルの更新に失敗しました'
        }), 500

# マニュアル管理API
@app.route('/api/manuals', methods=['GET'])
def api_get_manuals():
    """マニュアル一覧取得API"""
    try:
        if not HAS_AUTH_SYSTEM:
            # 認証システムがない場合は空のリストを返す
            return jsonify({
                'success': True,
                'manuals': []
            })
        
        query = Manual.query
        
        if current_user.is_authenticated:
            query = query.filter_by(company_id=current_user.company_id)
        
        manuals = query.order_by(Manual.created_at.desc()).all()
        
        manual_list = [manual.to_dict() for manual in manuals]
        
        return jsonify({
            'success': True,
            'manuals': manual_list
        })
        
    except Exception as e:
        logger.error(f"マニュアル一覧取得エラー: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'マニュアル一覧の取得に失敗しました'
        }), 500

@app.route('/api/manuals/summary', methods=['GET'])
def api_get_manuals_summary():
    """軽量マニュアル一覧取得API（ページネーション対応）"""
    try:
        if not HAS_AUTH_SYSTEM:
            return jsonify({
                'success': True,
                'manuals': [],
                'pagination': {
                    'page': 1,
                    'per_page': 10,
                    'total': 0,
                    'pages': 0
                }
            })
        
        # ページネーションパラメータ
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # per_pageの上限設定（パフォーマンス保護）
        per_page = min(per_page, 100)
        
        query = Manual.query
        
        if current_user.is_authenticated:
            query = query.filter_by(company_id=current_user.company_id)
        
        # ページネーション実行
        pagination = query.order_by(Manual.created_at.desc()).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # 軽量データ構造で変換
        manual_list = [manual.to_dict_summary() for manual in pagination.items]
        
        return jsonify({
            'success': True,
            'manuals': manual_list,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            }
        })
        
    except Exception as e:
        logger.error(f"軽量マニュアル一覧取得エラー: {str(e)}")
        return jsonify({
            'success': False,
            'error': '軽量マニュアル一覧の取得に失敗しました'
        }), 500

@app.route('/api/manual/create', methods=['POST'])
def api_create_manual():
    """マニュアル作成API（マニュアル（画像あり）生成統一版）"""
    try:
        data = request.get_json()
        logger.info(f"マニュアル作成リクエスト: {data}")
        
        # バリデーション
        title = data.get('title', '').strip()
        if not title:
            return jsonify({
                'success': False,
                'error': 'マニュアルタイトルが必要です'
            }), 400
        
        # メイン動画（expert_file_id）が必要
        expert_file_id = data.get('expert_file_id')
        if not expert_file_id:
            return jsonify({
                'success': False,
                'error': 'メイン動画が必要です'
            }), 400
        
        # マニュアル（画像あり）生成エンドポイントにリダイレクト
        return generate_manual_multi_stage()
        
    except Exception as e:
        logger.error(f"マニュアル作成API エラー: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/manual/<int:manual_id>', methods=['GET'])
def api_get_manual(manual_id):
    """マニュアル詳細取得API"""
    import re
    from urllib.parse import quote
    
    try:
        manual = Manual.query.get_or_404(manual_id)
        
        # アクセス権限チェック
        if HAS_AUTH_SYSTEM and current_user.is_authenticated:
            if manual.company_id != current_user.company_id:
                return jsonify({
                    'success': False,
                    'error': 'アクセス権限がありません'
                }), 403
        
        # 元動画表示再発防止: source_videos を含む拡張版を返す
        manual_data = manual.to_dict_with_sources()
        
        # Convert gs:// URLs to /api/video/ URLs for browser playback
        def replace_gs_url(match):
            gs_url = match.group(1)
            if gs_url.startswith('gs://'):
                path_parts = gs_url.replace('gs://', '').split('/', 1)
                if len(path_parts) > 1:
                    file_path = path_parts[1]
                    if '#' in file_path:
                        file_path, fragment = file_path.split('#', 1)
                        encoded_path = quote(f'gs://{path_parts[0]}/{file_path}', safe='')
                        return f'/api/video/{encoded_path}#{fragment}'
                    else:
                        encoded_path = quote(f'gs://{path_parts[0]}/{file_path}', safe='')
                        return f'/api/video/{encoded_path}'
            return gs_url
        
        # Replace all gs:// URLs in src attributes for all content fields
        for field in ['content', 'content_html', 'content_text']:
            if manual_data.get(field):
                original_content = manual_data[field]
                manual_data[field] = re.sub(
                    r'src="(gs://[^"]+)"',
                    lambda m: f'src="{replace_gs_url(m)}"',
                    manual_data[field]
                )
                if original_content != manual_data[field]:
                    gs_urls = re.findall(r'gs://[^\s"\'<>]+', original_content)
                    logger.info(f"API: Converted {len(gs_urls)} gs:// URLs in {field} for manual {manual_id}")
        
        return jsonify({
            'success': True,
            'manual': manual_data
        })
        
    except Exception as e:
        logger.error(f"マニュアル取得エラー: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'マニュアルの取得に失敗しました'
        }), 500


@app.route('/api/manual/<int:manual_id>', methods=['DELETE'])
def api_delete_manual(manual_id):
    """マニュアル削除API"""
    try:
        manual = Manual.query.get_or_404(manual_id)
        
        # アクセス権限チェック
        if HAS_AUTH_SYSTEM and current_user.is_authenticated:
            if manual.company_id != current_user.company_id:
                return jsonify({
                    'success': False,
                    'error': 'アクセス権限がありません'
                }), 403
        
        # マニュアルのタイトルを削除前に保存
        manual_title = manual.title
        
        # 関連するソースファイルの関連付けを削除
        source_files = ManualSourceFile.query.filter_by(manual_id=manual.id).all()
        for source_file in source_files:
            db.session.delete(source_file)
        
        # マニュアル本体を削除
        db.session.delete(manual)
        db.session.commit()
        
        logger.info(f"マニュアル削除完了: ID={manual_id}, タイトル={manual_title}")
        
        return jsonify({
            'success': True,
            'message': f'マニュアル「{manual_title}」を削除しました'
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"マニュアル削除エラー: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'削除に失敗しました: {str(e)}'
        }), 500


@app.route('/api/manual/<int:manual_id>/retry', methods=['POST'])
def api_retry_manual(manual_id):
    """マニュアル再生成API - 既存のマニュアル設定を使用して再生成"""
    try:
        manual = Manual.query.get_or_404(manual_id)
        
        # アクセス権限チェック
        if HAS_AUTH_SYSTEM and current_user.is_authenticated:
            if manual.company_id != current_user.company_id:
                return jsonify({
                    'success': False,
                    'error': 'アクセス権限がありません'
                }), 403
        
        # ソースファイルを取得
        source_files = ManualSourceFile.query.filter_by(manual_id=manual.id).all()
        if not source_files:
            return jsonify({
                'success': False,
                'error': 'ソース動画ファイルが見つかりません'
            }), 404
        
        # expert と novice ファイルを取得
        expert_file = None
        novice_file = None
        for source in source_files:
            uploaded_file = UploadedFile.query.get(source.file_id)
            if not uploaded_file:
                continue
                
            if source.role == 'expert':
                expert_file = uploaded_file
            elif source.role == 'novice':
                novice_file = uploaded_file
            elif source.role == 'primary':  # 旧形式も対応
                expert_file = uploaded_file
        
        if not expert_file:
            return jsonify({
                'success': False,
                'error': 'メイン動画ファイルが見つかりません'
            }), 404
        
        # ファイルのGCS URIを取得
        def get_video_uri(uploaded_file):
            metadata = uploaded_file.get_metadata()
            if 'gcs_uri' in metadata:
                return metadata['gcs_uri']
            elif uploaded_file.file_path.startswith('gs://'):
                return uploaded_file.file_path
            else:
                import os
                file_size_mb = (uploaded_file.file_size or 0) / (1024 * 1024)
                if file_size_mb > 2048:
                    return None
                else:
                    return os.path.abspath(os.path.join('uploads', uploaded_file.file_path))
        
        expert_uri = get_video_uri(expert_file)
        novice_uri = get_video_uri(novice_file) if novice_file else None
        
        if not expert_uri:
            return jsonify({
                'success': False,
                'error': 'メイン動画ファイルのURIを取得できませんでした'
            }), 400
        
        # 既存の設定を取得
        config = manual.get_generation_config() or {}
        config.setdefault('max_output_tokens', 8192)
        config.setdefault('temperature', 0.7)
        config.setdefault('top_p', 0.9)
        config.setdefault('version', 'gemini-2.5-pro')
        config['generation_type'] = 'multi_stage'
        
        # マニュアルのステータスをリセット
        manual.generation_status = 'pending'
        manual.generation_progress = 0
        manual.error_message = None
        manual.content = '再生成中...'
        manual.stage1_content = None
        manual.stage2_content = None
        manual.stage3_content = None
        
        db.session.commit()
        
        # バックグラウンドで生成処理を開始
        thread = threading.Thread(
            target=run_multi_stage_generation_background,
            args=(manual.id, expert_uri, novice_uri, config)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"マニュアル再生成開始: manual_id={manual.id}")
        
        return jsonify({
            'success': True,
            'manual_id': manual.id,
            'message': 'マニュアル再生成を開始しました。処理完了まで数分かかります。',
            'status': 'processing'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"マニュアル再生成エラー: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'再生成に失敗しました: {str(e)}'
        }), 500


@app.route('/api/manual/<int:manual_id>/status', methods=['GET'])
def api_get_manual_status(manual_id):
    """マニュアル生成ステータス取得API"""
    try:
        manual = Manual.query.get_or_404(manual_id)
        
        # アクセス権限チェック
        if HAS_AUTH_SYSTEM and current_user.is_authenticated:
            if manual.company_id != current_user.company_id:
                return jsonify({
                    'success': False,
                    'error': 'アクセス権限がありません'
                }), 403
        
        return jsonify({
            'success': True,
            'status': {
                'generation_status': manual.generation_status or 'completed',
                'generation_progress': manual.generation_progress or 100,
                'error_message': manual.error_message,
                'manual_type': manual.manual_type,
                'title': manual.title
            }
        })
        
    except Exception as e:
        logger.error(f"ステータス取得エラー: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/user-info', methods=['GET'])
def api_get_user_info():
    """現在のユーザー情報を取得"""
    try:
        if not HAS_AUTH_SYSTEM:
            return jsonify({
                'success': True,
                'user': {
                    'name': 'ゲストユーザー',
                    'company': 'デモ環境',
                    'role': 'user'
                }
            })
        
        if current_user and current_user.is_authenticated:
            return jsonify({
                'success': True,
                'user': {
                    'id': current_user.id,
                    'name': current_user.username,  # nameではなくusernameを使用
                    'company': current_user.company.name if current_user.company else '不明',
                    'role': current_user.role,
                    'email': current_user.email if hasattr(current_user, 'email') else ''
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'ユーザーが認証されていません'
            }), 401
            
    except Exception as e:
        logger.error(f"ユーザー情報取得エラー: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/upload', methods=['POST'])
def api_upload_file():
    """
    File upload API endpoint
    Supports video file uploads for manual generation
    """
    logger.info("=== API Upload Processing Started ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request files keys: {list(request.files.keys())}")
    logger.info(f"Request form keys: {list(request.form.keys())}")
    
    try:
        # Authentication check
        if HAS_AUTH_SYSTEM and not current_user.is_authenticated:
            logger.warning("Unauthorized upload attempt")
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
        
        # Check if file is in request
        if 'file' not in request.files:
            logger.error("'file' key not found in request.files")
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        logger.info(f"Received file: filename={file.filename}, content_type={file.content_type}")
        
        if file.filename == '':
            logger.error("Empty filename")
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Get optional parameters
        role = request.form.get('role', 'user')
        description = request.form.get('description', '')
        
        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        logger.info(f"File type validation passed: {file.filename}")
        
        # Save file using file manager
        file_manager = get_file_manager()
        logger.info(f"File manager obtained: {type(file_manager)}")
        
        file_info = file_manager.save_file(file, file.filename, 'video')
        logger.info(f"File saved successfully: {file_info}")
        
        # Record in database if authentication is enabled
        uploaded_file_record = None
        if HAS_AUTH_SYSTEM and current_user.is_authenticated:
            logger.info("Recording upload in database")
            uploaded_file_record = UploadedFile(
                original_filename=file.filename,
                stored_filename=file_info['filename'],
                file_type='video',
                file_path=file_info['file_path'],
                file_size=file_info.get('file_size'),
                mime_type=file.content_type,
                company_id=current_user.company_id,
                uploaded_by=current_user.id
            )
            db.session.add(uploaded_file_record)
            db.session.commit()
            logger.info(f"Upload recorded with ID: {uploaded_file_record.id}")
        
        # Prepare response
        response_data = {
            'success': True,
            'message': 'File uploaded successfully',
            'file': {
                'id': uploaded_file_record.id if uploaded_file_record else None,
                'original_filename': file.filename,
                'stored_filename': file_info['filename'],
                'file_path': file_info['file_path'],
                'file_size': file_info.get('file_size'),
                'mime_type': file.content_type,
                'uploaded_at': uploaded_file_record.uploaded_at.isoformat() if uploaded_file_record else None
            }
        }
        
        logger.info("Upload completed successfully")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Upload failed: {str(e)}'
        }), 500

@app.route('/api/system/info', methods=['GET'])
def api_system_info():
    """
    System information API endpoint
    Returns system configuration and status
    """
    try:
        # Basic system information
        system_info = {
            'version': '1.0.0',
            'environment': os.getenv('FLASK_ENV', 'production'),
            'debug': os.getenv('DEBUG', 'False') == 'True',
            'features': {
                'authentication': HAS_AUTH_SYSTEM,
                'gcs_storage': os.path.exists(os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')),
                'gemini_api': True,  # Always available in this system
                'video_processing': True
            },
            'storage': {
                'type': 'gcs',
                'bucket': os.getenv('GCS_BUCKET_NAME', ''),
                'project_id': os.getenv('PROJECT_ID', '')
            },
            'limits': {
                'max_file_size_gb': 10,
                'max_video_duration_minutes': 60,
                'supported_formats': list(ALLOWED_EXTENSIONS)
            }
        }
        
        # Add authentication status if available
        if HAS_AUTH_SYSTEM:
            system_info['auth_status'] = {
                'authenticated': current_user.is_authenticated if current_user else False,
                'user': current_user.username if (current_user and current_user.is_authenticated) else None,
                'company': current_user.company.name if (current_user and current_user.is_authenticated and current_user.company) else None
            }
        
        return jsonify(system_info), 200
        
    except Exception as e:
        logger.error(f"System info error: {e}", exc_info=True)
        return jsonify({
            'error': f'Failed to retrieve system information: {str(e)}'
        }), 500

@app.route('/api/manuals/status', methods=['POST'])
def api_get_multiple_manual_status():
    """複数マニュアルの生成ステータスを一括取得"""
    try:
        data = request.get_json()
        manual_ids = data.get('manual_ids', [])
        
        if not manual_ids:
            return jsonify({
                'success': False,
                'error': 'マニュアルIDのリストが必要です'
            }), 400
        
        manuals = Manual.query.filter(Manual.id.in_(manual_ids)).all()
        
        statuses = []
        for manual in manuals:
            status_info = {
                'id': manual.id,
                'status': manual.generation_status or 'completed',
                'progress': manual.generation_progress or 100,
                'error_message': manual.error_message
            }
            # 完了したマニュアルの場合は必要な情報を含める
            if manual.generation_status == 'completed':
                status_info.update({
                    'title': manual.title,
                    'manual_type': manual.manual_type
                })
            statuses.append(status_info)
        
        return jsonify({
            'success': True,
            'statuses': statuses
        })
        
    except Exception as e:
        logger.error(f"複数ステータス取得エラー: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def generate_manual_content(manual_id, config):
    """マニュアル内容生成（同期処理）"""
    try:
        # マニュアル情報を取得してタイトルを保持
        manual = Manual.query.get(manual_id)
        user_title = manual.title if manual else None
        
        expert_uri = config.get('expert_video_uri')
        novice_uri = config.get('novice_video_uri')
        custom_prompt = config.get('custom_prompt', '')
        
        # 基本プロンプトを構築
        base_prompt = build_manual_prompt(custom_prompt)
        
        if expert_uri and novice_uri:
            # 比較分析マニュアル
            logger.info(f"比較分析マニュアル生成開始: expert={expert_uri}, novice={novice_uri}")
            
            if HAS_GEMINI_SERVICE:
                service = GeminiUnifiedService()
                
                # asyncio.run()を使用してasyncメソッドを実行
                try:
                    result = asyncio.run(service.analyze_expert_novice_comparison(expert_uri, novice_uri, []))
                except Exception as e:
                    logger.error(f"比較分析エラー: {e}")
                    raise Exception(f"比較分析エラー: {e}")
                
                if result['success']:
                    # 分析結果をマニュアル形式に変換（ユーザータイトルを渡す）
                    return format_comparison_analysis_as_manual(result, base_prompt, user_title)
                else:
                    raise Exception(f"比較分析に失敗: {result.get('error', '不明なエラー')}")
            else:
                # Geminiサービスが利用できない場合は従来のエンドポイントを使用
                response = requests.post('http://localhost:5000/generate_manual', json={
                    'filename': expert_uri,
                    'prompt': base_prompt,
                    'version': 'gemini-2.5-pro',
                    'max_output_tokens': 65535
                })
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        return result['manual_text']
                    else:
                        raise Exception(result.get('error', 'マニュアル生成に失敗'))
                else:
                    raise Exception(f"API呼び出しエラー: {response.status_code}")
        
        elif expert_uri:
            # 基本マニュアル（熟練者動画のみ）
            logger.info(f"基本マニュアル生成開始: {expert_uri}")
            
            response = requests.post('http://localhost:5000/generate_manual', json={
                'filename': expert_uri,
                'prompt': base_prompt,
                'version': 'gemini-2.5-pro',
                'max_output_tokens': 65535
            })
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return result['manual_text']
                else:
                    raise Exception(result.get('error', 'マニュアル生成に失敗'))
            else:
                raise Exception(f"API呼び出しエラー: {response.status_code}")
        
        else:
            raise Exception('動画URIが指定されていません')
    
    except Exception as e:
        logger.error(f"マニュアル生成エラー: {str(e)}")
        raise

def build_manual_prompt(custom_prompt):
    """マニュアル生成用プロンプト構築（文章量等はカスタムプロンプトのみ反映）"""
    base_prompt = """この動画は製造業の作業手順を説明した動画です。以下の要件で実用的な作業マニュアルを作成してください：

## 作業概要
- 作業の目的と重要性
- 推定作業時間
- 必要な技能レベル

## 準備工程
- 必要な工具・材料
- 安全装備の確認
- 作業環境の整備

## 詳細作業手順
- ステップごとの指示
- 安全上の注意事項
- 品質チェックポイント

## 熟練者のコツ・ポイント
- 効率的な作業方法
- 品質向上のための技術

## 注意事項・トラブルシューティング
- よくある失敗とその対策
- 緊急時の対応

## 品質管理・検査項目
- 完成品の確認ポイント
- 品質基準"""
    
    # カスタムプロンプトを最も重要な指示として配置
    if custom_prompt:
        base_prompt = f"""{custom_prompt}

以下の基本構成に従って作成してください：

{base_prompt}"""
    
    base_prompt += "\n\n実用的で分かりやすい日本語で、現場で使えるマニュアルを作成してください。"
    
    return base_prompt

def format_comparison_analysis_as_manual(analysis_result, base_prompt, user_title=None):
    """比較分析結果をマニュアル形式に変換"""
    logger.info(f"分析結果構造確認: {type(analysis_result)} - keys: {analysis_result.keys() if isinstance(analysis_result, dict) else 'N/A'}")
    
    if not analysis_result.get('success'):
        logger.error(f"分析結果取得失敗: success={analysis_result.get('success')}")
        return "分析結果を取得できませんでした。"
    
    # Function Calling結果の処理 - analysis_resultキーがない場合は直接使用
    result = analysis_result.get('analysis_result', analysis_result)
    logger.info(f"分析結果の詳細構造: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
    
    # Function Calling形式の結果を処理
    if 'parts' in result and result['parts']:
        # Function Calling形式の結果を処理
        parts = result['parts']
        expert_analysis = None
        novice_analysis = None
        comparison_arguments = result.get('arguments', {})
        
        # expert_analysisとnovice_analysisを検索
        for part in parts:
            if part.get('function_name') == 'extract_work_steps':
                args = part.get('arguments', {})
                if args.get('skill_level') == 'expert':
                    expert_analysis = args
                elif args.get('skill_level') == 'beginner':
                    novice_analysis = args
        
        # 作業タイトルの決定 - ユーザータイトルがある場合はそれを優先
        work_title = user_title if user_title else "作業マニュアル"
        
        # ユーザータイトルがない場合のみ分析結果からタイトルを取得
        if not user_title:
            if expert_analysis and expert_analysis.get('work_title'):
                work_title = expert_analysis['work_title']
            elif comparison_arguments and 'detailed_differences' in comparison_arguments:
                work_title = "ボルト締結作業マニュアル"  # デフォルト値
        
        manual_content = f"""# {work_title}

## 📋 作業概要
この作業は製造業における重要な工程です。熟練者と非熟練者の作業比較分析に基づいて、最適な手順をまとめました。

**推定作業時間:** {expert_analysis.get('estimated_time', '不明') if expert_analysis else '不明'}分

## 🔧 準備工程
"""
        
        # 熟練者の手順から準備工程を抽出
        if expert_analysis and expert_analysis.get('steps'):
            expert_steps = expert_analysis['steps']
            for i, step in enumerate(expert_steps):
                if '準備' in step.get('action', '') or '配置' in step.get('action', '') or i == 0:
                    manual_content += f"- {step.get('action', '')}\n"
                    if step.get('expert_tips'):
                        manual_content += f" **コツ:** {step.get('expert_tips')}\n"
                    if step.get('safety_notes'):
                        manual_content += f" **安全:** {step.get('safety_notes')}\n"
        
        manual_content += "\n## 詳細作業手順\n"
        
        # 熟練者の詳細手順
        if expert_analysis and expert_analysis.get('steps'):
            expert_steps = expert_analysis['steps']
            for i, step in enumerate(expert_steps, 1):
                manual_content += f"### ステップ {i}: {step.get('action', '')}\n"
                manual_content += f"**所要時間:** {step.get('duration_seconds', 0)}秒\n\n"
                
                if step.get('expert_tips'):
                    manual_content += f"**熟練者のコツ:**\n{step.get('expert_tips')}\n\n"
                
                if step.get('quality_points'):
                    manual_content += f"**品質ポイント:**\n{step.get('quality_points')}\n\n"
                
                if step.get('safety_notes'):
                    manual_content += f"**安全注意事項:**\n{step.get('safety_notes')}\n\n"
                
                if step.get('common_mistakes'):
                    manual_content += f"**よくある失敗:**\n{step.get('common_mistakes')}\n\n"
        
        # 比較分析結果を追加
        manual_content += "## 熟練者と非熟練者の違い\n"
        
        differences = comparison_arguments.get('detailed_differences', [])
        for diff in differences:
            manual_content += f"### {diff.get('aspect', '')}\n"
            manual_content += f"**影響度:** {diff.get('impact_level', '').upper()}\n\n"
            manual_content += f"**熟練者のアプローチ:**\n{diff.get('expert_approach', '')}\n\n"
            manual_content += f"**非熟練者の問題点:**\n{diff.get('novice_approach', '')}\n\n"
            manual_content += f"**改善提案:**\n{diff.get('improvement_suggestion', '')}\n\n"
        
        # 推奨トレーニング
        training = comparison_arguments.get('recommended_training', [])
        if training:
            manual_content += "## 推奨トレーニング\n"
            for t in training:
                manual_content += f"### {t.get('skill_area', '')}\n"
                manual_content += f"**トレーニング方法:** {t.get('training_method', '')}\n"
                manual_content += f"**期待される改善:** {t.get('expected_improvement', '')}\n\n"
        
        # 総合評価
        overall_assessment = comparison_arguments.get('overall_assessment', {})
        if overall_assessment:
            manual_content += "## 総合評価\n"
            if overall_assessment.get('safety_gap'):
                manual_content += f"**安全性の差:**\n{overall_assessment['safety_gap']}\n\n"
            if overall_assessment.get('quality_gap'):
                manual_content += f"**品質の差:**\n{overall_assessment['quality_gap']}\n\n"
            if overall_assessment.get('efficiency_gap'):
                manual_content += f"**効率性の差:**\n{overall_assessment['efficiency_gap']}\n\n"
        
        logger.info(f"マニュアル生成完了: {len(manual_content)}文字")
        return manual_content
    else:
        logger.error("分析結果にpartsが含まれていません")
        return "分析結果の構造が正しくありません。"

# データベース初期化は起動時に実行
def init_database():
    """データベーステーブル作成"""
    try:
        # 環境変数から直接パスを取得するか、コンテナ/ローカル環境に応じてパスを設定
        database_path_env = os.getenv('DATABASE_PATH')
        if database_path_env:
            # 環境変数で指定されている場合
            db_path = database_path_env
            instance_dir = os.path.dirname(db_path)
        elif os.path.exists('/app'):
            # コンテナ環境
            instance_dir = '/app/instance'
            db_path = '/app/instance/manual_generator.db'
        else:
            # ローカル環境
            instance_dir = os.path.join(os.getcwd(), 'instance')
            db_path = os.path.join(instance_dir, 'manual_generator.db')
            
        # instanceディレクトリの作成を確実に実行
        os.makedirs(instance_dir, exist_ok=True)
        
        # ディレクトリの権限を確認
        if not os.access(instance_dir, os.W_OK):
            logger.warning(f"Instance directory {instance_dir} is not writable")
            try:
                os.chmod(instance_dir, 0o755)
                logger.info("Fixed instance directory permissions")
            except Exception as perm_error:
                logger.error(f"Failed to fix permissions: {perm_error}")
        
        logger.info(f"Instance directory created: {instance_dir}")
        
        if HAS_AUTH_SYSTEM:
            # データベースファイルのパスを確認
            logger.info(f"Database path: {db_path}")
            
            # データベーステーブルを作成
            db.create_all()
            logger.info("データベーステーブルを作成しました")
            
            # データベースマイグレーションの実行
            try:
                from migrate_unified import run_migrations
                logger.info("データベースマイグレーションを実行します...")
                migration_success = run_migrations(db_path, logger)
                if migration_success:
                    logger.info("DB: データベースマイグレーションが完了しました")
                else:
                    logger.warning("DB: データベースマイグレーションに失敗しました")
            except Exception as migration_error:
                logger.error(f"DB: マイグレーションエラー: {migration_error}")

            # データベースファイルの存在とサイズを確認
            if os.path.exists(db_path):
                file_size = os.path.getsize(db_path)
                logger.info(f"DB: Database file created successfully: {db_path}")
                logger.info(f"DB: Database file size: {file_size} bytes")
            else:
                logger.error(f"DB: Database file not found after initialization: {db_path}")

            logger.info("DB: Database initialization completed")
            
    except Exception as e:
        logger.error(f"データベース初期化エラー: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

# =====================================
# 動画マニュアル生成 API エンドポイント
# =====================================

@app.route('/manual/video/three-stage')
def manual_with_images_page():
    """マニュアル（画像あり）生成ページ"""
    return render_template('manual_create_with_images.html')

# ======= マニュアル（画像あり）生成API =======

def get_upload_directory():
    """動画アップロード用ディレクトリを取得"""
    temp_dir = os.path.join(app.instance_path, 'temp_videos')
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

@app.route('/api/video-manual/three-stage/async-generate', methods=['POST'])
def api_manual_with_images_async():
    """マニュアル（画像あり）非同期生成API"""
    try:
        if not HAS_VIDEO_MANUAL:
            return jsonify({
                'success': False,
                'error': '動画マニュアル生成機能が利用できません'
            }), 500

        # ファイルアップロード処理 (互換: 'video' も許可)
        upload_key = 'video_file'
        if 'video_file' not in request.files and 'video' in request.files:
            upload_key = 'video'
        if upload_key not in request.files:
            return jsonify({
                'success': False,
                'error': '動画ファイルが選択されていません'
            }), 400
        video_file = request.files[upload_key]
        if video_file.filename == '':
            return jsonify({
                'success': False,
                'error': '動画ファイルが選択されていません'
            }), 400

        # タイトル・カスタム生成設定を取得
        title = request.form.get('title', '動画マニュアル')
        description = request.form.get('description', '')  # マニュアル説明文
        prompt_purpose = request.form.get('purpose')
        prompt_length = request.form.get('length')
        prompt_custom = request.form.get('custom_instruction')
        output_detail = request.form.get('output_detail', 'titles_only')

        # file_managerを使ってファイルを正しく保存
        file_manager = get_file_manager()
        file_info = file_manager.save_file(video_file, video_file.filename, 'video')
        logger.info(f"ファイル保存完了: {file_info}")

        # データベースにUploadedFileレコードを作成
        # NOTE: db を先に import しないと後続でローカル扱いになるケースを避ける
        from src.models.models import UploadedFile, Manual, ManualSourceFile, db
        company_id = 1
        user_id = None
        try:
            if HAS_AUTH_SYSTEM and current_user.is_authenticated:
                company_id = current_user.company_id
                user_id = current_user.id
        except Exception:
            pass

        uploaded_file = UploadedFile(
            original_filename=video_file.filename,
            stored_filename=file_info['filename'],
            file_type='video',
            file_path=file_info['file_path'],
            file_size=file_info.get('file_size'),
            mime_type=video_file.content_type,
            company_id=company_id,
            uploaded_by=user_id
        )

        metadata = {
            'storage_type': file_info.get('storage_type', 'local'),
            'upload_timestamp': datetime.now(JST).isoformat()
        }
        if 'gcs_uri' in file_info:
            metadata['gcs_uri'] = file_info['gcs_uri']
            logger.info(f"GCS URI設定: {file_info['gcs_uri']}")
        uploaded_file.set_metadata(metadata)
        db.session.add(uploaded_file)

        # マニュアルレコード作成
        manual = Manual(
            title=title,
            description=description,
            content='',
            manual_type='manual_with_images',
            company_id=company_id,
            generation_status='processing',
            generation_progress=0
        )

        # ローカル保存時は full_path が存在、GCS 保存時は存在しないため KeyError 回避し使い分け
        if 'full_path' in file_info:
            video_path = file_info['full_path']
        else:
            # GCS では後続処理で gs:// URI を直接扱う想定
            video_path = file_info.get('gcs_uri') or file_info.get('file_path')
            logger.debug(f"GCS保存: video_path(URI)={video_path}")
        config = {
            'video_path': video_path,
            'video_filename': video_file.filename,
            'generation_type': 'manual_with_images_async',
            'custom_prompt': {
                'title': title,
                'description': description,
                'purpose': prompt_purpose,
                'length': prompt_length,
                'custom_instruction': prompt_custom,
                'output_detail': output_detail,
                'default_style': '体言止めの箇条書き'
            }
        }
        manual.set_generation_config(config)
        db.session.add(manual)
        db.session.flush()

        source_file = ManualSourceFile(
            manual_id=manual.id,
            file_id=uploaded_file.id,
            role='primary'
        )
        db.session.add(source_file)
        db.session.commit()

        thread = threading.Thread(
            target=process_manual_with_images_async,
            args=(manual.id, video_path, title, config.get('custom_prompt'))
        )
        thread.daemon = True
        thread.start()

        return jsonify({'success': True,'manual_id': manual.id,'message': 'マニュアル（画像あり）の生成を開始しました'})

    except Exception as e:
        import traceback
        logger.error(f"マニュアル（画像あり）非同期生成エラー: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'success': False,'error': f'エラーが発生しました: {str(e)}'}), 500

def process_manual_with_images_async(manual_id, video_path, title, custom_prompt=None):
    """マニュアル（画像あり）非同期処理

    custom_prompt で frame_mode='hybrid' が指定された場合は
    ハイブリッド (text-only stage1 + minimal midpoint stage2) を使用。
    それ以外は従来(full)パイプライン。
    """
    with app.app_context():  # Flaskアプリケーションコンテキストを設定
        try:
            from src.models.models import Manual, db
            
            # マニュアルレコードを取得
            manual = Manual.query.get(manual_id)
            if not manual:
                logger.error(f"Manual ID {manual_id} が見つかりません")
                return

            # マニュアル（画像あり）生成処理を実行
            from src.services.video_manual_with_images_generator import ManualWithImagesGenerator
            generator = ManualWithImagesGenerator()

            frame_mode = None
            if isinstance(custom_prompt, dict):
                frame_mode = custom_prompt.get('frame_mode') or custom_prompt.get('frames_mode')
            frame_mode = (frame_mode or 'full').lower()

            manual.generation_progress = 10
            db.session.commit()

            if frame_mode == 'hybrid':
                logger.info("画像ありマニュアル: hybrid パイプライン開始")
                s1 = generator.stage_1_analyze_work_steps_text_only(video_path, custom_prompt)
                manual.stage1_content = json.dumps(s1, ensure_ascii=False)
                manual.generation_progress = 35
                db.session.commit()
                s2 = generator.stage_2_extract_representative_frames_hybrid(video_path, s1)
                manual.stage2_content = json.dumps(s2, ensure_ascii=False)
                manual.generation_progress = 65
                db.session.commit()
                stage1_result = s1
                stage2_result = s2
            else:
                logger.info("画像ありマニュアル: full パイプライン開始")
                stage1_result = generator.stage_1_analyze_work_steps(video_path, custom_prompt)
                manual.stage1_content = json.dumps(stage1_result, ensure_ascii=False)
                manual.generation_progress = 40
                db.session.commit()
                stage2_result = generator.stage_2_extract_representative_frames(video_path, stage1_result)
                manual.stage2_content = json.dumps(stage2_result, ensure_ascii=False)
                manual.generation_progress = 70
                db.session.commit()

            # Stage 3: HTMLマニュアル生成
            stage3_result = generator.stage_3_generate_html_manual(stage1_result, stage2_result, custom_prompt)
            manual.stage3_content = stage3_result  # 文字列として保存
            manual.content = stage3_result  # HTMLマニュアルの内容
            manual.generation_progress = 100
            manual.generation_status = 'completed'
            db.session.commit()

            logger.info(f"マニュアル（画像あり）生成完了: Manual ID {manual_id}")

        except Exception as e:
            logger.error(f"マニュアル（画像あり）非同期処理エラー: {str(e)}")
            
            # エラー時の処理
            try:
                from src.models.models import Manual, db
                manual = Manual.query.get(manual_id)
                if manual:
                    manual.generation_status = 'failed'
                    manual.error_message = str(e)
                    db.session.commit()
            except Exception as db_error:
                logger.error(f"データベース更新エラー: {db_error}")

@app.route('/api/video-manual/three-stage/generate', methods=['POST'])
def api_manual_with_images():
    """マニュアル（画像あり）生成API"""
    try:
        if not HAS_VIDEO_MANUAL:
            return jsonify({
                'status': 'error',
                'error': '動画マニュアル生成機能が利用できません'
            }), 500

        # ファイルアップロード処理
        if 'video' not in request.files:
            return jsonify({
                'status': 'error',
                'error': '動画ファイルが選択されていません'
            }), 400

        video_file = request.files['video']
        if video_file.filename == '':
            return jsonify({
                'status': 'error',
                'error': '動画ファイルが選択されていません'
            }), 400

        # 一時ファイル保存
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            video_file.save(tmp_file.name)
            video_path = tmp_file.name

        try:
            # マニュアル（画像あり）生成処理実行
            generator = ManualWithImagesGenerator()
            result = generator.generate_manual_with_images(video_path)
            
            if result.get('success'):
                return jsonify({
                    'status': 'success',
                    'data': {
                        'stage1_result': result['stage1_result'],
                        'stage2_result': result['stage2_result'], 
                        'html_manual': result['html_manual'],
                        'summary': result['summary']
                    }
                })
            else:
                return jsonify({
                    'status': 'error',
                    'error': result.get('error', 'マニュアル（画像あり）生成処理でエラーが発生しました')
                }), 500
                
        finally:
            # 一時ファイル削除
            try:
                os.unlink(video_path)
            except:
                pass

    except Exception as e:
        logger.error(f"マニュアル（画像あり）生成エラー: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Vertex AI権限エラーの場合は特別なメッセージ
        if "IAM_PERMISSION_DENIED" in str(e) or "Permission" in str(e):
            return jsonify({
                'status': 'error',
                'error': f'Vertex AI権限エラー: {str(e)}',
                'error_type': 'permission_denied',
                'solutions': [
                    'Google Cloud Consoleでプロジェクト権限を確認',
                    'Vertex AI APIが有効化されているか確認',
                    'サービスアカウントに適切な権限が付与されているか確認',
                    '環境変数 GOOGLE_APPLICATION_CREDENTIALS が正しく設定されているか確認'
                ]
            }), 403
        else:
            return jsonify({
                'status': 'error',
                'error': f'マニュアル生成（画像あり）中にエラーが発生しました: {str(e)}'
            }), 500

@app.route('/api/video-manual/three-stage/stage1', methods=['POST'])
def api_stage1_analyze():
    """1段階: 作業ステップ分析API"""
    try:
        if not HAS_VIDEO_MANUAL:
            return jsonify({
                'status': 'error',
                'error': '動画マニュアル生成機能が利用できません'
            }), 500

        # ファイルアップロード処理
        if 'video' not in request.files:
            return jsonify({
                'status': 'error',
                'error': '動画ファイルが選択されていません'
            }), 400

        video_file = request.files['video']
        if video_file.filename == '':
            return jsonify({
                'status': 'error',
                'error': '動画ファイルが選択されていません'
            }), 400

        # 一時ファイル保存
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            video_file.save(tmp_file.name)
            video_path = tmp_file.name

        try:
            # 1段階のみ実行
            generator = ManualWithImagesGenerator()
            stage1_result = generator.stage_1_analyze_work_steps(video_path)
            
            return jsonify({
                'status': 'success',
                'data': stage1_result
            })
                
        finally:
            # 一時ファイル削除
            try:
                os.unlink(video_path)
            except:
                pass

    except Exception as e:
        logger.error(f"1段階処理エラー: {e}")
        return jsonify({
            'status': 'error',
            'error': f'1段階の作業分析でエラーが発生しました: {str(e)}'
        }), 500

@app.route('/api/video-manual/three-stage/stage2', methods=['POST'])
def api_stage2_extract_frames():
    """2段階: 代表フレーム抽出API"""
    try:
        if not HAS_VIDEO_MANUAL:
            return jsonify({
                'status': 'error',
                'error': '動画マニュアル生成機能が利用できません'
            }), 500

        # ファイルアップロードと1段階結果を受信
        if 'video' not in request.files:
            return jsonify({
                'status': 'error',
                'error': '動画ファイルが選択されていません'
            }), 400

        video_file = request.files['video']
        stage1_result_json = request.form.get('stage1_result')
        
        if not stage1_result_json:
            return jsonify({
                'status': 'error',
                'error': '1段階の結果が提供されていません'
            }), 400

        stage1_result = json.loads(stage1_result_json)

        # 一時ファイル保存
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            video_file.save(tmp_file.name)
            video_path = tmp_file.name

        try:
            # 2段階実行
            generator = ManualWithImagesGenerator()
            stage2_result = generator.stage_2_extract_representative_frames(video_path, stage1_result)
            
            return jsonify({
                'status': 'success',
                'data': stage2_result
            })
                
        finally:
            # 一時ファイル削除
            try:
                os.unlink(video_path)
            except:
                pass

    except Exception as e:
        logger.error(f"2段階処理エラー: {e}")
        return jsonify({
            'status': 'error',
            'error': f'2段階のフレーム抽出でエラーが発生しました: {str(e)}'
        }), 500

@app.route('/api/video-manual/three-stage/stage3', methods=['POST'])
def api_stage3_generate_html():
    """マニュアル（画像あり）生成: HTMLマニュアル生成API"""
    try:
        if not HAS_VIDEO_MANUAL:
            return jsonify({
                'status': 'error',
                'error': '動画マニュアル生成機能が利用できません'
            }), 500

        data = request.get_json()
        stage1_result = data.get('stage1_result')
        stage2_result = data.get('stage2_result')

        if not stage1_result or not stage2_result:
            return jsonify({
                'status': 'error',
                'error': '1段階または2段階の結果が提供されていません'
            }), 400

        # マニュアル（画像あり）生成実行
        generator = ManualWithImagesGenerator()
        html_manual = generator.stage_3_generate_html_manual(stage1_result, stage2_result)
        
        return jsonify({
            'status': 'success',
            'data': {
                'html_manual': html_manual,
                'summary': {
                    'work_title': stage1_result.get('work_title', ''),
                    'total_steps': len(stage1_result.get('work_steps', [])),
                    'extracted_frames': len(stage2_result.get('extracted_frames', [])),
                    'html_length': len(html_manual)
                }
            }
        })

    except Exception as e:
        logger.error(f"マニュアル（画像あり）生成処理エラー: {e}")
        return jsonify({
            'status': 'error',
            'error': f'マニュアル（画像あり）生成のHTMLマニュアル生成でエラーが発生しました: {str(e)}'
        }), 500

def generate_fallback_html_manual(stage1_result, stage2_result):
    """Geminiが利用できない場合の代替HTML生成"""
    html_parts = []
    
    # タイトル
    work_title = stage1_result.get('work_title', '作業マニュアル')
    html_parts.append(f'<h1>{work_title}</h1>')
    
    # 手順リスト
    work_steps = stage1_result.get('work_steps', [])
    if work_steps:
        html_parts.append('<h2>作業手順</h2>')
        html_parts.append('<ol>')
        
        for step in work_steps:
            step_number = step.get('step_number', 1)
            step_title = step.get('step_title', f'手順{step_number}')
            step_description = step.get('step_description', '')
            
            html_parts.append(f'<li>')
            html_parts.append(f'<h3>ステップ {step_number}: {step_title}</h3>')
            
            # 画像の挿入
            if 'extracted_frames' in stage2_result:
                for frame in stage2_result['extracted_frames']:
                    if frame.get('step_number') == step_number and frame.get('image_data_url'):
                        html_parts.append(f'<figure data-step="{step_number}">')
                        html_parts.append(f'<img src="{frame["image_data_url"]}" alt="ステップ {step_number} の画像" style="max-width: 100%; height: auto;">')
                        html_parts.append(f'<figcaption>ステップ {step_number}: {step_title}</figcaption>')
                        html_parts.append('</figure>')
                        break
            
            # 説明
            if step_description:
                html_parts.append(f'<p>{step_description}</p>')
            
            html_parts.append('</li>')
        
        html_parts.append('</ol>')
    
    return '\n'.join(html_parts)

@app.route('/api/video-manual/three-stage/save-edited-image', methods=['POST'])
def api_save_edited_image():
    """編集済み画像保存API"""
    try:
        data = request.get_json()
        step_number = data.get('step_number')
        edited_image_data_url = data.get('edited_image_data_url')
        stage1_result = data.get('stage1_result', {})
        stage2_result = data.get('stage2_result', {})
        manual_id = data.get('manual_id')  # 追加：マニュアルIDを取得
        
        app.logger.info(f"編集済み画像保存開始: step={step_number}, manual_id={manual_id}")
        
        if not edited_image_data_url:
            return jsonify({'status': 'error', 'error': '編集済み画像データが必要です'})
        
        # 対象フレームを検索して更新
        updated = False
        for frame in stage2_result.get('extracted_frames', []):
            if frame.get('step_number') == step_number:
                frame['image_data_url'] = edited_image_data_url
                updated = True
                app.logger.info(f"フレーム {step_number} の画像を更新しました")
                break
        
        if not updated:
            app.logger.error(f"フレーム {step_number} が見つかりませんでした")
            return jsonify({'status': 'error', 'error': 'フレームが見つかりません'})
        
        # HTML再生成（元のcustom_promptを使用）
        from src.services.video_manual_with_images_generator import ManualWithImagesGenerator
        try:
            generator = ManualWithImagesGenerator()
            
            # マニュアルの生成設定からcustom_promptを取得
            custom_prompt = None
            if manual_id:
                from src.models.models import Manual
                manual = Manual.query.get(manual_id)
                if manual and manual.generation_config:
                    config = json.loads(manual.generation_config) if isinstance(manual.generation_config, str) else manual.generation_config
                    custom_prompt = config.get('custom_prompt')
                    app.logger.info(f"元のcustom_prompt取得: {custom_prompt}")
            
            html_manual = generator.stage_3_generate_html_manual(stage1_result, stage2_result, custom_prompt)
        except Exception as generator_error:
            app.logger.error(f"HTML生成エラー: {generator_error}")
            # Geminiが利用できない場合の代替処理
            html_manual = generate_fallback_html_manual(stage1_result, stage2_result)
        
        # データベースに保存（重要：永続化）
        if manual_id:
            try:
                from src.models.models import Manual
                manual = Manual.query.get(manual_id)
                if manual:
                    # stage2_contentとstage3_contentを更新
                    manual.stage2_content = json.dumps(stage2_result, ensure_ascii=False, indent=2)
                    manual.stage3_content = html_manual
                    
                    # データベースにコミット
                    db.session.commit()
                    app.logger.info(f"マニュアル {manual_id} をデータベースに保存しました")
                else:
                    app.logger.error(f"マニュアル {manual_id} が見つかりません")
            except Exception as db_error:
                app.logger.error(f"データベース保存エラー: {db_error}")
                db.session.rollback()
        
        app.logger.info(f"編集済み画像保存完了: step={step_number}")
        
        return jsonify({
            'status': 'success',
            'data': {
                'stage2_result': stage2_result,
                'html_manual': html_manual
            }
        })
        
    except Exception as e:
        app.logger.error(f"編集済み画像保存エラー: {e}")
        return jsonify({'status': 'error', 'error': str(e)})

@app.route('/api/video-manual/three-stage/rotation', methods=['POST'])
def api_update_frame_rotation():
    """(2)(3)(4)対応: 指定ステップ画像の回転角を更新し Stage3 HTML を再生成して返す"""
    try:
        logger.info("画像回転API呼び出し開始")
        
        data = request.get_json() or {}
        stage1_result = data.get('stage1_result')
        stage2_result = data.get('stage2_result')
        step_number = int(data.get('step_number')) if 'step_number' in data else None
        rotation = int(data.get('rotation')) if 'rotation' in data else 0
        
        logger.info(f"パラメータ: step_number={step_number}, rotation={rotation}")
        
        if rotation not in (0, 90, 180, 270):
            logger.error(f"無効な回転角度: {rotation}")
            return jsonify({'status': 'error', 'error': 'rotationは0/90/180/270のみ許可'}), 400
            
        if not stage1_result or not stage2_result:
            logger.error("stage1_result または stage2_result が不足")
            return jsonify({'status': 'error', 'error': 'stage1_result / stage2_result が不足'}), 400
        
        frames = stage2_result.get('extracted_frames') or []
        logger.info(f"フレーム数: {len(frames)}")
        
        target_frame = None
        frame_index = -1
        
        # 対象フレームを検索
        for i, f in enumerate(frames):
            if f.get('step_number') == step_number:
                target_frame = f
                frame_index = i
                logger.info(f"対象フレーム見つかりました: index={i}, step={step_number}")
                break
        
        if target_frame is None:
            logger.error(f"指定ステップが見つかりません: {step_number}")
            return jsonify({'status': 'error', 'error': '指定ステップが見つかりません'}), 404
        
        # 現在の回転角度を取得
        current_rotation = int(target_frame.get('rotation', 0) or 0)
        logger.info(f"現在の回転角度: {current_rotation}")
        
        # 新しい回転角度と現在の角度の差分を計算
        rotation_delta = (rotation - current_rotation) % 360
        logger.info(f"回転差分: {rotation_delta}度")
        
        # 画像データを実際に回転させる
        if rotation_delta != 0 and 'image_data_url' in target_frame:
            try:
                logger.info("画像回転処理を開始")
                # 画像を回転
                rotated_data_url = rotate_image_data_url(target_frame['image_data_url'], rotation_delta)
                logger.info("画像回転処理完了")
                
                # フレームデータを更新
                target_frame['image_data_url'] = rotated_data_url
                target_frame['rotation'] = rotation
                
                # stage2_resultのフレームリストを更新
                frames[frame_index] = target_frame
                stage2_result['extracted_frames'] = frames
                
                logger.info(f"ステップ {step_number} の画像を {rotation_delta}度回転しました（合計回転角: {rotation}度）")
                
            except Exception as e:
                logger.error(f"画像回転処理エラー: {e}")
                return jsonify({'status': 'error', 'error': f'画像回転処理に失敗しました: {str(e)}'}), 500
        else:
            # 回転角度のみ更新（画像は変更なし）
            logger.info(f"回転なし、角度のみ更新: {rotation}")
            target_frame['rotation'] = rotation
            frames[frame_index] = target_frame
            stage2_result['extracted_frames'] = frames
        
        # Stage3再生成
        logger.info("Stage3 HTML再生成開始")
        generator = ManualWithImagesGenerator()
        html_manual = generator.stage_3_generate_html_manual(stage1_result, stage2_result, data.get('custom_prompt'))
        logger.info("Stage3 HTML再生成完了")
        
        # データベースに保存（重要：永続化）
        manual_id = data.get('manual_id')
        if manual_id:
            try:
                from src.models.models import Manual
                manual = Manual.query.get(manual_id)
                if manual:
                    # stage2_contentとstage3_contentを更新
                    manual.stage2_content = json.dumps(stage2_result, ensure_ascii=False, indent=2)
                    manual.stage3_content = html_manual
                    
                    # データベースにコミット
                    db.session.commit()
                    logger.info(f"マニュアル {manual_id} の回転をデータベースに保存しました")
                else:
                    logger.error(f"マニュアル {manual_id} が見つかりません")
            except Exception as db_error:
                logger.error(f"データベース保存エラー: {db_error}")
                db.session.rollback()
        
        return jsonify({
            'status': 'success',
            'data': {
                'stage2_result': stage2_result,
                'html_manual': html_manual
            }
        })
    except Exception as e:
        logger.error(f"回転更新APIエラー: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/login', methods=['GET'])
def login_page():
    """ログインページ"""
    if HAS_AUTH_SYSTEM:
        return render_template('login.html')
    else:
        # 認証システムがない場合はマニュアル一覧にリダイレクト
        return redirect(url_for('manual_list'))

# 動画再キャプチャ機能
@app.route('/api/recapture', methods=['POST'])
def api_recapture_frame():
    """動画フレーム再キャプチャAPI"""
    try:
        import time
        t0 = time.perf_counter()
        if not HAS_VIDEO_MANUAL:
            return jsonify({
                'status': 'error',
                'error': '動画処理機能が利用できません'
            }), 500
        
        # リクエストデータの取得
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'error': 'リクエストデータが不正です'
            }), 400
        
        video_path = data.get('video_path')
        timestamp = data.get('timestamp')  # 秒単位
        
        if not video_path or timestamp is None:
            return jsonify({
                'status': 'error',
                'error': 'video_pathとtimestampが必要です'
            }), 400
        
        # OpenCVでフレーム抽出
        import cv2
        import base64
        import numpy as np

        # パス正規化（ストリーミングと整合性を保つ）
        from utils.path_normalization import normalize_video_path
        canonical, _cand = normalize_video_path(video_path)
        video_path_normalized = canonical
        t1 = time.perf_counter()

        # ファイルマネージャーから実際のパスを取得（シングルトン）
        file_manager = get_file_manager()
        local_video_path = file_manager.get_local_path(video_path_normalized)
        t2 = time.perf_counter()

        if not local_video_path or not os.path.exists(local_video_path):
            return jsonify({
                'status': 'error',
                'error': '動画ファイルが見つかりません'
            }), 404

        # OpenCVで動画を開く
        cap = cv2.VideoCapture(local_video_path)
        t3 = time.perf_counter()
        if not cap.isOpened():
            return jsonify({
                'status': 'error',
                'error': '動画ファイルを開けませんでした'
            }), 500

        try:
            # FPSを取得
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30.0  # デフォルト値
            
            # 指定時刻のフレーム番号を計算
            frame_number = int(timestamp * fps)
            
            # フレーム位置を設定
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            t4 = time.perf_counter()
            
            # フレームを読み取り
            ret, frame = cap.read()
            t5 = time.perf_counter()
            if not ret:
                return jsonify({
                    'status': 'error',
                    'error': '指定された時刻のフレームを取得できませんでした'
                }), 400
            
            # フレームをBase64エンコード
            # 強制上下補正
            try:
                from utils.frame_orientation import enforce_vertical_orientation, ALWAYS_FLIP_VERTICAL, ALWAYS_FLIP_HORIZONTAL
                before_shape = frame.shape if frame is not None else None
                frame = enforce_vertical_orientation(frame)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"orientation.flip applied vertical={ALWAYS_FLIP_VERTICAL} horizontal={ALWAYS_FLIP_HORIZONTAL} shape={before_shape}")
            except Exception:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("orientation.flip skipped (exception)")
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            from PIL import Image
            pil_image = Image.fromarray(frame_rgb)
            
            # 一時的にメモリ上でJPEGエンコード
            import io
            buffer = io.BytesIO()
            pil_image.save(buffer, format='JPEG', quality=85)
            t6 = time.perf_counter()
            image_data = buffer.getvalue()
            
            # Base64エンコード
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            data_url = f'data:image/jpeg;base64,{image_base64}'
            
            logger.info(
                "フレーム再キャプチャ成功: timestamp=%.3f秒 frame=%s path=%s timing(ms): normalize=%.1f get_local=%.1f open=%.1f seek=%.1f read=%.1f encode=%.1f total=%.1f" % (
                    timestamp,
                    frame_number,
                    video_path_normalized,
                    (t1 - t0)*1000,
                    (t2 - t1)*1000,
                    (t3 - t2)*1000,
                    (t4 - t3)*1000,
                    (t5 - t4)*1000,
                    (t6 - t5)*1000,
                    (t6 - t0)*1000,
                )
            )
            
            return jsonify({
                'status': 'success',
                'data': {
                    'image_data_url': data_url,
                    'timestamp': timestamp,
                    'frame_number': frame_number
                }
            })
            
        finally:
            cap.release()
            
    except Exception as e:
        logger.error(f"フレーム再キャプチャエラー: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': f'フレーム抽出に失敗しました: {str(e)}'
        }), 500

@app.route('/api/video/<path:video_path>')
def stream_video(video_path):
    """動画ストリーミング (Range対応 / GCS最適化 / 直リンクオプション)

    機能:
      - ?direct=1 & GCS: 署名付きURLへ 302 リダイレクト
      - Range ヘッダ (bytes= start-end / start- / -suffix) を解析し 206 応答
      - GCS + Range: download_as_bytes による部分取得 (フルダウンロード不要)
      - フォールバック: ローカル/キャッシュファイルから逐次送信
    """
    try:
        file_manager = get_file_manager()
        direct = request.args.get('direct') == '1'

        # --- パス正規化 / フォールバック候補生成 (utility 利用) ---
        try:
            from utils.path_normalization import normalize_video_path, fix_mp4_extension
            canonical, cand_list = normalize_video_path(video_path)
            original_path = video_path
            video_path = canonical
            normalized_list = cand_list
            
            # 追加的に _mp4 拡張子の候補も生成
            extra_candidates = []
            for cand in normalized_list:
                mp4_fixed = fix_mp4_extension(cand)
                if mp4_fixed != cand and mp4_fixed not in normalized_list:
                    extra_candidates.append(mp4_fixed)
            normalized_list.extend(extra_candidates)
            
        except Exception as e:
            logger.warning(f"Video path normalization failed path={video_path} err={e}")
            original_path = video_path
            normalized_list = [video_path]

        selected_path = None
        existence_map = {}
        for cand in normalized_list:
            exists = file_manager.file_exists(cand)
            existence_map[cand] = exists
            if exists and selected_path is None:
                selected_path = cand

        if selected_path is None:
            logger.warning(f"Video not found after normalization. original={original_path} tried={existence_map}")
            
            # フォールバック機能: 同じ元ファイル名の代替ファイルを検索
            alternative_path = find_alternative_video_file(original_path)
            if alternative_path:
                logger.info(f"Video fallback found: {original_path} -> {alternative_path}")
                return redirect(f"/api/video/{alternative_path}", code=302)
            
            abort(404)

        if selected_path != original_path:
            logger.info(f"Video path normalized: original={original_path} -> selected={selected_path}")

        video_path = selected_path  # 以降は正規化済みを使用

        # 署名付きURLリダイレクト (正規化後パス)
        if direct and file_manager.storage_type == 'gcs':
            try:
                signed = file_manager.backend.get_file_url(video_path, expires_in=300)
                return redirect(signed, code=302)
            except Exception as e:
                logger.error(f"Signed URL redirect failed: {e} path={video_path}")
                abort(500)
        range_header = request.headers.get('Range')

        # GCS 直接部分取得パス
        if file_manager.storage_type == 'gcs' and range_header:
            try:
                blob = file_manager.backend.bucket.blob(video_path)
                blob.reload()  # size 取得
                file_size = getattr(blob, 'size', None)
                if file_size is None:
                    # サイズ無い場合はフォールバック
                    raise RuntimeError('blob size unavailable')

                def parse_range(header: str, total: int):
                    # bytes=START-END | START- | -SUFFIX
                    try:
                        units, spec = header.split('=')
                        if units.strip() != 'bytes':
                            raise ValueError('Unsupported unit')
                        start_str, end_str = spec.split('-', 1)
                        if start_str == '' and end_str == '':
                            raise ValueError('Empty range')
                        if start_str == '':  # suffix range
                            length = int(end_str)
                            if length <= 0:
                                raise ValueError('Invalid suffix length')
                            start = max(0, total - length)
                            end = total - 1
                        else:
                            start = int(start_str)
                            if end_str == '':
                                end = total - 1
                            else:
                                end = int(end_str)
                            if start > end:
                                raise ValueError('start > end')
                            if start >= total:
                                raise ValueError('start >= total')
                            if end >= total:
                                end = total - 1
                        return start, end
                    except Exception as e:
                        raise ValueError(f"Invalid range header: {header} ({e})")

                try:
                    start, end = parse_range(range_header, file_size)
                except ValueError as e:
                    logger.warning(str(e))
                    # 416 応答
                    rv = Response(status=416)
                    rv.headers['Content-Range'] = f'bytes */{file_size}'
                    return rv

                byte_count = end - start + 1
                # download_as_bytes は end が inclusive なので end をそのまま渡す
                data = blob.download_as_bytes(start=start, end=end)
                if len(data) != byte_count:
                    logger.debug(f"Partial fetch size mismatch expected={byte_count} got={len(data)}")

                rv = Response(data, status=206, mimetype='video/mp4', direct_passthrough=True)
                rv.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
                rv.headers['Accept-Ranges'] = 'bytes'
                rv.headers['Content-Length'] = str(len(data))
                return rv
            except Exception as e:
                logger.error(f"GCS partial range path failed -> fallback: {e}")
                # フォールバックへ続行

        # フォールバック: ローカルまたはキャッシュファイル
        local_path = file_manager.get_local_path(video_path)
        if not local_path or not os.path.exists(local_path):
            logger.warning(f"Local/cache file missing after existence check path={video_path} local_path={local_path}")
            abort(404)
        file_size = os.path.getsize(local_path)

        if range_header:
            # シンプルな bytes=START-END 解析
            try:
                units, spec = range_header.split('=')
                if units.strip() != 'bytes':
                    raise ValueError('Unsupported unit')
                start_str, end_str = spec.split('-', 1)
                if start_str == '':  # suffix not supported here -> 416
                    raise ValueError('Suffix range unsupported in fallback')
                start = int(start_str)
                if end_str == '':
                    end = file_size - 1
                else:
                    end = int(end_str)
                if start > end or start >= file_size:
                    raise ValueError('Invalid start/end')
                if end >= file_size:
                    end = file_size - 1
            except Exception as e:
                logger.warning(f"Fallback range parse error {range_header}: {e}")
                rv = Response(status=416)
                rv.headers['Content-Range'] = f'bytes */{file_size}'
                return rv

            length = end - start + 1

            def generate_part(s, e):
                with open(local_path, 'rb') as f:
                    f.seek(s)
                    remaining = e - s + 1
                    chunk = 256 * 1024
                    while remaining > 0:
                        read_size = min(chunk, remaining)
                        data = f.read(read_size)
                        if not data:
                            break
                        yield data
                        remaining -= len(data)

            rv = Response(generate_part(start, end), status=206, mimetype='video/mp4', direct_passthrough=True)
            rv.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            rv.headers['Accept-Ranges'] = 'bytes'
            rv.headers['Content-Length'] = str(length)
            return rv

        # フル配信
        def generate_full():
            with open(local_path, 'rb') as f:
                chunk = 256 * 1024
                while True:
                    data = f.read(chunk)
                    if not data:
                        break
                    yield data
        rv = Response(generate_full(), mimetype='video/mp4')
        rv.headers['Accept-Ranges'] = 'bytes'
        rv.headers['Content-Length'] = str(file_size)
        return rv

    except Exception as e:
        logger.error(f"Video streaming fatal error: {e}", exc_info=True)
        abort(500)

if __name__ == '__main__':
    try:
        # FLASK_ENVが'production'でない場合（開発環境など）にのみデバッグモードを有効にし、DBを初期化
        is_debug = os.environ.get('FLASK_ENV') != 'production'

        if is_debug:
            logger.info("Development mode detected. Initializing database...")
            if HAS_AUTH_SYSTEM:
                with app.app_context():
                    init_database()
                    logger.info("Database initialization completed for development.")
        else:
            logger.info("Production mode detected. Skipping database initialization.")

        logger.info("Starting Manual Generator application...")
        logger.info(f"Google Cloud features available: {HAS_GOOGLE_CLOUD}")
        logger.info(f"Gemini service available: {HAS_GEMINI_SERVICE}")
        logger.info(f"Video manual generation available: {HAS_VIDEO_MANUAL}")
        
        # is_debug変数を使ってデバッグモードを制御
        app.run(debug=is_debug, host='0.0.0.0', port=5000)
        
    except Exception as e:
        logger.error(f"Application startup error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
