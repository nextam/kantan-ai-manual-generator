"""
ファイル管理システム
ローカルストレージとクラウドストレージ（GCS/S3）の統一インターフェース
"""

import os
import uuid
import shutil
import threading
from pathlib import Path
from typing import Optional, Dict, Any, BinaryIO, List
from abc import ABC, abstractmethod
import json
import hashlib

from werkzeug.utils import secure_filename
from google.cloud import storage as gcs
from src.utils.path_normalization import fix_mp4_extension
import logging
logger = logging.getLogger(__name__)

class StorageBackend(ABC):
    """ストレージバックエンドの抽象基底クラス"""
    
    @abstractmethod
    def save_file(self, file_obj: BinaryIO, filename: str, folder: str = None, company_id: int = None) -> Dict[str, Any]:
        """ファイルを保存"""
        pass
    
    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """ファイルを削除"""
        pass
    
    @abstractmethod
    def get_file_url(self, file_path: str, expires_in: int = 3600) -> str:
        """ファイルのアクセスURLを取得"""
        pass
    
    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        """ファイルの存在確認"""
        pass

class LocalStorageBackend(StorageBackend):
    """ローカルストレージバックエンド"""
    
    def __init__(self, base_path: str = "uploads"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save_file(self, file_obj: BinaryIO, filename: str, folder: str = None, company_id: int = None) -> Dict[str, Any]:
        """ローカルファイル保存"""
        # ファイル名を安全に処理（拡張子を保持）
        secure_name = secure_filename(filename)
        
        # 拡張子を元のファイル名から取得
        original_ext = ''
        if '.' in filename:
            original_ext = '.' + filename.rsplit('.', 1)[1].lower()
        
        # secure_filenameが空の場合や拡張子が失われた場合の対処
        if not secure_name or secure_name == original_ext.lstrip('.'):
            # ファイル名の本体部分がない場合、generic nameを使用
            secure_name = f"file{original_ext}"
        elif original_ext and not secure_name.lower().endswith(original_ext):
            # 拡張子が失われた場合、追加
            secure_name += original_ext
        
        unique_filename = f"{uuid.uuid4()}_{secure_name}"
        
        # フォルダ構造作成
        if folder:
            folder_path = self.base_path / folder
            folder_path.mkdir(parents=True, exist_ok=True)
            file_path = folder_path / unique_filename
        else:
            file_path = self.base_path / unique_filename
        
        # ファイル保存
        file_obj.seek(0)
        with open(file_path, 'wb') as f:
            shutil.copyfileobj(file_obj, f)
        
        # ファイルサイズとハッシュ計算
        file_size = file_path.stat().st_size
        file_hash = self._calculate_file_hash(file_path)
        
        return {
            'file_path': str(file_path.relative_to(self.base_path)),
            'full_path': str(file_path),
            'filename': unique_filename,
            'original_filename': filename,
            'file_size': file_size,
            'file_hash': file_hash,
            'storage_type': 'local'
        }
    
    def delete_file(self, file_path: str) -> bool:
        """ローカルファイル削除"""
        try:
            full_path = self.base_path / file_path
            if full_path.exists():
                full_path.unlink()
                return True
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
        return False
    
    def get_file_url(self, file_path: str, expires_in: int = 3600) -> str:
        """ローカルファイルURL（相対パス）"""
        return f"/uploads/{file_path}"
    
    def file_exists(self, file_path: str) -> bool:
        """ローカルファイル存在確認"""
        return (self.base_path / file_path).exists()
    
    def get_absolute_path(self, file_path: str) -> str:
        """ファイルの絶対パスを取得"""
        full_path = self.base_path / file_path
        return str(full_path.absolute()) if full_path.exists() else None
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """ファイルのSHA256ハッシュ計算"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

class GCSStorageBackend(StorageBackend):
    """Google Cloud Storageバックエンド"""
    
    def __init__(self, bucket_name: str = None, credentials_path: str = None, cdn_domain: str = None):
        # Auto-select bucket based on ENVIRONMENT variable if not explicitly provided
        if not bucket_name:
            environment = os.getenv('ENVIRONMENT', 'development')
            if environment == 'production':
                bucket_name = 'kantan-ai-manual-generator-live'
            else:
                bucket_name = 'kantan-ai-manual-generator-dev'
            logger.info(f"GCS Backend auto-selected bucket: environment={environment}, bucket={bucket_name}")
        else:
            logger.info(f"GCS Backend using provided bucket: {bucket_name}")
        
        # CDN configuration
        self.cdn_domain = cdn_domain or os.getenv('CDN_DOMAIN')
        
        self.bucket_name = bucket_name
        
        # { file_path: { 'local_path': str, 'size': int } }
        self._download_cache = {}
        self._cache_lock = threading.Lock()

        resolved = None

        def _exists(p: str) -> bool:
            return p and os.path.isfile(p)

        # 既存環境変数が有効なら最優先で保持
        env_current = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if env_current and _exists(env_current):
            resolved = env_current
        else:
            # 引数優先で解決
            cand = credentials_path
            if cand:
                cand = cand.strip().strip('"').strip("'")
                if not os.path.isabs(cand):
                    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # リポジトリルート想定
                    manual_dir = os.path.dirname(os.path.abspath(__file__))  # manual_generator/
                    # 候補探索順
                    candidates = [
                        os.path.join(repo_root, cand),
                        os.path.join(manual_dir, cand),
                        os.path.join(manual_dir, '..', cand),
                    ]
                    for c in candidates:
                        if _exists(c):
                            resolved = os.path.abspath(c)
                            break
                elif _exists(cand):
                    resolved = cand
            # .env 由来環境変数ロード (引数で決まらなかった場合)
            if not resolved:
                from dotenv import load_dotenv
                load_dotenv()
                env_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                if env_creds:
                    env_creds = env_creds.strip().strip('"').strip("'")
                    if not os.path.isabs(env_creds):
                        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        manual_dir = os.path.dirname(os.path.abspath(__file__))
                        for c in [
                            os.path.join(repo_root, env_creds),
                            os.path.join(manual_dir, env_creds)
                        ]:
                            if _exists(c):
                                resolved = os.path.abspath(c)
                                break
                    elif _exists(env_creds):
                        resolved = env_creds

        if resolved:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = resolved
            logger.info(f"Using GCP credentials: {resolved} exists={_exists(resolved)}")
        else:
            logger.warning("GCP credentials file could not be resolved; Client init may fail")

        # クライアント初期化 (失敗時は例外を握りつぶさず上位でログ)
        self.client = gcs.Client()
        self.bucket = self.client.bucket(bucket_name)
    
    def save_file(self, file_obj: BinaryIO, filename: str, folder: str = None, company_id: int = None) -> Dict[str, Any]:
        """GCSファイル保存（company_idベースのフォルダ構造、CDN対応キャッシュヘッダー設定）"""
        # ファイル名を安全に処理（拡張子を保持）
        secure_name = secure_filename(filename)
        
        # 拡張子を元のファイル名から取得
        original_ext = ''
        if '.' in filename:
            original_ext = '.' + filename.rsplit('.', 1)[1].lower()
        
        # secure_filenameが空の場合や拡張子が失われた場合の対処
        if not secure_name or secure_name == original_ext.lstrip('.'):
            # ファイル名の本体部分がない場合、generic nameを使用
            secure_name = f"file{original_ext}"
        elif original_ext and not secure_name.lower().endswith(original_ext):
            # 拡張子が失われた場合、追加
            secure_name += original_ext
        
        unique_filename = f"{uuid.uuid4()}_{secure_name}"
        
        # Folder structure enforces tenant isolation at root level
        # For multi-tenancy: folder should already be in format "company_{id}/videos"
        # No additional prepending needed if folder already contains company prefix
        if folder:
            blob_name = f"{folder}/{unique_filename}"
        else:
            blob_name = unique_filename
        
        blob = self.bucket.blob(blob_name)
        
        # Set cache headers for CDN optimization
        if original_ext in ['.mp4', '.ts', '.m3u8', '.webm', '.mov']:
            # Video files: cache for 24 hours
            blob.cache_control = 'public, max-age=86400'
            blob.content_type = self._get_content_type(original_ext)
        elif original_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            # Image files: cache for 7 days
            blob.cache_control = 'public, max-age=604800'
            blob.content_type = self._get_content_type(original_ext)
        
        file_obj.seek(0)
        
        # ファイルアップロード
        blob.upload_from_file(file_obj)
        
        return {
            'file_path': blob_name,
            'filename': unique_filename,
            'original_filename': filename,
            'file_size': blob.size,
            'gcs_uri': f"gs://{self.bucket_name}/{blob_name}",
            'storage_type': 'gcs',
            'cdn_url': self._get_cdn_url(blob_name) if self.cdn_domain else None
        }
    
    def _get_content_type(self, extension: str) -> str:
        """Get content type based on file extension"""
        content_types = {
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.mov': 'video/quicktime',
            '.ts': 'video/mp2t',
            '.m3u8': 'application/vnd.apple.mpegurl',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        return content_types.get(extension.lower(), 'application/octet-stream')
    
    def _get_cdn_url(self, blob_name: str) -> str:
        """Get CDN URL for a blob"""
        if self.cdn_domain:
            return f"https://{self.cdn_domain}/{blob_name}"
        return None
    
    def delete_file(self, file_path: str) -> bool:
        """GCSファイル削除"""
        try:
            blob = self.bucket.blob(file_path)
            blob.delete()
            
            # キャッシュからも削除
            if file_path in self._download_cache:
                cached_path = self._download_cache[file_path]
                if os.path.exists(cached_path):
                    try:
                        os.remove(cached_path)
                    except:
                        pass
                del self._download_cache[file_path]
            
            return True
        except Exception as e:
            print(f"Error deleting GCS file {file_path}: {e}")
            return False
    
    def get_file_url(self, file_path: str, expires_in: int = 3600) -> str:
        """GCS署名付きURL生成（CDN優先）"""
        # CDN URLが利用可能な場合は優先
        if self.cdn_domain:
            return self._get_cdn_url(file_path)
        
        # Fallback to signed URL
        blob = self.bucket.blob(file_path)
        return blob.generate_signed_url(
            version="v4",
            expiration=expires_in,
            method="GET"
        )
    
    def file_exists(self, file_path: str) -> bool:
        """GCSファイル存在確認"""
        blob = self.bucket.blob(file_path)
        return blob.exists()
    
    def download_to_temp(self, file_path: str) -> str:
        """GCSファイルをキャッシュ付きでローカルに取得しパスを返す

        改善点:
          - 以前は毎回 uuid 付き temp を生成し再ダウンロードしていた
          - blob.size を利用してサイズ一致で再利用
          - 同時アクセス時の重複ダウンロードをロックで防止
          - 決定的一時パス: ハッシュ + 元ファイル名
        """
        import tempfile
        import hashlib

        # gs:// 対応: 内部 blob_path の抽出
        if file_path.startswith('gs://'):
            parts = file_path.replace('gs://', '').split('/', 1)
            blob_path = parts[1] if len(parts) > 1 else ''
        else:
            blob_path = file_path

        if not blob_path:
            logger.error(f"Invalid GCS path: {file_path}")
            return None

        blob = self.bucket.blob(blob_path)
        if not blob.exists():
            logger.warning(f"GCS file not found: {file_path}")
            return None

        try:
            blob.reload()  # 最新メタデータ取得 (size 等)
        except Exception:
            pass  # size が無くても続行

        expected_size = getattr(blob, 'size', None)

        # 決定的キャッシュファイル名: sha1(bucket + path) + original basename
        h = hashlib.sha1(f"{self.bucket_name}:{blob_path}".encode('utf-8')).hexdigest()[:16]
        safe_base = os.path.basename(blob_path)
        cache_filename = f"gcs_cache_{h}_{safe_base}"
        temp_dir = os.path.join(tempfile.gettempdir(), 'gcs_cache')
        os.makedirs(temp_dir, exist_ok=True)
        cache_path = os.path.join(temp_dir, cache_filename)

        with self._cache_lock:
            meta = self._download_cache.get(file_path)
            if meta:
                local_path = meta.get('local_path')
                size = meta.get('size')
                if local_path and os.path.exists(local_path):
                    if expected_size is None or size == expected_size:
                        logger.info(f"GCS cache hit: {file_path} -> {local_path}")
                        return local_path
                    else:
                        logger.info(f"GCS cache size mismatch -> re-download: {file_path}")

        # 既存キャッシュファイルだけ存在するがメタ無い場合 (異常終了後など)
        if os.path.exists(cache_path) and expected_size is not None:
            actual_size = os.path.getsize(cache_path)
            if actual_size == expected_size:
                with self._cache_lock:
                    self._download_cache[file_path] = {'local_path': cache_path, 'size': actual_size}
                logger.info(f"GCS orphan cache reattached: {file_path} -> {cache_path}")
                return cache_path

        logger.info(f"GCS cache miss: downloading {file_path}")
        try:
            # 一時ファイルに直接保存 (決定的パス)
            blob.download_to_filename(cache_path)
            actual_size = os.path.getsize(cache_path)
            with self._cache_lock:
                self._download_cache[file_path] = {'local_path': cache_path, 'size': actual_size}
            logger.info(f"GCS download complete: {file_path} size={actual_size}")
            return cache_path
        except Exception as e:
            logger.error(f"Error downloading GCS file {file_path}: {e}")
            return None


class FileManager:
    """統一ファイル管理システム"""
    
    def __init__(self, storage_type: str = 'gcs', storage_config: Dict[str, Any] = None):
        self.storage_type = storage_type
        self.storage_config = storage_config or {}
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.backend = self._create_backend()
        
        # Video optimization settings from environment
        self.enable_video_optimization = os.getenv('ENABLE_VIDEO_OPTIMIZATION', 'true').lower() == 'true'
        self.enable_hls_generation = os.getenv('ENABLE_HLS_GENERATION', 'true').lower() == 'true'
        self.video_quality = os.getenv('VIDEO_OPTIMIZATION_QUALITY', '720p')
        
        # Initialize video services if enabled
        self.video_optimizer = None
        self.hls_generator = None
        if self.enable_video_optimization or self.enable_hls_generation:
            try:
                from src.services.video_optimizer import VideoOptimizer
                from src.services.hls_generator import HLSGenerator
                self.video_optimizer = VideoOptimizer()
                self.hls_generator = HLSGenerator()
                logger.info("Video optimization services initialized")
            except Exception as e:
                logger.warning(f"Video optimization services not available: {e}")
    
    def _create_backend(self) -> StorageBackend:
        """ストレージバックエンドの作成"""
        if self.storage_type == 'local':
            return LocalStorageBackend(
                base_path=self.storage_config.get('base_path', 'uploads')
            )
        elif self.storage_type == 'gcs':
            return GCSStorageBackend(
                bucket_name=self.storage_config['bucket_name'],
                credentials_path=self.storage_config.get('credentials_path'),
                cdn_domain=self.storage_config.get('cdn_domain')
            )
        else:
            raise ValueError(f"Unsupported storage type: {self.storage_type}")
    
    def save_file(self, file_obj: BinaryIO, filename: str, 
                  file_type: str = None, folder: str = None, company_id: int = None) -> Dict[str, Any]:
        """ファイル保存"""
        # ファイルタイプに基づくフォルダ分類
        if file_type and not folder:
            folder = file_type
        
        result = self.backend.save_file(file_obj, filename, folder, company_id)
        result['file_type'] = file_type
        return result
    
    async def upload_base64_image(self, image_base64: str, filename: str, 
                                   folder: str = 'keyframes', company_id: int = None) -> str:
        """
        Upload base64-encoded image to storage
        
        Args:
            image_base64: Base64-encoded image data (without data URI prefix)
            filename: Target filename
            folder: Storage folder (default: 'keyframes')
            company_id: Company ID for multi-tenant isolation
            
        Returns:
            GCS URI or file path of uploaded image
        """
        import base64
        import io
        
        try:
            # Decode base64 to binary
            image_data = base64.b64decode(image_base64)
            
            # Create file-like object
            image_file = io.BytesIO(image_data)
            
            # Upload using save_file
            result = self.save_file(
                file_obj=image_file,
                filename=filename,
                file_type='images',
                folder=folder,
                company_id=company_id
            )
            
            # Return GCS URI or file path
            if self.storage_type == 'gcs':
                return result['file_path']  # gs://bucket/path/to/file.jpg
            else:
                return result['file_path']
                
        except Exception as e:
            logger.error(f"Failed to upload base64 image {filename}: {e}")
            raise
    
    def delete_file(self, file_path: str) -> bool:
        """ファイル削除"""
        return self.backend.delete_file(file_path)
    
    def get_file_url(self, file_path: str, expires_in: int = 3600) -> str:
        """ファイルURL取得"""
        return self.backend.get_file_url(file_path, expires_in)
    
    def file_exists(self, file_path: str) -> bool:
        """
        ファイル存在確認（拡張子正規化対応）
        _mp4 拡張子を .mp4 に正規化してチェック
        """
        # まず元のパスでチェック
        if self.backend.file_exists(file_path):
            return True
            
        # _mp4 を .mp4 に正規化してチェック
        normalized_path = fix_mp4_extension(file_path)
        if normalized_path != file_path:
            return self.backend.file_exists(normalized_path)
            
        return False
    
    def get_local_path(self, file_path: str) -> str:
        """
        ファイルのローカルパスを取得（拡張子正規化対応）
        GCSファイルの場合はダウンロードしてローカルパスを返す
        """
        def try_get_path(path: str) -> str:
            if self.storage_type == 'local':
                # ローカルストレージの場合、そのまま絶対パスを返す
                if isinstance(self.backend, LocalStorageBackend):
                    return self.backend.get_absolute_path(path)
                else:
                    return path
            elif self.storage_type == 'gcs':
                # GCSの場合、一時的にダウンロードしてローカルパスを返す
                if isinstance(self.backend, GCSStorageBackend):
                    return self.backend.download_to_temp(path)
                else:
                    return None
            else:
                return None
        
        # まず元のパスで試行
        result = try_get_path(file_path)
        if result and os.path.exists(result):
            return result
            
        # _mp4 を .mp4 に正規化して試行
        normalized_path = fix_mp4_extension(file_path)
        if normalized_path != file_path:
            result = try_get_path(normalized_path)
            if result and os.path.exists(result):
                return result
                
        # 元の結果を返す（存在しない場合でも）
        return try_get_path(file_path)
    
    def save_video_with_optimization(
        self, 
        file_obj: BinaryIO,
        filename: str,
        folder: str = None,
        company_id: int = None,
        generate_hls: bool = None
    ) -> Dict[str, Any]:
        """
        Save video file with automatic optimization and HLS generation
        
        Workflow:
        1. Save original file to temp location
        2. Optimize video (compress, web-optimize)
        3. Generate HLS variants if enabled
        4. Upload optimized MP4 and HLS files to storage
        5. Clean up temp files
        
        Args:
            file_obj: Video file object
            filename: Original filename
            folder: Target folder in storage
            company_id: Company ID for multi-tenant isolation
            generate_hls: Override HLS generation setting
            
        Returns:
            Dictionary with upload results including optimized and HLS URLs
        """
        import tempfile
        import shutil
        from pathlib import Path
        
        # Determine if HLS should be generated
        should_generate_hls = generate_hls if generate_hls is not None else self.enable_hls_generation
        
        # Create temp directory
        temp_dir = Path(tempfile.mkdtemp(prefix='video_upload_'))
        
        try:
            # Save original to temp
            original_ext = Path(filename).suffix
            temp_original = temp_dir / f"original{original_ext}"
            file_obj.seek(0)
            with open(temp_original, 'wb') as f:
                shutil.copyfileobj(file_obj, f)
            
            logger.info(f"Video saved to temp: {temp_original} ({os.path.getsize(temp_original)} bytes)")
            
            result = {
                'success': True,
                'original_filename': filename,
                'optimization_enabled': self.enable_video_optimization,
                'hls_enabled': should_generate_hls
            }
            
            # Step 1: Optimize video
            optimized_path = None
            if self.enable_video_optimization and self.video_optimizer:
                logger.info(f"Optimizing video: quality={self.video_quality}")
                temp_optimized = temp_dir / f"optimized{original_ext}"
                
                opt_result = self.video_optimizer.optimize_video(
                    str(temp_original),
                    str(temp_optimized),
                    quality=self.video_quality
                )
                
                if opt_result['success']:
                    optimized_path = temp_optimized
                    result['optimization'] = opt_result
                    logger.info(f"Video optimized: {opt_result['compression_ratio']} reduction")
                else:
                    logger.warning(f"Optimization failed: {opt_result.get('error')}")
                    logger.warning("Using original video")
                    optimized_path = temp_original
            else:
                logger.info("Video optimization disabled, using original")
                optimized_path = temp_original
            
            # Step 2: Upload optimized MP4
            with open(optimized_path, 'rb') as f:
                upload_result = self.backend.save_file(f, filename, folder, company_id)
            
            result['mp4'] = upload_result
            logger.info(f"Optimized video uploaded: {upload_result['file_path']}")
            
            # Step 3: Generate and upload HLS
            if should_generate_hls and self.hls_generator:
                logger.info("Generating HLS streams...")
                hls_dir = temp_dir / 'hls'
                hls_dir.mkdir(exist_ok=True)
                
                # Determine quality levels based on video size
                video_info = self.video_optimizer.get_video_info(str(optimized_path)) if self.video_optimizer else None
                quality_levels = self._determine_hls_quality_levels(video_info)
                
                hls_result = self.hls_generator.generate_hls(
                    str(optimized_path),
                    str(hls_dir),
                    quality_levels=quality_levels,
                    base_filename='video'
                )
                
                if hls_result['success']:
                    # Upload HLS files
                    hls_uploads = self._upload_hls_files(hls_dir, folder, company_id)
                    result['hls'] = {
                        'master_playlist': hls_uploads.get('master_playlist'),
                        'variants': hls_result['variants'],
                        'files_uploaded': len(hls_uploads.get('files', []))
                    }
                    logger.info(f"HLS generation complete: {len(hls_uploads.get('files', []))} files uploaded")
                else:
                    logger.warning(f"HLS generation failed: {hls_result.get('error')}")
                    result['hls'] = {'success': False, 'error': hls_result.get('error')}
            
            return result
            
        except Exception as e:
            logger.error(f"Error in video upload with optimization: {e}")
            return {
                'success': False,
                'error': str(e),
                'original_filename': filename
            }
        finally:
            # Clean up temp directory
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"Temp directory cleaned: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean temp directory: {e}")
    
    def _determine_hls_quality_levels(self, video_info: Optional[Dict]) -> List[str]:
        """Determine appropriate HLS quality levels based on video info"""
        if not video_info:
            return ['360p', '720p']
        
        height = video_info.get('height', 720)
        
        if height >= 1080:
            return ['360p', '720p', '1080p']
        elif height >= 720:
            return ['360p', '720p']
        else:
            return ['360p']
    
    def _upload_hls_files(self, hls_dir: Path, folder: str, company_id: int) -> Dict:
        """Upload all HLS files to storage"""
        uploaded_files = []
        master_playlist_url = None
        
        # Create HLS subfolder
        hls_folder = f"{folder}/hls" if folder else "hls"
        
        # Upload all files in HLS directory
        for file_path in hls_dir.rglob('*'):
            if file_path.is_file():
                with open(file_path, 'rb') as f:
                    upload_result = self.backend.save_file(
                        f,
                        file_path.name,
                        hls_folder,
                        company_id
                    )
                    uploaded_files.append(upload_result)
                    
                    # Track master playlist
                    if file_path.name == 'master.m3u8':
                        master_playlist_url = upload_result.get('gcs_uri') or upload_result.get('file_path')
        
        return {
            'files': uploaded_files,
            'master_playlist': master_playlist_url
        }

def create_file_manager(company_storage_type: str = 'gcs', 
                       company_storage_config: Dict[str, Any] = None) -> FileManager:
    """企業設定に基づくファイルマネージャー作成"""
    if not company_storage_config:
        # Use environment-based defaults
        environment = os.getenv('ENVIRONMENT', 'development')
        if environment == 'production':
            bucket_name = 'kantan-ai-manual-generator-live'
        else:
            bucket_name = 'kantan-ai-manual-generator-dev'
        
        company_storage_config = {
            'bucket_name': bucket_name,
            'credentials_path': os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'gcp-credentials.json')
        }
    
    return FileManager(company_storage_type, company_storage_config)
