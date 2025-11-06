"""
データベースモデル定義
企業テナント、ユーザー、ファイル、マニュアル、設定の管理
"""

from datetime import datetime, timezone, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

# 日本標準時（JST）の定義
JST = timezone(timedelta(hours=9))

def utc_to_jst_isoformat(utc_dt):
    """UTC日時をJST形式のISO文字列に変換"""
    if utc_dt is None:
        return None
    
    # タイムゾーン情報がない場合はUTCとして扱う
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    
    # JSTに変換（UTC+9時間）
    jst_dt = utc_dt.astimezone(JST)
    
    # JST形式のISO文字列を生成
    return jst_dt.strftime('%Y-%m-%dT%H:%M:%S+09:00')

# DEPRECATED: SuperAdmin is now managed through User.role='super_admin'
# This class is kept for backward compatibility only
class SuperAdmin(db.Model):
    """スーパー管理者（非推奨: User.role='super_admin'を使用してください）"""
    __tablename__ = 'super_admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # 権限レベル
    permission_level = db.Column(db.String(20), default='full')  # full, readonly
    
    def set_password(self, password):
        """パスワードハッシュ化"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """パスワード検証"""
        return check_password_hash(self.password_hash, password)
    
    def is_authenticated(self):
        return True
    
    def is_active_user(self):
        return self.is_active
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)
    
    def is_super_admin(self):
        """Compatibility method"""
        return True

class Company(db.Model):
    """企業テナント"""
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    company_code = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # 企業設定（JSON形式で保存）
    settings = db.Column(db.Text)  # JSON形式の設定
    
    # ストレージは常にGCS使用のため設定カラムを削除
    # storage_type = db.Column(db.String(20), default='local')  # 削除済み
    # storage_config = db.Column(db.Text)  # 削除済み
    
    # リレーション
    users = db.relationship('User', backref='company', lazy=True, cascade='all, delete-orphan')
    uploaded_files = db.relationship('UploadedFile', backref='company', lazy=True, cascade='all, delete-orphan')
    manuals = db.relationship('Manual', backref='company', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """パスワードハッシュ化"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """パスワード検証"""
        return check_password_hash(self.password_hash, password)
    
    def get_settings(self):
        """設定をJSONから取得"""
        if self.settings:
            return json.loads(self.settings)
        return {}
    
    def set_settings(self, settings_dict):
        """設定をJSONで保存"""
        self.settings = json.dumps(settings_dict, ensure_ascii=False)
    
    # ストレージ設定関連メソッドを削除
    # def get_storage_config(self):
    # def set_storage_config(self, config_dict):

class User(UserMixin, db.Model):
    """ユーザー（企業内のユーザー）"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)  # メールアドレスを必須化、グローバルユニーク制約
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    role = db.Column(db.String(20), default='user')  # user, admin, super_admin
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    password_hash = db.Column(db.String(255), nullable=False)  # パスワードを必須化
    language_preference = db.Column(db.String(10), default='ja')
    
    # 企業内でのユニーク制約は維持（互換性のため）
    __table_args__ = (db.UniqueConstraint('username', 'company_id', name='unique_username_per_company'),)
    
    def set_password(self, password):
        """パスワードハッシュ化"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """パスワード検証"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def is_super_admin(self):
        """スーパー管理者かどうか"""
        return self.role == 'super_admin'
    
    def is_company_admin(self):
        """企業管理者かどうか"""
        return self.role == 'admin'
    
    def is_general_user(self):
        """一般ユーザーかどうか"""
        return self.role == 'user'

class UploadedFile(db.Model):
    """アップロードファイル管理"""
    __tablename__ = 'uploaded_files'
    
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)  # video, document, image
    file_path = db.Column(db.String(500), nullable=False)  # ローカルパスまたはクラウドURI
    file_size = db.Column(db.BigInteger)
    mime_type = db.Column(db.String(100))
    
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # ファイルメタデータ（JSON形式）
    file_metadata = db.Column(db.Text)  # 動画の長さ、解像度など
    
    def get_metadata(self):
        """メタデータをJSONから取得"""
        if self.file_metadata:
            return json.loads(self.file_metadata)
        return {}
    
    def set_metadata(self, metadata_dict):
        """メタデータをJSONで保存"""
        self.file_metadata = json.dumps(metadata_dict, ensure_ascii=False)

