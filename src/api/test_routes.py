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
import logging
import json

logger = logging.getLogger(__name__)

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



# ============================================================
# Phase 5 Test Endpoints: Enhanced Manual Generation
# ============================================================

@test_bp.route('/phase5/create-test-template', methods=['POST'])
def create_test_template():
    """
    Create a test manual template
    
    Body (optional): {
      "name": "Test Template",
      "company_id": 1,
      "is_default": false
    }
    """
    try:
        from src.models.models import ManualTemplate, Company, User
        
        data = request.json or {}
        
        name = data.get('name', f'Test Template {datetime.now().strftime("%Y%m%d_%H%M%S")}')
        is_default = data.get('is_default', False)
        
        # Get company_id (required field)
        company_id = data.get('company_id')
        if not company_id:
            # Get first company or create test company
            company = Company.query.first()
            if not company:
                return jsonify({'error': 'No company found. Please create a company first.'}), 400
            company_id = company.id
        
        # Get user_id for created_by (required field)
        user = User.query.filter_by(company_id=company_id).first()
        if not user:
            user = User.query.first()
        if not user:
            return jsonify({'error': 'No user found. Please create a user first.'}), 400
        created_by = user.id
        
        # Sample template content
        template_content = {
            "sections": [
                {
                    "id": "overview",
                    "title": "Overview",
                    "description": "Process overview and objectives"
                },
                {
                    "id": "materials",
                    "title": "Required Materials",
                    "description": "Tools and materials needed"
                },
                {
                    "id": "safety",
                    "title": "Safety Precautions",
                    "description": "Safety guidelines and warnings"
                },
                {
                    "id": "steps",
                    "title": "Step-by-Step Instructions",
                    "description": "Detailed process steps"
                },
                {
                    "id": "quality",
                    "title": "Quality Checkpoints",
                    "description": "Quality assurance checks"
                }
            ],
            "format": "structured",
            "include_timestamps": True,
            "include_images": True
        }
        
        template = ManualTemplate(
            name=name,
            description=f"Test template created at {datetime.now().isoformat()}",
            template_content=json.dumps(template_content, ensure_ascii=False),
            company_id=company_id,
            created_by=created_by,
            is_default=is_default,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.session.add(template)
        db.session.commit()
        
        return jsonify({
            'message': 'Test template created successfully',
            'template': template.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create test template: {str(e)}")
        return jsonify({
            'error': 'Failed to create test template',
            'details': str(e)
        }), 500


@test_bp.route('/phase5/bulk-create-templates', methods=['POST'])
def bulk_create_templates():
    """
    Create multiple test templates
    
    Body: {
      "count": 3,
      "company_id": 1
    }
    """
    try:
        from src.models.models import ManualTemplate, Company, User
        
        data = request.json or {}
        count = data.get('count', 3)
        
        # Get company_id (required field)
        company_id = data.get('company_id')
        if not company_id:
            company = Company.query.first()
            if not company:
                return jsonify({'error': 'No company found. Please create a company first.'}), 400
            company_id = company.id
        
        # Get user_id for created_by (required field)
        user = User.query.filter_by(company_id=company_id).first()
        if not user:
            user = User.query.first()
        if not user:
            return jsonify({'error': 'No user found. Please create a user first.'}), 400
        created_by = user.id
        
        created_templates = []
        
        template_types = [
            ("Standard Manufacturing", "Basic manufacturing process template"),
            ("Safety Procedure", "Safety-focused template with emphasis on precautions"),
            ("Quality Assurance", "QA-focused template with checkpoints"),
            ("Maintenance", "Equipment maintenance procedure template"),
            ("Assembly", "Product assembly process template")
        ]
        
        for i in range(min(count, len(template_types))):
            name, desc = template_types[i]
            
            template = ManualTemplate(
                name=f"{name} - Test {i+1}",
                description=desc,
                template_content=json.dumps({
                    "sections": [
                        {"id": f"section_{j}", "title": f"Section {j+1}"}
                        for j in range(3)
                    ]
                }, ensure_ascii=False),
                company_id=company_id,
                created_by=created_by,
                is_default=(i == 0),
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            db.session.add(template)
            db.session.flush()
            created_templates.append(template.to_dict())
        
        db.session.commit()
        
        return jsonify({
            'message': f'Created {len(created_templates)} test templates',
            'templates': created_templates
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to bulk create templates: {str(e)}")
        return jsonify({
            'error': 'Failed to bulk create templates',
            'details': str(e)
        }), 500


@test_bp.route('/phase5/validate-template', methods=['POST'])
def validate_template():
    """
    Validate template JSON structure
    
    Body: {
      "template_content": {...}
    }
    """
    try:
        data = request.json
        template_content = data.get('template_content')
        
        if not template_content:
            return jsonify({
                'valid': False,
                'error': 'template_content is required'
            }), 400
        
        # Basic validation
        required_keys = ['sections']
        validation_errors = []
        
        for key in required_keys:
            if key not in template_content:
                validation_errors.append(f"Missing required key: {key}")
        
        if 'sections' in template_content:
            if not isinstance(template_content['sections'], list):
                validation_errors.append("sections must be an array")
            else:
                for idx, section in enumerate(template_content['sections']):
                    if 'id' not in section:
                        validation_errors.append(f"Section {idx} missing 'id' field")
                    if 'title' not in section:
                        validation_errors.append(f"Section {idx} missing 'title' field")
        
        if validation_errors:
            return jsonify({
                'valid': False,
                'errors': validation_errors
            }), 400
        
        return jsonify({
            'valid': True,
            'message': 'Template structure is valid',
            'section_count': len(template_content.get('sections', []))
        }), 200
        
    except Exception as e:
        return jsonify({
            'valid': False,
            'error': str(e)
        }), 400


@test_bp.route('/phase5/test-rag-search', methods=['POST'])
def test_rag_search():
    """
    Test RAG semantic search
    
    Body: {
      "query": "safety procedures",
      "company_id": 1,
      "max_results": 5
    }
    """
    try:
        from src.services.elasticsearch_service import elasticsearch_service
        from src.services.rag_processor import RAGProcessor
        
        data = request.json or {}
        query = data.get('query', 'test search')
        company_id = data.get('company_id', 1)
        max_results = data.get('max_results', 5)
        
        # Generate query embedding using RAG processor
        rag_processor = RAGProcessor()
        query_embedding = rag_processor.generate_embedding(query)
        
        # Perform hybrid search
        results = elasticsearch_service.hybrid_search(
            query_text=query,
            query_embedding=query_embedding,
            company_id=company_id,
            top_k=max_results
        )
        
        return jsonify({
            'query': query,
            'company_id': company_id,
            'results_count': len(results),
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"RAG search test failed: {str(e)}")
        return jsonify({
            'error': 'RAG search failed',
            'details': str(e)
        }), 500


@test_bp.route('/phase5/elasticsearch-status', methods=['GET'])
def elasticsearch_status():
    """Check ElasticSearch connection and index status"""
    try:
        from src.services.elasticsearch_service import elasticsearch_service
        
        health = elasticsearch_service.health_check()
        
        # Handle both dict and bool return types
        if isinstance(health, bool):
            return jsonify({
                'elasticsearch_available': health,
                'status': 'healthy' if health else 'unavailable'
            }), 200
        
        return jsonify({
            'elasticsearch_available': health.get('status') == 'healthy' if isinstance(health, dict) else bool(health),
            'elasticsearch': health if isinstance(health, dict) else {'status': 'healthy' if health else 'unavailable'}
        }), 200
        
    except Exception as e:
        return jsonify({
            'elasticsearch_available': False,
            'error': str(e)
        }), 500
