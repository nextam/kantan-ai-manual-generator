"""
File: test_routes.py
Purpose: Test endpoints for development and verification
Main functionality: API testing and data generation
Dependencies: Flask, models, auth
"""

from flask import Blueprint, request, jsonify, session
from src.models.models import db, Company, User, ActivityLog
from src.middleware.auth import require_super_admin
from werkzeug.security import generate_password_hash
from datetime import datetime
from sqlalchemy import inspect
import logging
import json
import os

logger = logging.getLogger(__name__)

test_bp = Blueprint('test', __name__, url_prefix='/api/test')


@test_bp.route('/create-super-admin', methods=['POST'])
def create_super_admin():
    """Create initial super admin account (User with role='super_admin')"""
    data = request.json if request.is_json else {}
    
    username = data.get('username', 'support')
    email = data.get('email', 'support@career-survival.com')
    password = data.get('password', '0000')
    
    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({'error': 'User already exists', 'user_id': existing.id}), 400
    
    # Find or create career-survival company
    company = Company.query.filter_by(company_code='career-survival').first()
    if not company:
        company = Company(
            name='Career Survival Inc.',
            company_code='career-survival'
        )
        company.set_password('0000')
        db.session.add(company)
        db.session.flush()
    
    super_admin_user = User(
        username=username,
        email=email,
        company_id=company.id,
        role='super_admin'
    )
    super_admin_user.set_password(password)
    
    db.session.add(super_admin_user)
    db.session.commit()
    
    return jsonify({
        'message': 'Super admin created successfully',
        'super_admin': {
            'id': super_admin_user.id,
            'username': super_admin_user.username,
            'email': super_admin_user.email,
            'role': super_admin_user.role
        }
    }), 201


