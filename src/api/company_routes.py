"""
File: company_routes.py
Purpose: Company admin endpoints for user and template management
Main functionality: Company-scoped user and template CRUD operations
Dependencies: Flask, models, auth
"""

from flask import Blueprint, request, jsonify, session, g
from src.models.models import db, Company, User, ManualTemplate, ActivityLog
from src.middleware.auth import require_company_admin, log_activity
from flask_login import current_user
from datetime import datetime
from sqlalchemy import or_, func
import json

company_bp = Blueprint('company', __name__, url_prefix='/api/company')


# ============================================================================
# User Management Endpoints (Own Company Only)
# ============================================================================

@company_bp.route('/users', methods=['GET'])
@require_company_admin
@log_activity('list_company_users', 'Viewed company user list', 'user')
def list_company_users():
    """
    List users in the company admin's own company
    
    Query params:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)
        - role: Filter by role (admin/user)
        - search: Search by username or email
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    role = request.args.get('role', '').strip()
    search = request.args.get('search', '').strip()
    
    # Only query users from current company
    query = User.query.filter_by(company_id=g.company_id)
    
    # Role filter
    if role in ['admin', 'user']:
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


@company_bp.route('/users', methods=['POST'])
@require_company_admin
@log_activity('create_company_user', 'Created company user', 'user')
def create_company_user():
    """
    Create a new user in the company admin's own company
    
    Body:
        - username: Username (required)
        - email: Email
        - role: User role (admin/user, default: user)
        - password: Initial password (required)
        - language_preference: UI language (default: ja)
    """
    data = request.json if request.is_json else {}
    
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    role = data.get('role', 'user').strip()
    password = data.get('password', '').strip()
    language_preference = data.get('language_preference', 'ja').strip()
    
    # Validation
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    if not password:
        return jsonify({'error': 'Password is required'}), 400
    if role not in ['admin', 'user']:
        return jsonify({'error': 'Invalid role. Must be admin or user'}), 400
    
    # Check for duplicate username in same company
    existing = User.query.filter_by(
        username=username,
        company_id=g.company_id
    ).first()
    
    if existing:
        return jsonify({'error': 'Username already exists in this company'}), 400
    
    try:
        user = User(
            username=username,
            email=email,
            company_id=g.company_id,
            role=role,
            is_active=True,
            language_preference=language_preference
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
                'role': user.role,
                'is_active': user.is_active
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create user: {str(e)}'}), 500


@company_bp.route('/users/<int:user_id>', methods=['GET'])
@require_company_admin
@log_activity('view_company_user', 'Viewed company user details', 'user', 'user_id')
def get_company_user(user_id):
    """Get user details (must be in same company)"""
    user = User.query.filter_by(id=user_id, company_id=g.company_id).first()
    
    if not user:
        return jsonify({'error': 'User not found or not in your company'}), 404
    
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'last_login': user.last_login.isoformat() if user.last_login else None,
        'language_preference': user.language_preference
    }), 200


@company_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_company_admin
@log_activity('update_company_user', 'Updated company user', 'user', 'user_id')
def update_company_user(user_id):
    """
    Update user information (must be in same company)
    
    Body:
        - email: Email
        - role: User role (admin/user)
        - is_active: Active status
        - language_preference: UI language
    """
    user = User.query.filter_by(id=user_id, company_id=g.company_id).first()
    
    if not user:
        return jsonify({'error': 'User not found or not in your company'}), 404
    
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


@company_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_company_admin
@log_activity('delete_company_user', 'Deleted company user', 'user', 'user_id')
def delete_company_user(user_id):
    """Delete user (soft delete, must be in same company)"""
    user = User.query.filter_by(id=user_id, company_id=g.company_id).first()
    
    if not user:
        return jsonify({'error': 'User not found or not in your company'}), 404
    
    # Prevent deleting self
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
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


# ============================================================================
# Template Management Endpoints
# ============================================================================

@company_bp.route('/templates', methods=['GET'])
@require_company_admin
@log_activity('list_templates', 'Viewed template list', 'template')
def list_templates():
    """
    List templates for the company
    
    Query params:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)
        - search: Search by template name
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '').strip()
    
    # Query templates for current company
    query = ManualTemplate.query.filter_by(
        company_id=g.company_id,
        is_active=True
    )
    
    # Search filter
    if search:
        query = query.filter(ManualTemplate.name.ilike(f'%{search}%'))
    
    # Pagination
    pagination = query.order_by(ManualTemplate.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    templates = []
    for template in pagination.items:
        # Parse template_content JSON
        try:
            template_content = json.loads(template.template_content) if isinstance(template.template_content, str) else template.template_content
        except:
            template_content = {}
        
        templates.append({
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'is_default': template.is_default,
            'template_content': template_content,
            'created_at': template.created_at.isoformat() if template.created_at else None,
            'updated_at': template.updated_at.isoformat() if template.updated_at else None
        })
    
    return jsonify({
        'templates': templates,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200


@company_bp.route('/templates/<int:template_id>', methods=['GET'])
@require_company_admin
@log_activity('view_template', 'Viewed template details', 'template', 'template_id')
def get_template(template_id):
    """Get template details"""
    template = ManualTemplate.query.filter_by(
        id=template_id,
        company_id=g.company_id,
        is_active=True
    ).first()
    
    if not template:
        return jsonify({'error': 'Template not found or not in your company'}), 404
    
    # Parse template_content JSON
    try:
        template_content = json.loads(template.template_content) if isinstance(template.template_content, str) else template.template_content
    except:
        template_content = {}
    
    return jsonify({
        'id': template.id,
        'name': template.name,
        'description': template.description,
        'is_default': template.is_default,
        'template_content': template_content,
        'created_at': template.created_at.isoformat() if template.created_at else None,
        'updated_at': template.updated_at.isoformat() if template.updated_at else None
    }), 200


@company_bp.route('/templates', methods=['POST'])
@require_company_admin
@log_activity('create_template', 'Created template', 'template')
def create_template():
    """
    Create a new template
    
    Body:
        - name: Template name (required)
        - description: Template description
        - template_content: Template structure (JSON)
        - is_default: Set as default template (boolean)
    """
    data = request.json if request.is_json else {}
    
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    template_content = data.get('template_content', {})
    is_default = data.get('is_default', False)
    
    # Validation
    if not name:
        return jsonify({'error': 'Template name is required'}), 400
    
    # Check for duplicate name in same company
    existing = ManualTemplate.query.filter_by(
        name=name,
        company_id=g.company_id,
        is_active=True
    ).first()
    
    if existing:
        return jsonify({'error': 'Template with this name already exists'}), 400
    
    try:
        # Convert template_content to JSON string
        template_content_str = json.dumps(template_content) if isinstance(template_content, dict) else template_content
        
        template = ManualTemplate(
            name=name,
            description=description,
            template_content=template_content_str,
            company_id=g.company_id,
            is_default=is_default,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # If setting as default, unset other defaults
        if is_default:
            ManualTemplate.query.filter_by(
                company_id=g.company_id,
                is_default=True
            ).update({'is_default': False})
        
        db.session.add(template)
        db.session.commit()
        
        return jsonify({
            'message': 'Template created successfully',
            'template': {
                'id': template.id,
                'name': template.name,
                'description': template.description,
                'is_default': template.is_default
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create template: {str(e)}'}), 500


@company_bp.route('/templates/<int:template_id>', methods=['PUT'])
@require_company_admin
@log_activity('update_template', 'Updated template', 'template', 'template_id')
def update_template(template_id):
    """
    Update template
    
    Body:
        - name: Template name
        - description: Template description
        - template_content: Template structure (JSON)
        - is_default: Set as default template
    """
    template = ManualTemplate.query.filter_by(
        id=template_id,
        company_id=g.company_id,
        is_active=True
    ).first()
    
    if not template:
        return jsonify({'error': 'Template not found or not in your company'}), 404
    
    data = request.json if request.is_json else {}
    
    try:
        if 'name' in data:
            name = data['name'].strip()
            if name:
                # Check for duplicate name
                existing = ManualTemplate.query.filter(
                    ManualTemplate.name == name,
                    ManualTemplate.company_id == g.company_id,
                    ManualTemplate.id != template_id,
                    ManualTemplate.is_active == True
                ).first()
                if existing:
                    return jsonify({'error': 'Template name already exists'}), 400
                template.name = name
        
        if 'description' in data:
            template.description = data['description'].strip()
        
        if 'template_content' in data:
            template_content = data['template_content']
            template.template_content = json.dumps(template_content) if isinstance(template_content, dict) else template_content
        
        if 'is_default' in data:
            is_default = bool(data['is_default'])
            if is_default:
                # Unset other defaults
                ManualTemplate.query.filter_by(
                    company_id=g.company_id,
                    is_default=True
                ).update({'is_default': False})
            template.is_default = is_default
        
        template.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Template updated successfully',
            'template': {
                'id': template.id,
                'name': template.name,
                'description': template.description,
                'is_default': template.is_default
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update template: {str(e)}'}), 500


@company_bp.route('/templates/<int:template_id>', methods=['DELETE'])
@require_company_admin
@log_activity('delete_template', 'Deleted template', 'template', 'template_id')
def delete_template(template_id):
    """Delete template (soft delete)"""
    template = ManualTemplate.query.filter_by(
        id=template_id,
        company_id=g.company_id,
        is_active=True
    ).first()
    
    if not template:
        return jsonify({'error': 'Template not found or not in your company'}), 404
    
    try:
        # Soft delete
        template.is_active = False
        template.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Template deleted successfully',
            'template_id': template_id
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete template: {str(e)}'}), 500


@company_bp.route('/templates/<int:template_id>/preview', methods=['GET'])
@require_company_admin
@log_activity('preview_template', 'Previewed template', 'template', 'template_id')
def preview_template(template_id):
    """
    Preview template structure
    Returns template content with sample data filled in
    """
    template = ManualTemplate.query.filter_by(
        id=template_id,
        company_id=g.company_id,
        is_active=True
    ).first()
    
    if not template:
        return jsonify({'error': 'Template not found or not in your company'}), 404
    
    try:
        template_content = json.loads(template.template_content) if isinstance(template.template_content, str) else template.template_content
    except:
        template_content = {}
    
    # Generate sample preview data
    preview_data = {
        'template_id': template.id,
        'template_name': template.name,
        'template_structure': template_content,
        'sample_output': {
            'title': 'Sample Manual Title',
            'sections': [
                {
                    'section_name': 'Introduction',
                    'content': 'This is a sample introduction section based on the template structure.'
                },
                {
                    'section_name': 'Main Content',
                    'content': 'This is the main content section.'
                }
            ]
        }
    }
    
    return jsonify(preview_data), 200
