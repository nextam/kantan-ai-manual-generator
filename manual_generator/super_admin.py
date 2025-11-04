"""
スーパー管理者システム
企業テナント管理、システム全体の監視・管理機能
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from functools import wraps

from flask import session, request, redirect, url_for, current_app, g, jsonify
from sqlalchemy import func

from models import db, SuperAdmin, Company, User, UploadedFile, Manual

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
    iso_str = jst_dt.strftime('%Y-%m-%dT%H:%M:%S.%f+09:00')
    return iso_str

class SuperAdminManager:
    """スーパー管理者管理システム"""
    
    @staticmethod
    def create_super_admin(username: str, email: str, password: str, 
                          permission_level: str = 'full') -> Dict[str, Any]:
        """スーパー管理者作成"""
        # 重複チェック
        existing = SuperAdmin.query.filter(
            (SuperAdmin.username == username) | (SuperAdmin.email == email)
        ).first()
        
        if existing:
            return {
                'success': False,
                'error': 'ユーザー名またはメールアドレスが既に存在します'
            }
        
        try:
            super_admin = SuperAdmin(
                username=username,
                email=email,
                permission_level=permission_level
            )
            super_admin.set_password(password)
            
            db.session.add(super_admin)
            db.session.commit()
            
            return {
                'success': True,
                'super_admin': super_admin
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': f'スーパー管理者作成中にエラーが発生しました: {str(e)}'
            }
    
    @staticmethod
    def authenticate_super_admin(username: str, password: str) -> Optional[SuperAdmin]:
        """スーパー管理者認証"""
        super_admin = SuperAdmin.query.filter_by(
            username=username, 
            is_active=True
        ).first()
        
        if super_admin and super_admin.check_password(password):
            return super_admin
        return None
    
    @staticmethod
    def get_system_overview() -> Dict[str, Any]:
        """システム全体の概要取得"""
        try:
            # 基本統計
            stats = {
                'companies_total': Company.query.count(),
                'companies_active': Company.query.filter_by(is_active=True).count(),
                'users_total': User.query.count(),
                'users_active': User.query.filter_by(is_active=True).count(),
                'files_total': UploadedFile.query.count(),
                'manuals_total': Manual.query.count(),
            }
            
            # 今日の活動
            today = datetime.now(JST).date()
            stats['companies_created_today'] = Company.query.filter(
                func.date(Company.created_at) == today
            ).count()
            stats['files_uploaded_today'] = UploadedFile.query.filter(
                func.date(UploadedFile.uploaded_at) == today
            ).count()
            stats['manuals_created_today'] = Manual.query.filter(
                func.date(Manual.created_at) == today
            ).count()
            
            # 企業別データ
            companies_data = []
            companies = Company.query.all()
            
            for company in companies:
                company_stats = {
                    'id': company.id,
                    'name': company.name,
                    'code': company.company_code,
                    'created_at': datetime_to_jst_isoformat(company.created_at),
                    'is_active': company.is_active,
                    'storage_type': company.storage_type,
                    'users_count': User.query.filter_by(company_id=company.id).count(),
                    'files_count': UploadedFile.query.filter_by(company_id=company.id).count(),
                    'manuals_count': Manual.query.filter_by(company_id=company.id).count(),
                }
                
                # 最新活動
                last_manual = Manual.query.filter_by(company_id=company.id).order_by(
                    Manual.created_at.desc()
                ).first()
                if last_manual:
                    company_stats['last_activity'] = last_manual.created_at.isoformat()
                
                companies_data.append(company_stats)
            
            return {
                'success': True,
                'stats': stats,
                'companies': companies_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'システム概要取得エラー: {str(e)}'
            }
    
    @staticmethod
    def get_company_details(company_id: int) -> Dict[str, Any]:
        """企業詳細情報取得"""
        try:
            company = Company.query.get(company_id)
            if not company:
                return {
                    'success': False,
                    'error': '企業が見つかりません'
                }
            
            # 企業基本情報
            company_data = {
                'id': company.id,
                'name': company.name,
                'code': company.company_code,
                'created_at': company.created_at.isoformat() if company.created_at else None,
                'updated_at': company.updated_at.isoformat() if company.updated_at else None,
                'is_active': company.is_active,
                'storage_type': company.storage_type,
                'settings': company.get_settings(),
                'storage_config': company.get_storage_config()
            }
            
            # ユーザー一覧
            users = User.query.filter_by(company_id=company_id).all()
            users_data = []
            for user in users:
                user_data = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'is_active': user.is_active,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'last_login': user.last_login.isoformat() if user.last_login else None
                }
                users_data.append(user_data)
            
            # 最近のファイル
            recent_files = UploadedFile.query.filter_by(
                company_id=company_id
            ).order_by(UploadedFile.uploaded_at.desc()).limit(10).all()
            
            files_data = []
            for file in recent_files:
                file_data = {
                    'id': file.id,
                    'original_filename': file.original_filename,
                    'file_type': file.file_type,
                    'file_size': file.file_size,
                    'uploaded_at': file.uploaded_at.isoformat() if file.uploaded_at else None,
                    'uploaded_by': file.uploaded_by
                }
                files_data.append(file_data)
            
            # 最近のマニュアル
            recent_manuals = Manual.query.filter_by(
                company_id=company_id
            ).order_by(Manual.created_at.desc()).limit(10).all()
            
            manuals_data = []
            for manual in recent_manuals:
                manual_data = {
                    'id': manual.id,
                    'title': manual.title,
                    'manual_type': manual.manual_type,
                    'created_at': manual.created_at.isoformat() if manual.created_at else None,
                    'created_by': manual.created_by
                }
                manuals_data.append(manual_data)
            
            return {
                'success': True,
                'company': company_data,
                'users': users_data,
                'recent_files': files_data,
                'recent_manuals': manuals_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'企業詳細取得エラー: {str(e)}'
            }
    
    @staticmethod
    def update_company_status(company_id: int, is_active: bool) -> Dict[str, Any]:
        """企業の有効/無効切り替え"""
        try:
            company = Company.query.get(company_id)
            if not company:
                return {
                    'success': False,
                    'error': '企業が見つかりません'
                }
            
            company.is_active = is_active
            company.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            return {
                'success': True,
                'message': f'企業を{"有効" if is_active else "無効"}にしました'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': f'企業ステータス更新エラー: {str(e)}'
            }
    
    @staticmethod
    def delete_company(company_id: int) -> Dict[str, Any]:
        """企業削除（関連データも全て削除）"""
        try:
            company = Company.query.get(company_id)
            if not company:
                return {
                    'success': False,
                    'error': '企業が見つかりません'
                }
            
            # カスケード削除でユーザー、ファイル、マニュアルも削除される
            db.session.delete(company)
            db.session.commit()
            
            return {
                'success': True,
                'message': f'企業 {company.name} とその関連データを削除しました'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': f'企業削除エラー: {str(e)}'
            }
    
    @staticmethod
    def get_system_logs(limit: int = 100) -> Dict[str, Any]:
        """システムログ取得（最近の活動）"""
        try:
            # 最近の企業作成
            recent_companies = Company.query.order_by(
                Company.created_at.desc()
            ).limit(limit // 4).all()
            
            # 最近のユーザー作成
            recent_users = User.query.order_by(
                User.created_at.desc()
            ).limit(limit // 4).all()
            
            # 最近のファイルアップロード
            recent_files = UploadedFile.query.order_by(
                UploadedFile.uploaded_at.desc()
            ).limit(limit // 4).all()
            
            # 最近のマニュアル生成
            recent_manuals = Manual.query.order_by(
                Manual.created_at.desc()
            ).limit(limit // 4).all()
            
            logs = []
            
            # 企業ログ
            for company in recent_companies:
                logs.append({
                    'type': 'company_created',
                    'timestamp': company.created_at.isoformat() if company.created_at else None,
                    'message': f'新規企業作成: {company.name} ({company.company_code})',
                    'company_id': company.id
                })
            
            # ユーザーログ
            for user in recent_users:
                logs.append({
                    'type': 'user_created',
                    'timestamp': user.created_at.isoformat() if user.created_at else None,
                    'message': f'新規ユーザー作成: {user.username} (企業ID: {user.company_id})',
                    'company_id': user.company_id
                })
            
            # ファイルログ
            for file in recent_files:
                logs.append({
                    'type': 'file_uploaded',
                    'timestamp': file.uploaded_at.isoformat() if file.uploaded_at else None,
                    'message': f'ファイルアップロード: {file.original_filename} (企業ID: {file.company_id})',
                    'company_id': file.company_id
                })
            
            # マニュアルログ
            for manual in recent_manuals:
                logs.append({
                    'type': 'manual_created',
                    'timestamp': manual.created_at.isoformat() if manual.created_at else None,
                    'message': f'マニュアル生成: {manual.title} (企業ID: {manual.company_id})',
                    'company_id': manual.company_id
                })
            
            # 時系列でソート
            logs.sort(key=lambda x: x['timestamp'] or '', reverse=True)
            
            return {
                'success': True,
                'logs': logs[:limit]
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'ログ取得エラー: {str(e)}'
            }

def require_super_admin(f):
    """スーパー管理者権限が必要なエンドポイントのデコレーター"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # セッションにスーパー管理者情報があるかチェック
        if 'super_admin_id' not in session:
            return jsonify({'error': 'スーパー管理者ログインが必要です'}), 401
        
        super_admin = SuperAdmin.query.get(session['super_admin_id'])
        if not super_admin or not super_admin.is_active:
            session.pop('super_admin_id', None)
            return jsonify({'error': 'スーパー管理者ログインが必要です'}), 401
        
        g.current_super_admin = super_admin
        return f(*args, **kwargs)
    return decorated_function

def require_super_admin_permission(permission: str = 'full'):
    """特定権限が必要なエンドポイントのデコレーター"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_super_admin'):
                return jsonify({'error': 'スーパー管理者ログインが必要です'}), 401
            
            if g.current_super_admin.permission_level != permission and permission != 'readonly':
                return jsonify({'error': '権限が不足しています'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