@test_bp.route('/login-super-admin', methods=['POST'])
def login_super_admin():
    """Login as super admin for testing"""
    data = request.json if request.is_json else {}
    
    email = data.get('email', 'support@career-survival.com')
    password = data.get('password', '0000')
    
    super_admin = User.query.filter_by(email=email, role='super_admin').first()
    if not super_admin or not super_admin.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    session['is_super_admin'] = True
    session['super_admin_id'] = super_admin.id
    session['super_admin_username'] = super_admin.username
    session['user_role'] = super_admin.role
    session['company_id'] = super_admin.company_id
    
    super_admin.last_login = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Super admin logged in successfully',
        'super_admin': {
            'id': super_admin.id,
            'username': super_admin.username,
            'email': super_admin.email,
            'role': super_admin.role
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
    
    from flask_login import current_user
    
    if current_user.is_authenticated:
        auth_info['is_authenticated'] = True
        auth_info['company_id'] = current_user.company_id
        
        if current_user.is_super_admin():
            auth_info['is_super_admin'] = True
            auth_info['user_info'] = {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'role': current_user.role,
                'type': 'super_admin'
            }
        else:
            auth_info['user_info'] = {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
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
            'companies': Company,
            'users': User,
            'activity_logs': ActivityLog
        }
        
        for table_name, model in model_map.items():
            if table_name in tables:
                count = model.query.count()
                tables_info['counts'][table_name] = count
        
        # Count super admins separately (from users table)
        if 'users' in tables:
            super_admin_count = User.query.filter_by(role='super_admin').count()
            tables_info['counts']['super_admins'] = super_admin_count
        
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


# ===== Phase 6-8 Test Endpoints =====

@test_bp.route('/pdf/generate-sample', methods=['POST'])
def test_generate_sample_pdf():
    """
    Test PDF generation with sample manual
    
    POST /api/test/pdf/generate-sample
    Body: {
        "manual_id": 1,
        "language_code": "ja"
    }
    """
    try:
        data = request.get_json() or {}
        manual_id = data.get('manual_id')
        language_code = data.get('language_code', 'ja')
        
        if not manual_id:
            # Get first manual from database
            from src.models.models import Manual
            manual = Manual.query.first()
            if not manual:
                return {'error': 'No manuals found in database. Please create a manual first.'}, 404
            manual_id = manual.id
        
        # Trigger PDF generation
        from src.api.pdf_routes import generate_pdf
        from flask import session as flask_session
        
        # Simulate authentication
        manual = Manual.query.get(manual_id)
        if manual:
            with flask_session as sess:
                sess['company_id'] = manual.company_id
                sess['user_id'] = manual.created_by
                
                # Generate PDF
                result = generate_pdf(manual_id)
                
                return result
        else:
            return {'error': f'Manual {manual_id} not found'}, 404
            
    except Exception as e:
        logger.error(f"Test PDF generation failed: {str(e)}")
        return {'error': str(e)}, 500


@test_bp.route('/translation/test-single', methods=['POST'])
def test_translation_single():
    """
    Test single language translation
    
    POST /api/test/translation/test-single
    Body: {
        "manual_id": 1,
        "language_code": "en"
    }
    """
    try:
        data = request.get_json() or {}
        manual_id = data.get('manual_id')
        language_code = data.get('language_code', 'en')
        
        if not manual_id:
            from src.models.models import Manual
            manual = Manual.query.first()
            if not manual:
                return {'error': 'No manuals found in database'}, 404
            manual_id = manual.id
        
        # Test translation
        from src.services.translation_service import translation_service
        from src.models.models import Manual
        
        manual = Manual.query.get(manual_id)
        if not manual:
            return {'error': f'Manual {manual_id} not found'}, 404
        
        result = translation_service.translate_manual(
            title=manual.title,
            content=manual.content[:500],  # Test with first 500 chars
            source_lang='ja',
            target_lang=language_code,
            preserve_formatting=True
        )
        
        return {
            'message': 'Translation test successful',
            'manual_id': manual_id,
            'language_code': language_code,
            'original_title': manual.title,
            'translated_title': result['translated_title'],
            'content_length': len(result['translated_content'])
        }, 200
        
    except Exception as e:
        logger.error(f"Translation test failed: {str(e)}")
        return {'error': str(e)}, 500


@test_bp.route('/translation/test-batch', methods=['POST'])
def test_translation_batch():
    """
    Test batch translation to multiple languages
    
    POST /api/test/translation/test-batch
    Body: {
        "manual_id": 1,
        "language_codes": ["en", "zh", "ko"]
    }
    """
    try:
        data = request.get_json() or {}
        manual_id = data.get('manual_id')
        language_codes = data.get('language_codes', ['en', 'zh'])
        
        if not manual_id:
            from src.models.models import Manual
            manual = Manual.query.first()
            if not manual:
                return {'error': 'No manuals found in database'}, 404
            manual_id = manual.id
        
        # Test batch translation
        from src.services.translation_service import translation_service
        from src.models.models import Manual
        
        manual = Manual.query.get(manual_id)
        if not manual:
            return {'error': f'Manual {manual_id} not found'}, 404
        
        results = []
        for lang_code in language_codes:
            try:
                result = translation_service.translate_manual(
                    title=manual.title,
                    content=manual.content[:200],  # Test with first 200 chars
                    source_lang='ja',
                    target_lang=lang_code,
                    preserve_formatting=True
                )
                
                results.append({
                    'language_code': lang_code,
                    'status': 'success',
                    'translated_title': result['translated_title']
                })
            except Exception as e:
                results.append({
                    'language_code': lang_code,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return {
            'message': 'Batch translation test completed',
            'manual_id': manual_id,
            'results': results
        }, 200
        
    except Exception as e:
        logger.error(f"Batch translation test failed: {str(e)}")
        return {'error': str(e)}, 500


@test_bp.route('/jobs/test-worker', methods=['GET'])
def test_worker_connection():
    """
    Test Celery worker connection
    
    GET /api/test/jobs/test-worker
    """
    try:
        from src.workers.celery_app import celery
        
        # Check if workers are available
        inspect = celery.control.inspect()
        
        # Get active workers
        active = inspect.active()
        stats = inspect.stats()
        
        if not active and not stats:
            return {
                'status': 'no_workers',
                'message': 'No Celery workers are running. Start worker with: celery -A src.workers.celery_app worker --loglevel=info'
            }, 503
        
        return {
            'status': 'connected',
            'message': 'Celery workers are running',
            'active_workers': list(stats.keys()) if stats else [],
            'worker_count': len(stats) if stats else 0
        }, 200
        
    except Exception as e:
        logger.error(f"Worker connection test failed: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'message': 'Failed to connect to Celery. Make sure Redis is running and Celery worker is started.'
        }, 500


@test_bp.route('/jobs/create-test-job', methods=['POST'])
def create_test_job():
    """
    Create a test async job
    
    POST /api/test/jobs/create-test-job
    Body: {
        "job_type": "test",
        "duration": 10
    }
    """
    try:
        data = request.get_json() or {}
        duration = data.get('duration', 5)
        
        # Create a simple test task
        from src.workers.celery_app import celery
        
        @celery.task(bind=True)
        def test_task(self, duration):
            import time
            for i in range(duration):
                self.update_state(
                    state='PROGRESS',
                    meta={'current': i+1, 'total': duration, 'status': f'Step {i+1} of {duration}'}
                )
                time.sleep(1)
            return {'status': 'completed', 'duration': duration}
        
        # Start task
        result = test_task.delay(duration)
        
        return {
            'message': 'Test job created',
            'task_id': result.id,
            'duration': duration,
            'check_status': f'/api/jobs/{result.id}'
        }, 201
        
    except Exception as e:
        logger.error(f"Test job creation failed: {str(e)}")
        return {'error': str(e)}, 500


@test_bp.route('/health-check', methods=['GET'])
def comprehensive_health_check():
    """
    Comprehensive system health check
    
    GET /api/test/health-check
    """
    try:
        health = {
            'database': False,
            'redis': False,
            'celery': False,
            'gemini': False,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Check database
        try:
            db.session.execute('SELECT 1')
            health['database'] = True
        except:
            pass
        
        # Check Redis
        try:
            import redis
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            r = redis.from_url(redis_url)
            r.ping()
            health['redis'] = True
        except:
            pass
        
        # Check Celery
        try:
            from src.workers.celery_app import celery
            inspect = celery.control.inspect()
            stats = inspect.stats()
            if stats:
                health['celery'] = True
                health['celery_workers'] = len(stats)
        except:
            pass
        
        # Check Gemini API
        try:
            from src.services.translation_service import translation_service
            if translation_service.client:
                health['gemini'] = True
        except:
            pass
        
        # Overall status
        all_healthy = all([
            health['database'],
            health['redis'],
            health['celery'],
            health['gemini']
        ])
        
        health['status'] = 'healthy' if all_healthy else 'degraded'
        
        status_code = 200 if all_healthy else 503
        
        return health, status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }, 500