class Manual(db.Model):
    """生成されたマニュアル"""
    __tablename__ = 'manuals'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)  # マニュアルの説明文
    content = db.Column(db.Text, nullable=False)
    # manual_type: 現在使用中の種類は basic / multi_stage / manual_with_images
    #   - basic: 単一動画から即時生成
    #   - multi_stage: 旧三段階（現在は画像なし処理表示用）
    #   - manual_with_images: 新しい画像付きマニュアル
    # 予約されていた comparison / comprehensive は未実装のためコメント化
    manual_type = db.Column(db.String(50), default='basic')  # basic, multi_stage, manual_with_images
    
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 生成ステータス管理
    generation_status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    generation_progress = db.Column(db.Integer, default=0)  # 0-100の進捗率
    error_message = db.Column(db.Text)  # エラーメッセージ
    
    # マニュアル（画像あり）生成用のフィールド
    stage1_content = db.Column(db.Text)  # 作業内容・手順の分析結果
    stage2_content = db.Column(db.Text)  # 熟練者と非熟練者の差異比較（表形式）
    stage3_content = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    generation_config = db.Column(db.Text, nullable=True)  # 生成設定(JSON形式)
    
    # Phase 5: Enhanced Manual Generation fields
    template_id = db.Column(db.Integer, db.ForeignKey('manual_templates.id'), nullable=True)
    video_uri = db.Column(db.String(500), nullable=True)  # GCS or S3 URI
    processing_job_id = db.Column(db.Integer, db.ForeignKey('processing_jobs.id'), nullable=True)
    rag_sources = db.Column(db.Text, nullable=True)  # JSON: RAG sources used
    completed_at = db.Column(db.DateTime, nullable=True)

    def get_generation_config(self):
        """生成設定をJSONから取得"""
        if self.generation_config:
            try:
                return json.loads(self.generation_config)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    
    def set_generation_config(self, config_dict):
        """生成設定をJSONで保存"""
        if config_dict:
            self.generation_config = json.dumps(config_dict, ensure_ascii=False)
        else:
            self.generation_config = None

    def to_dict(self):
        def sanitize_string(text):
            """JSON化の際に問題となる制御文字をサニタイズする"""
            if not text:
                return text
            # 制御文字を適切にエスケープ/置換
            import re
            # 不正な制御文字を除去（改行やタブは保持）
            text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
            return text
        
        return {
            'id': self.id,
            'title': sanitize_string(self.title),
            'content': sanitize_string(self.content),
            'company_id': self.company_id,
            'created_by': self.created_by,
            'created_at': utc_to_jst_isoformat(self.created_at),
            'updated_at': utc_to_jst_isoformat(self.updated_at),
            'manual_type': self.manual_type,
            'generation_status': self.generation_status,
            'generation_progress': self.generation_progress,
            'error_message': sanitize_string(self.error_message),
            'stage1_content': sanitize_string(self.stage1_content),
            'stage2_content': sanitize_string(self.stage2_content),
            'stage3_content': sanitize_string(self.stage3_content),
            'description': sanitize_string(self.description),
            'generation_config': self.get_generation_config()
        }

    def to_dict_summary(self):
        """一覧表示用の軽量データ構造を返す（巨大なcontentフィールドを除外）"""
        def sanitize_string(text):
            """JSON化の際に問題となる制御文字をサニタイズする"""
            if not text:
                return text
            import re
            text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
            return text
        
        return {
            'id': self.id,
            'title': sanitize_string(self.title),
            'company_id': self.company_id,
            'created_by': self.created_by,
            'created_at': utc_to_jst_isoformat(self.created_at),
            'updated_at': utc_to_jst_isoformat(self.updated_at),
            'manual_type': self.manual_type,
            'generation_status': self.generation_status,
            'generation_progress': self.generation_progress,
            'description': sanitize_string(self.description) if self.description else None,
            # 巨大なcontentフィールドは除外
            # 'content', 'stage1_content', 'stage2_content', 'stage3_content', 'error_message' は除外
        }

    def to_dict_with_sources(self):
        """関連するソース動画/ファイル情報を含めた辞書を返す。

        フロントエンド manual_detail.js などが期待する manual.source_videos 配列を提供する。
        後方互換のため既存 to_dict() は変更せず、新メソッドで拡張する。
        """
        base = self.to_dict()
        # 明示的クエリ: manual_id で関連ファイルを取得し UI 用フィールドへマッピング
        try:
            source_links = ManualSourceFile.query.filter_by(manual_id=self.id).all()
            if not source_links:
                base['source_videos'] = []
                return base

            file_ids = [l.file_id for l in source_links if l.file_id]
            files_map = {}
            if file_ids:
                for f in UploadedFile.query.filter(UploadedFile.id.in_(file_ids)).all():
                    files_map[f.id] = f

            from urllib.parse import quote
            ui_items = []
            for link in source_links:
                f = files_map.get(link.file_id)
                if not f:
                    continue
                # role を前提にフロント期待フィールドへマッピング
                role = (link.role or '').lower()
                vtype = role if role in ('expert', 'novice', 'document') else (f.file_type or 'video')
                raw_path = f.file_path
                # API 経由ストリーミング URL (エンコード) - gs:///ローカルいずれも /api/video/ に渡す
                encoded_path = quote(raw_path, safe='') if raw_path else ''
                stream_url = f"/api/video/{encoded_path}" if raw_path else ''
                ui_items.append({
                    'file_id': f.id,
                    'role': role,
                    'type': vtype,            # displayVideos が参照
                    'filename': f.original_filename,
                    'original_filename': f.original_filename,
                    'stored_filename': f.stored_filename,
                    'file_path': raw_path,
                    'url': stream_url,        # <video><source src= 用
                    'mime_type': f.mime_type,
                    'file_type': f.file_type,
                    'uploaded_at': utc_to_jst_isoformat(f.uploaded_at)
                })

            role_priority = {'expert': 1, 'primary': 1, 'novice': 2, 'document': 3}
            ui_items.sort(key=lambda x: (role_priority.get(x.get('role'), 99), x.get('file_id')))
            base['source_videos'] = ui_items
        except Exception as e:  # noqa: F841
            base['source_videos'] = []
        return base

