"""
File: test_routes.py
Purpose: Test endpoints for development and verification
Main functionality: API testing and data generation
Dependencies: Flask, models, auth
"""

from flask import Blueprint, request, jsonify, session
from src.models.models import db, SuperAdmin, Company, User, ActivityLog
from src.middleware.auth import require_super_admin
from werkzeug.security import generate_password_hash
from datetime import datetime
from sqlalchemy import inspect

test_bp = Blueprint('test', __name__, url_prefix='/api/test')


@test_bp.route('/create-super-admin', methods=['POST'])
def create_super_admin():
    """Create initial super admin account"""
    data = request.json if request.is_json else {}
    
    username = data.get('username', 'superadmin')
    email = data.get('email', 'admin@kantan-ai.net')
    password = data.get('password', 'admin123')
    
    existing = SuperAdmin.query.filter_by(email=email).first()
    if existing:
        return jsonify({'error': 'Super admin already exists', 'super_admin_id': existing.id}), 400
    
    super_admin = SuperAdmin(
        username=username,
        email=email,
        permission_level='full'
    )
    super_admin.set_password(password)
    
    db.session.add(super_admin)
    db.session.commit()
    
    return jsonify({
        'message': 'Super admin created successfully',
        'super_admin': {
            'id': super_admin.id,
            'username': super_admin.username,
            'email': super_admin.email
        }
    }), 201


@test_bp.route('/login-super-admin', methods=['POST'])
def login_super_admin():
    """Login as super admin for testing"""
    data = request.json if request.is_json else {}
    
    email = data.get('email', 'admin@kantan-ai.net')
    password = data.get('password', 'admin123')
    
    super_admin = SuperAdmin.query.filter_by(email=email).first()
    if not super_admin or not super_admin.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    session['is_super_admin'] = True
    session['super_admin_id'] = super_admin.id
    
    super_admin.last_login = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Super admin logged in successfully',
        'super_admin': {
            'id': super_admin.id,
            'username': super_admin.username,
            'email': super_admin.email
        }
    }), 200


@test_bp.route('/check-permissions', methods=['GET'])
def check_permissions():
    """Verify authentication and permissions"""
    auth_info = {
        'is_authenticated': False,
        'is_super_admin': False,
        'company_id': None,
        'user_info': None
    }
    
    if session.get('is_super_admin'):
        auth_info['is_super_admin'] = True
        super_admin_id = session.get('super_admin_id')
        if super_admin_id:
            super_admin = SuperAdmin.query.get(super_admin_id)
            if super_admin:
                auth_info['user_info'] = {
                    'id': super_admin.id,
                    'username': super_admin.username,
                    'email': super_admin.email,
                    'type': 'super_admin'
                }
    
    elif session.get('company_id'):
        auth_info['is_authenticated'] = True
        auth_info['company_id'] = session.get('company_id')
        
        from flask_login import current_user
        if current_user.is_authenticated:
            auth_info['user_info'] = {
                'id': current_user.id,
                'username': current_user.username,
                'role': current_user.role,
                'type': 'company_user'
            }
    
    return jsonify(auth_info), 200


@test_bp.route('/database-status', methods=['GET'])
def database_status():
    """Check database tables and sample data"""
    try:
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        tables_info = {
            'total_tables': len(tables),
            'tables': tables,
            'counts': {}
        }
        
        model_map = {
            'super_admins': SuperAdmin,
            'companies': Company,
            'users': User,
            'activity_logs': ActivityLog
        }
        
        for table_name, model in model_map.items():
            if table_name in tables:
                count = model.query.count()
                tables_info['counts'][table_name] = count
        
        return jsonify(tables_info), 200
    
    except Exception as e:
        return jsonify({
            'error': 'Database error',
            'message': str(e)
        }), 500


@test_bp.route('/create-test-company', methods=['POST'])
@require_super_admin
def create_test_company():
    """Create a test company for development"""
    data = request.json if request.is_json else {}
    
    company_code = data.get('company_code', 'test-company')
    company_name = data.get('name', 'Test Company')
    password = data.get('password', 'test123')
    
    existing = Company.query.filter_by(company_code=company_code).first()
    if existing:
        return jsonify({'error': 'Company already exists', 'company_id': existing.id}), 400
    
    company = Company(
        name=company_name,
        company_code=company_code
    )
    company.set_password(password)
    
    db.session.add(company)
    db.session.flush()
    
    admin_user = User(
        username='admin',
        email=f'admin@{company_code}.com',
        company_id=company.id,
        role='admin'
    )
    admin_user.set_password(password)
    
    db.session.add(admin_user)
    db.session.commit()
    
    return jsonify({
        'message': 'Test company created successfully',
        'company': {
            'id': company.id,
            'name': company.name,
            'code': company.company_code
        },
        'admin_user': {
            'id': admin_user.id,
            'username': admin_user.username,
            'email': admin_user.email
        }
    }), 201


@test_bp.route('/logout', methods=['POST'])
def test_logout():
    """Logout from test session"""
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200


@test_bp.route('/activity-logs', methods=['GET'])
@require_super_admin
def get_activity_logs():
    """Get recent activity logs for testing"""
    limit = request.args.get('limit', 20, type=int)
    
    logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(limit).all()
    
    return jsonify({
        'total': ActivityLog.query.count(),
        'logs': [log.to_dict() for log in logs]
    }), 200
