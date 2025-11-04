"""
ファイル管理システム
ローカルストレージとクラウドストレージ（GCS/S3）の統一インターフェース
"""

import os
import uuid
import shutil
import threading
from pathlib import Path
from typing import Optional, Dict, Any, BinaryIO
from abc import ABC, abstractmethod
import json
import hashlib

from werkzeug.utils import secure_filename
from google.cloud import storage as gcs
from utils.path_normalization import fix_mp4_extension
import logging
logger = logging.getLogger(__name__)

class StorageBackend(ABC):
    """ストレージバックエンドの抽象基底クラス"""
    
    @abstractmethod
    def save_file(self, file_obj: BinaryIO, filename: str, folder: str = None) -> Dict[str, Any]:
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
    
    def save_file(self, file_obj: BinaryIO, filename: str, folder: str = None) -> Dict[str, Any]:
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
    
    def __init__(self, bucket_name: str, credentials_path: str = None):
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
    
    def save_file(self, file_obj: BinaryIO, filename: str, folder: str = None) -> Dict[str, Any]:
        """GCSファイル保存"""
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
        
        if folder:
            blob_name = f"{folder}/{unique_filename}"
        else:
            blob_name = unique_filename
        
        blob = self.bucket.blob(blob_name)
        file_obj.seek(0)
        
        # ファイルアップロード
        blob.upload_from_file(file_obj)
        
        return {
            'file_path': blob_name,
            'filename': unique_filename,
            'original_filename': filename,
            'file_size': blob.size,
            'gcs_uri': f"gs://{self.bucket_name}/{blob_name}",
            'storage_type': 'gcs'
        }
    
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
        """GCS署名付きURL生成"""
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
    
    def __init__(self, storage_type: str = 'local', storage_config: Dict[str, Any] = None):
        self.storage_type = storage_type
        self.storage_config = storage_config or {}
        self.backend = self._create_backend()
    
    def _create_backend(self) -> StorageBackend:
        """ストレージバックエンドの作成"""
        if self.storage_type == 'local':
            return LocalStorageBackend(
                base_path=self.storage_config.get('base_path', 'uploads')
            )
        elif self.storage_type == 'gcs':
            return GCSStorageBackend(
                bucket_name=self.storage_config['bucket_name'],
                credentials_path=self.storage_config.get('credentials_path')
            )
        else:
            raise ValueError(f"Unsupported storage type: {self.storage_type}")
    
    def save_file(self, file_obj: BinaryIO, filename: str, 
                  file_type: str = None, folder: str = None) -> Dict[str, Any]:
        """ファイル保存"""
        # ファイルタイプに基づくフォルダ分類
        if file_type and not folder:
            folder = file_type
        
        result = self.backend.save_file(file_obj, filename, folder)
        result['file_type'] = file_type
        return result
    
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

def create_file_manager(company_storage_type: str = 'local', 
                       company_storage_config: Dict[str, Any] = None) -> FileManager:
    """企業設定に基づくファイルマネージャー作成"""
    return FileManager(company_storage_type, company_storage_config)
