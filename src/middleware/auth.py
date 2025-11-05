"""
認証・セッション管理システム
企業テナント単位でのログイン・セッション管理
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps

from flask import session, request, redirect, url_for, current_app, g, render_template, jsonify
from flask_login import LoginManager, current_user, login_user, logout_user
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import func
import secrets

from src.models.models import db, Company, User, UserSession

class AuthManager:
    """認証管理システム"""
    
    def __init__(self, app=None):
        self.app = app
        self.login_manager = LoginManager()
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Flaskアプリの初期化"""
        self.app = app
        self.login_manager.init_app(app)
        self.login_manager.login_view = 'auth.login'
        self.login_manager.login_message = 'ログインが必要です'
        self.login_manager.user_loader(self.load_user)
    
    def load_user(self, user_id):
        """ユーザーローダー"""
        return User.query.get(int(user_id))
    
    def authenticate_company(self, company_code: str, password: str) -> Optional[Company]:
        """企業認証"""
        company = Company.query.filter_by(
            company_code=company_code, 
            is_active=True
        ).first()
        
        if company and company.check_password(password):
            return company
        return None
    
    def create_user_session(self, user: User) -> UserSession:
        """ユーザーセッション作成"""
        # 既存セッションの無効化
        UserSession.query.filter_by(user_id=user.id).delete()
        
        # 新しいセッション作成
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        user_session = UserSession(
            user_id=user.id,
            session_token=session_token,
            expires_at=expires_at,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.add(user_session)
        db.session.commit()
        
        return user_session
    
    def get_current_company(self) -> Optional[Company]:
        """現在の企業を取得"""
        if current_user.is_authenticated:
            return current_user.company
        return None
    
    def require_company_auth(self, f):
        """企業認証が必要なエンドポイントのデコレーター"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            company = self.get_current_company()
            if not company or not company.is_active:
                logout_user()
                return redirect(url_for('auth.login'))
            
            g.current_company = company
            return f(*args, **kwargs)
        return decorated_function

def setup_company_data_isolation():
    """企業データ分離の設定"""
    def before_request():
        """リクエスト前処理で企業フィルタを設定"""
        if current_user.is_authenticated:
            g.current_company_id = current_user.company_id
        else:
            g.current_company_id = None
    
    return before_request

class CompanyManager:
    """企業管理システム"""
    
    @staticmethod
    def create_company(name: str, company_code: str, password: str, 
                      admin_username: str = 'admin', 
                      admin_email: str = None) -> Dict[str, Any]:
        """新規企業作成"""
        # 重複チェック
        existing = Company.query.filter(
            (Company.name == name) | (Company.company_code == company_code)
        ).first()
        
        if existing:
            return {
                'success': False,
                'error': '企業名または企業コードが既に存在します'
            }
        
        try:
            # 企業作成
            company = Company(
                name=name,
                company_code=company_code
            )
            company.set_password(password)
            
            # デフォルト設定
            default_settings = {
                'manual_format': 'standard',
                'ai_model': 'gemini-2.5-pro',
                'storage_quota_gb': 10,
                'max_users': 5
            }
            company.set_settings(default_settings)
            
            # ローカルストレージ設定
            storage_config = {
                'base_path': f'uploads/company_{company_code}'
            }
            company.set_storage_config(storage_config)
            
            db.session.add(company)
            db.session.flush()  # IDを取得するため
            
            # 管理者ユーザー作成
            admin_user = User(
                username=admin_username,
                email=admin_email,
                company_id=company.id,
                role='admin'
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            return {
                'success': True,
                'company': company,
                'admin_user': admin_user
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': f'企業作成中にエラーが発生しました: {str(e)}'
            }
    
    @staticmethod
    def get_company_stats(company_id: int) -> Dict[str, Any]:
        """企業統計情報取得"""
        from src.models.models import UploadedFile, Manual
        
        company = Company.query.get(company_id)
        if not company:
            return {}
        
        # Calculate storage usage for this company
        total_storage_bytes = db.session.query(
            func.sum(UploadedFile.file_size)
        ).filter(
            UploadedFile.company_id == company_id
        ).scalar() or 0
        storage_used_mb = round(total_storage_bytes / (1024 ** 2), 2)
        
        stats = {
            'users_count': User.query.filter_by(company_id=company_id, is_active=True).count(),
            'files_count': UploadedFile.query.filter_by(company_id=company_id).count(),
            'manuals_count': Manual.query.filter_by(company_id=company_id).count(),
            'storage_used_mb': storage_used_mb,
            'last_activity': None
        }
        
        # 最新活動日時
        last_manual = Manual.query.filter_by(company_id=company_id).order_by(
            Manual.created_at.desc()
        ).first()
        if last_manual:
            stats['last_activity'] = last_manual.created_at
        
        return stats
    
    @staticmethod
    def update_company_settings(company_id: int, settings: Dict[str, Any]) -> bool:
        """企業設定更新"""
        try:
            company = Company.query.get(company_id)
            if not company:
                return False
            
            current_settings = company.get_settings()
            current_settings.update(settings)
            company.set_settings(current_settings)
            
            company.updated_at = datetime.utcnow()
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating company settings: {e}")
            return False
    
    @staticmethod
    def update_storage_config(company_id: int, storage_type: str, 
                            storage_config: Dict[str, Any]) -> bool:
        """ストレージ設定更新"""
        try:
            company = Company.query.get(company_id)
            if not company:
                return False
            
            company.storage_type = storage_type
            company.set_storage_config(storage_config)
            company.updated_at = datetime.utcnow()
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating storage config: {e}")
            return False

def require_role(role: str):
    """特定のロールが必要なエンドポイントのデコレーター"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if current_user.role != role and current_user.role != 'admin':
                return {'error': 'アクセス権限がありません'}, 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def init_auth_routes(app):
    """認証ルートの初期化"""
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """企業ログインページ"""
        if request.method == 'POST':
            company_code = request.form.get('company_code', '')
            password = request.form.get('password', '')
            username = request.form.get('username', 'admin')
            
            if not company_code or not password:
                return render_template('login.html', 
                                     error='企業コードとパスワードを入力してください')
            
            # 企業認証（グローバルのauth_managerを使用）
            auth_manager = getattr(current_app, 'auth_manager', None)
            if not auth_manager:
                # フォールバック: 基本的な認証処理
                company = Company.query.filter_by(
                    company_code=company_code, 
                    is_active=True
                ).first()
                if not (company and company.check_password(password)):
                    return render_template('login.html', 
                                         error='企業コードまたはパスワードが正しくありません')
            else:
                company = auth_manager.authenticate_company(company_code, password)
            
            if not company:
                return render_template('login.html', 
                                     error='企業コードまたはパスワードが正しくありません')
            
            # ユーザー検索
            user = User.query.filter_by(
                username=username,
                company_id=company.id,
                is_active=True
            ).first()
            
            if not user:
                return render_template('login.html', 
                                     error='ユーザーが見つかりません')
            
            # ログイン処理
            login_user(user, remember=True)
            
            # セッション作成（auth_managerがある場合のみ）
            if auth_manager:
                user_session = auth_manager.create_user_session(user)
                session['session_token'] = user_session.session_token
            
            session['company_id'] = company.id
            
            # 最終ログイン日時更新
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # メインページにリダイレクト
            return redirect(url_for('manual_generator'))
        
        return render_template('login.html')
    
    @app.route('/auth/login', methods=['GET', 'POST'])
    def auth_login():
        """API用ログインエンドポイント"""
        if request.method == 'POST':
            data = request.get_json() if request.is_json else request.form
            company_code = data.get('company_code')
            password = data.get('password')
            username = data.get('username', 'admin')
            
            # 企業認証（グローバルのauth_managerを使用）
            auth_manager = getattr(current_app, 'auth_manager', None)
            if not auth_manager:
                # フォールバック: 基本的な認証処理
                company = Company.query.filter_by(
                    company_code=company_code, 
                    is_active=True
                ).first()
                if not (company and company.check_password(password)):
                    return {'error': '企業コードまたはパスワードが正しくありません'}, 401
            else:
                company = auth_manager.authenticate_company(company_code, password)
            
            if not company:
                return {'error': '企業コードまたはパスワードが正しくありません'}, 401
            
            # ユーザー検索
            user = User.query.filter_by(
                username=username,
                company_id=company.id,
                is_active=True
            ).first()
            
            if not user:
                return {'error': 'ユーザーが見つかりません'}, 401
            
            # ログイン処理
            login_user(user, remember=True)
            
            # セッション作成（auth_managerがある場合のみ）
            if auth_manager:
                user_session = auth_manager.create_user_session(user)
                session['session_token'] = user_session.session_token
            
            session['company_id'] = company.id
            
            # 最終ログイン日時更新
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            return {
                'success': True,
                'company': company.name,
                'user': user.username,
                'role': user.role
            }
        
        return {'message': 'ログインページ'}
    
    @app.route('/auth/logout', methods=['POST'])
    def logout():
        """ログアウト"""
        try:
            if current_user.is_authenticated:
                # セッション削除
                session_token = session.get('session_token')
                if session_token:
                    UserSession.query.filter_by(session_token=session_token).delete()
                    db.session.commit()
                
                # Flask-Loginのログアウト
                logout_user()
            
            # セッション完全クリア
            session.clear()
            
            # レスポンスを作成
            response = jsonify({'success': True})
            
            # セッションクッキーを明示的に削除
            response.set_cookie('session', '', expires=0)
            response.set_cookie('remember_token', '', expires=0)
            
            # キャッシュを無効化
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            
            return response
            
        except Exception as e:
            print(f"ログアウトエラー: {e}")
            # エラーでもセッションはクリア
            session.clear()
            response = jsonify({'success': True})
            response.set_cookie('session', '', expires=0)
            return response
    
    @app.route('/auth/status')
    def auth_status():
        """認証ステータス確認"""
        try:
            # セッションの有効性も確認
            if (current_user.is_authenticated and 
                hasattr(current_user, 'company') and 
                current_user.company is not None):
                
                company = current_user.company
                
                # セッショントークンが有効か確認
                session_token = session.get('session_token')
                if session_token:
                    valid_session = UserSession.query.filter_by(
                        session_token=session_token,
                        user_id=current_user.id
                    ).first()
                    
                    if not valid_session or valid_session.expires_at < datetime.utcnow():
                        # セッションが無効な場合
                        session.clear()
                        return jsonify({'authenticated': False})
                
                return jsonify({
                    'authenticated': True,
                    'company': {
                        'id': company.id,
                        'name': company.name,
                        'code': company.company_code
                    },
                    'user': {
                        'id': current_user.id,
                        'username': current_user.username,
                        'email': getattr(current_user, 'email', ''),
                        'role': current_user.role
                    }
                })
            
            # 認証されていない場合
            session.clear()
            return jsonify({'authenticated': False})
            
        except Exception as e:
            print(f"認証ステータス確認エラー: {e}")
            session.clear()
            return jsonify({'authenticated': False})
