"""
File: admin_routes.py
Purpose: Super admin endpoints for company and user management
Main functionality: Production API for enterprise features
Dependencies: Flask, models, auth
"""

from flask import Blueprint, request, jsonify, session, g
from src.models.models import db, Company, User, ActivityLog
from src.middleware.auth import require_super_admin, log_activity
from datetime import datetime
from sqlalchemy import or_, func
import csv
from io import StringIO

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


# ============================================================================
# Company Management Endpoints
# ============================================================================

@admin_bp.route('/companies', methods=['GET'])
@require_super_admin
@log_activity('list_companies', 'Viewed company list', 'company')
def list_companies():
    """
    List all companies with pagination and search
    
    Query params:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)
        - search: Search by name or code
        - status: Filter by active/inactive
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    
    query = Company.query
    
    # Search filter
    if search:
        query = query.filter(
            or_(
                Company.name.ilike(f'%{search}%'),
                Company.company_code.ilike(f'%{search}%')
            )
        )
    
    # Status filter
    if status == 'active':
        query = query.filter(Company.is_active == True)
    elif status == 'inactive':
        query = query.filter(Company.is_active == False)
    
    # Pagination
    pagination = query.order_by(Company.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    companies = []
    for company in pagination.items:
        # Get user count
        user_count = User.query.filter_by(company_id=company.id).count()
        
        companies.append({
            'id': company.id,
            'name': company.name,
            'company_code': company.company_code,
            'is_active': company.is_active,
            'created_at': company.created_at.isoformat() if company.created_at else None,
            'updated_at': company.updated_at.isoformat() if company.updated_at else None,
            'user_count': user_count,
            'settings': company.get_settings()
        })
    
    return jsonify({
        'companies': companies,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200


@admin_bp.route('/companies', methods=['POST'])
@require_super_admin
@log_activity('create_company', 'Created new company', 'company')
def create_company():
    """
    Create a new company
    
    Body:
        - name: Company name (required)
        - company_code: Unique company code (required)
        - password: Company password (required)
        - settings: Company settings (optional)
    """
    data = request.json if request.is_json else {}
    
    name = data.get('name', '').strip()
    company_code = data.get('company_code', '').strip()
    password = data.get('password', '').strip()
    settings = data.get('settings', {})
    
    # Validation
    if not name:
        return jsonify({'error': 'Company name is required'}), 400
    if not company_code:
        return jsonify({'error': 'Company code is required'}), 400
    if not password:
        return jsonify({'error': 'Password is required'}), 400
    
    # Check for duplicates
    existing = Company.query.filter(
        or_(
            Company.name == name,
            Company.company_code == company_code
        )
    ).first()
    
    if existing:
        return jsonify({'error': 'Company name or code already exists'}), 400
    
    try:
        # Create company
        company = Company(
            name=name,
            company_code=company_code
        )
        company.set_password(password)
        
        # Set default settings
        default_settings = {
            'manual_format': 'standard',
            'ai_model': 'gemini-2.0-flash-exp',
            'max_users': 10,
            **settings
        }
        company.set_settings(default_settings)
        
        db.session.add(company)
        db.session.flush()
        
        # Create default admin user
        admin_email = data.get('admin_email', f'admin@{company_code}.com')
        if not admin_email:
            return jsonify({'error': 'Admin email is required'}), 400
            
        admin_user = User(
            username='admin',
            email=admin_email,
            company_id=company.id,
            role='admin',
            is_active=True
        )
        
        admin_password = data.get('admin_password', password)
        admin_user.set_password(admin_password)
        
        db.session.add(admin_user)
        db.session.commit()
        
        return jsonify({
            'message': 'Company created successfully',
            'company': {
                'id': company.id,
                'name': company.name,
                'company_code': company.company_code,
                'is_active': company.is_active
            },
            'admin_user': {
                'id': admin_user.id,
                'username': admin_user.username,
                'email': admin_user.email
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create company: {str(e)}'}), 500


@admin_bp.route('/companies/<int:company_id>', methods=['GET'])
@require_super_admin
@log_activity('view_company', 'Viewed company details', 'company', 'company_id')
def get_company(company_id):
    """Get company details"""
    company = Company.query.get(company_id)
    
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    # Get statistics
    user_count = User.query.filter_by(company_id=company_id).count()
    active_user_count = User.query.filter_by(company_id=company_id, is_active=True).count()
    
    from src.models.models import Manual, UploadedFile
    manual_count = Manual.query.filter_by(company_id=company_id).count()
    file_count = UploadedFile.query.filter_by(company_id=company_id).count()
    
    # Calculate storage usage
    total_storage = db.session.query(
        func.sum(UploadedFile.file_size)
    ).filter(
        UploadedFile.company_id == company_id
    ).scalar() or 0
    
    return jsonify({
        'id': company.id,
        'name': company.name,
        'company_code': company.company_code,
        'is_active': company.is_active,
        'created_at': company.created_at.isoformat() if company.created_at else None,
        'updated_at': company.updated_at.isoformat() if company.updated_at else None,
        'settings': company.get_settings(),
        'statistics': {
            'user_count': user_count,
            'active_user_count': active_user_count,
            'manual_count': manual_count,
            'file_count': file_count,
            'storage_used_bytes': total_storage
        }
    }), 200


@admin_bp.route('/companies/<int:company_id>', methods=['PUT'])
@require_super_admin
@log_activity('update_company', 'Updated company', 'company', 'company_id')
def update_company(company_id):
    """
    Update company details
    
    Body:
        - name: Company name
        - is_active: Active status
        - settings: Company settings
    """
    company = Company.query.get(company_id)
    
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    data = request.json if request.is_json else {}
    
    try:
        # Update fields
        if 'name' in data:
            name = data['name'].strip()
            if name:
                # Check for duplicate name
                existing = Company.query.filter(
                    Company.name == name,
                    Company.id != company_id
                ).first()
                if existing:
                    return jsonify({'error': 'Company name already exists'}), 400
                company.name = name
        
        if 'is_active' in data:
            company.is_active = bool(data['is_active'])
        
        if 'settings' in data:
            current_settings = company.get_settings()
            current_settings.update(data['settings'])
            company.set_settings(current_settings)
        
        company.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Company updated successfully',
            'company': {
                'id': company.id,
                'name': company.name,
                'company_code': company.company_code,
                'is_active': company.is_active,
                'settings': company.get_settings()
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update company: {str(e)}'}), 500


@admin_bp.route('/companies/<int:company_id>', methods=['DELETE'])
@require_super_admin
@log_activity('delete_company', 'Deleted company', 'company', 'company_id')
def delete_company(company_id):
    """Delete a company (soft delete by setting is_active to False)"""
    company = Company.query.get(company_id)
    
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    try:
        # Soft delete: set is_active to False
        company.is_active = False
        company.updated_at = datetime.utcnow()
        
        # Also deactivate all users
        User.query.filter_by(company_id=company_id).update({'is_active': False})
        
        db.session.commit()
        
        return jsonify({
            'message': 'Company deleted successfully',
            'company_id': company_id
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete company: {str(e)}'}), 500


# ============================================================================
# User Management Endpoints (All Companies)
# ============================================================================

@admin_bp.route('/users', methods=['GET'])
@require_super_admin
@log_activity('list_users', 'Viewed user list', 'user')
def list_users():
    """
    List all users across all companies
    
    Query params:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)
        - company_id: Filter by company
        - role: Filter by role (admin/user)
        - search: Search by username or email
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    company_id = request.args.get('company_id', type=int)
    role = request.args.get('role', '').strip()
    search = request.args.get('search', '').strip()
    
    query = User.query.join(Company)
    
    # Company filter
    if company_id:
        query = query.filter(User.company_id == company_id)
    
    # Role filter
    if role:
        query = query.filter(User.role == role)
    
    # Search filter
    if search:
        query = query.filter(
            or_(
                User.username.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )
    
    # Pagination
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    users = []
    for user in pagination.items:
        users.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'company_id': user.company_id,
            'company_name': user.company.name,
            'company_code': user.company.company_code,
            'role': user.role,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'language_preference': user.language_preference
        })
    
    return jsonify({
        'users': users,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200


@admin_bp.route('/users', methods=['POST'])
@require_super_admin
@log_activity('create_user', 'Created new user', 'user')
def create_user():
    """
    Create a new user
    
    Body:
        - username: Username (required)
        - email: Email
        - company_id: Company ID (required)
        - role: User role (admin/user)
        - password: Initial password (required)
    """
    data = request.json if request.is_json else {}
    
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    company_id = data.get('company_id')
    role = data.get('role', 'user').strip()
    password = data.get('password', '').strip()
    
    # Validation
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    if not company_id:
        return jsonify({'error': 'Company ID is required'}), 400
    if not password:
        return jsonify({'error': 'Password is required'}), 400
    if role not in ['admin', 'user']:
        return jsonify({'error': 'Invalid role'}), 400
    
    # Check company exists
    company = Company.query.get(company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    # Check for duplicate username in same company
    existing = User.query.filter_by(
        username=username,
        company_id=company_id
    ).first()
    
    if existing:
        return jsonify({'error': 'Username already exists in this company'}), 400
    
    try:
        user = User(
            username=username,
            email=email,
            company_id=company_id,
            role=role,
            is_active=True,
            language_preference=data.get('language_preference', 'ja')
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': 'User created successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'company_id': user.company_id,
                'role': user.role
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create user: {str(e)}'}), 500


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_super_admin
@log_activity('update_user', 'Updated user', 'user', 'user_id')
def update_user(user_id):
    """
    Update user details
    
    Body:
        - email: Email
        - role: User role
        - is_active: Active status
        - language_preference: UI language
    """
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.json if request.is_json else {}
    
    try:
        if 'email' in data:
            user.email = data['email'].strip()
        
        if 'role' in data:
            role = data['role'].strip()
            if role in ['admin', 'user']:
                user.role = role
        
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])
        
        if 'language_preference' in data:
            user.language_preference = data['language_preference'].strip()
        
        db.session.commit()
        
        return jsonify({
            'message': 'User updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'is_active': user.is_active,
                'language_preference': user.language_preference
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update user: {str(e)}'}), 500


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_super_admin
@log_activity('delete_user', 'Deleted user', 'user', 'user_id')
def delete_user(user_id):
    """Delete a user (soft delete by setting is_active to False)"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        # Soft delete
        user.is_active = False
        db.session.commit()
        
        return jsonify({
            'message': 'User deleted successfully',
            'user_id': user_id
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete user: {str(e)}'}), 500


@admin_bp.route('/users/<int:user_id>/proxy-login', methods=['POST'])
@require_super_admin
@log_activity('proxy_login', 'Proxy login as user', 'user', 'user_id')
def proxy_login(user_id):
    """
    Proxy login as a specific user
    Preserves super admin session for later restoration
    """
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if not user.is_active:
        return jsonify({'error': 'User account is inactive'}), 400
    
    # Save super admin session info
    super_admin_id = session.get('super_admin_id')
    session['proxy_super_admin_id'] = super_admin_id
    session['is_proxy_login'] = True
    
    # Set up user session
    from flask_login import login_user
    login_user(user, remember=False)
    session['company_id'] = user.company_id
    
    return jsonify({
        'message': f'Logged in as {user.username}',
        'redirect_url': '/',
        'user': {
            'id': user.id,
            'username': user.username,
            'company_name': user.company.name
        }
    }), 200


# ============================================================================
# Activity Log Endpoints
# ============================================================================

@admin_bp.route('/activity-logs', methods=['GET'])
@require_super_admin
def get_activity_logs():
    """
    Get activity logs with filtering
    
    Query params:
        - page: Page number
        - per_page: Items per page
        - company_id: Filter by company
        - user_id: Filter by user
        - action_type: Filter by action type
        - start_date: Filter by start date (ISO format)
        - end_date: Filter by end date (ISO format)
        - result_status: Filter by result status (success/failure)
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    company_id = request.args.get('company_id', type=int)
    user_id = request.args.get('user_id', type=int)
    action_type = request.args.get('action_type', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    result_status = request.args.get('result_status', '').strip()
    
    query = ActivityLog.query
    
    # Filters
    if company_id:
        query = query.filter(ActivityLog.company_id == company_id)
    
    if user_id:
        query = query.filter(ActivityLog.user_id == user_id)
    
    if action_type:
        query = query.filter(ActivityLog.action_type == action_type)
    
    if result_status:
        query = query.filter(ActivityLog.result_status == result_status)
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(ActivityLog.created_at >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(ActivityLog.created_at <= end_dt)
        except ValueError:
            pass
    
    # Pagination
    pagination = query.order_by(ActivityLog.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    logs = [log.to_dict() for log in pagination.items]
    
    return jsonify({
        'logs': logs,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200


@admin_bp.route('/activity-logs/export', methods=['GET'])
@require_super_admin
@log_activity('export_activity_logs', 'Exported activity logs to CSV', 'activity_log')
def export_activity_logs():
    """
    Export activity logs as CSV
    Uses same filter params as list endpoint
    """
    company_id = request.args.get('company_id', type=int)
    user_id = request.args.get('user_id', type=int)
    action_type = request.args.get('action_type', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    result_status = request.args.get('result_status', '').strip()
    limit = request.args.get('limit', 10000, type=int)  # Max 10k records
    
    query = ActivityLog.query
    
    # Apply same filters
    if company_id:
        query = query.filter(ActivityLog.company_id == company_id)
    if user_id:
        query = query.filter(ActivityLog.user_id == user_id)
    if action_type:
        query = query.filter(ActivityLog.action_type == action_type)
    if result_status:
        query = query.filter(ActivityLog.result_status == result_status)
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(ActivityLog.created_at >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(ActivityLog.created_at <= end_dt)
        except ValueError:
            pass
    
    logs = query.order_by(ActivityLog.created_at.desc()).limit(limit).all()
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'ID', 'Timestamp', 'User ID', 'Company ID', 'Action Type',
        'Action Detail', 'Resource Type', 'Resource ID', 'Result Status', 'Error Message'
    ])
    
    # Data
    for log in logs:
        writer.writerow([
            log.id,
            log.created_at.isoformat() if log.created_at else '',
            log.user_id or '',
            log.company_id or '',
            log.action_type or '',
            log.action_detail or '',
            log.resource_type or '',
            log.resource_id or '',
            log.result_status or '',
            log.error_message or ''
        ])
    
    output.seek(0)
    
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=activity_logs_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
        }
    )