class ManualSourceFile(db.Model):
    """マニュアル生成に使用されたファイル"""
    __tablename__ = 'manual_source_files'
    
    id = db.Column(db.Integer, primary_key=True)
    manual_id = db.Column(db.Integer, db.ForeignKey('manuals.id'), nullable=False)
    file_id = db.Column(db.Integer, db.ForeignKey('uploaded_files.id'), nullable=False)
    role = db.Column(db.String(50))  # expert, novice, document

class ManualTemplate(db.Model):
    """マニュアルテンプレート"""
    __tablename__ = 'manual_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    template_content = db.Column(db.Text, nullable=False)
    
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_default = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        """Convert template to dictionary"""
        import json
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'template_content': json.loads(self.template_content) if self.template_content else None,
            'company_id': self.company_id,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_default': self.is_default,
            'is_active': self.is_active
        }

class UserSession(db.Model):
    """ユーザーセッション管理"""
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_token = db.Column(db.String(255), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)


class ReferenceMaterial(db.Model):
    """
    RAG reference materials for manual generation
    """
    __tablename__ = 'reference_materials'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.BigInteger)
    
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    processing_status = db.Column(db.String(20), default='pending')
    processing_progress = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    
    extracted_metadata = db.Column(db.Text)
    
    elasticsearch_indexed = db.Column(db.Boolean, default=False)
    elasticsearch_index_name = db.Column(db.String(100))
    chunk_count = db.Column(db.Integer, default=0)
    
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'original_filename': self.original_filename,
            'stored_filename': self.stored_filename,
            'file_path': self.file_path,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'company_id': self.company_id,
            'uploaded_by': self.uploaded_by,
            'uploaded_at': utc_to_jst_isoformat(self.uploaded_at),
            'processing_status': self.processing_status,
            'processing_progress': self.processing_progress,
            'error_message': self.error_message,
            'chunk_count': self.chunk_count,
            'is_active': self.is_active
        }


class ReferenceChunk(db.Model):
    """
    Chunked text from reference materials for RAG
    """
    __tablename__ = 'reference_chunks'
    
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('reference_materials.id'), nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False)
    chunk_text = db.Column(db.Text, nullable=False)
    
    elasticsearch_doc_id = db.Column(db.String(100))
    chunk_metadata = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ActivityLog(db.Model):
    """
    User activity logs for UX analysis
    """
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    
    action_type = db.Column(db.String(50), nullable=False)
    action_detail = db.Column(db.String(255))
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.Integer)
    
    request_metadata = db.Column(db.Text)
    
    result_status = db.Column(db.String(20))
    error_message = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_user_action_date', 'user_id', 'action_type', 'created_at'),
        db.Index('idx_company_date', 'company_id', 'created_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'company_id': self.company_id,
            'action_type': self.action_type,
            'action_detail': self.action_detail,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'result_status': self.result_status,
            'created_at': utc_to_jst_isoformat(self.created_at)
        }


class ManualTranslation(db.Model):
    """
    Translated versions of manuals
    """
    __tablename__ = 'manual_translations'
    
    id = db.Column(db.Integer, primary_key=True)
    manual_id = db.Column(db.Integer, db.ForeignKey('manuals.id'), nullable=False)
    language_code = db.Column(db.String(10), nullable=False)
    
    translated_title = db.Column(db.String(255))
    translated_content = db.Column(db.Text, nullable=False)
    
    translation_engine = db.Column(db.String(50))
    translation_status = db.Column(db.String(20), default='pending')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('manual_id', 'language_code', name='unique_manual_translation'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'manual_id': self.manual_id,
            'language_code': self.language_code,
            'translated_title': self.translated_title,
            'translation_status': self.translation_status,
            'created_at': utc_to_jst_isoformat(self.created_at)
        }


class ManualPDF(db.Model):
    """
    Generated PDF files from manuals
    """
    __tablename__ = 'manual_pdfs'
    
    id = db.Column(db.Integer, primary_key=True)
    manual_id = db.Column(db.Integer, db.ForeignKey('manuals.id'), nullable=False)
    language_code = db.Column(db.String(10), default='ja')
    
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.BigInteger)
    page_count = db.Column(db.Integer)
    
    generation_config = db.Column(db.Text)
    generation_status = db.Column(db.String(20), default='pending')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'manual_id': self.manual_id,
            'language_code': self.language_code,
            'filename': self.filename,
            'file_size': self.file_size,
            'page_count': self.page_count,
            'generation_status': self.generation_status,
            'created_at': utc_to_jst_isoformat(self.created_at)
        }


class ProcessingJob(db.Model):
    """
    Async job management for heavy processing
    """
    __tablename__ = 'processing_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    job_type = db.Column(db.String(50), nullable=False)
    job_status = db.Column(db.String(20), default='pending')
    
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.Integer)
    
    job_params = db.Column(db.Text)
    
    progress = db.Column(db.Integer, default=0)
    current_step = db.Column(db.String(255))
    
    result_data = db.Column(db.Text)
    error_message = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    __table_args__ = (
        db.Index('idx_job_status_type', 'job_status', 'job_type'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'job_type': self.job_type,
            'job_status': self.job_status,
            'progress': self.progress,
            'current_step': self.current_step,
            'error_message': self.error_message,
            'created_at': utc_to_jst_isoformat(self.created_at)
        }
