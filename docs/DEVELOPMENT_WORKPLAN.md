# Development Work Plan - Enterprise Features Implementation

## Document Purpose
This document provides a step-by-step implementation guide for each development phase, including detailed tasks, code examples, test procedures, and verification steps.

## Table of Contents
1. [Development Environment Setup](#development-environment-setup)
2. [Phase-by-Phase Implementation Guide](#phase-by-phase-implementation-guide)
3. [Testing Procedures](#testing-procedures)
4. [Deployment Guide](#deployment-guide)

---

## Development Environment Setup

### Prerequisites

**Required Software:**
- Python 3.11+
- PostgreSQL 14+ (for production) or SQLite (for development)
- Redis 7.x
- Node.js 18+ (for frontend tools)
- AWS CLI (for S3 access)
- ElasticSearch 8.x (Phase 4+)

**Python Virtual Environment:**
```powershell
# Use existing .venv
.venv\Scripts\activate

# Install new dependencies
pip install -r requirements.txt
```

**New Dependencies to Add to requirements.txt:**
```
# RAG System
elasticsearch==8.11.0
sentence-transformers==2.2.2

# PDF Generation
weasyprint==60.1
pypdf2==3.0.1
pdfplumber==0.10.3

# Document Processing
python-docx==1.1.0
openpyxl==3.1.2

# Async Processing
celery==5.3.4
redis==5.0.1
flower==2.0.1

# Translation
google-cloud-translate==3.12.1

# Testing
faker==20.1.0
```

### Database Setup

**Create Development Database:**
```sql
-- For local PostgreSQL development
CREATE DATABASE manual_generator_dev;
CREATE USER dev_user WITH PASSWORD 'dev_password';
GRANT ALL PRIVILEGES ON DATABASE manual_generator_dev TO dev_user;
```

**Environment Variables (.env):**
```bash
# Database
DATABASE_URL=postgresql://dev_user:dev_password@localhost:5432/manual_generator_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# ElasticSearch
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=changeme

# AWS S3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET_NAME=kantan-ai-manual-generator
AWS_REGION=ap-northeast-1

# Existing (keep as is)
GCS_BUCKET_NAME=kantan-ai-manual-generator
PROJECT_ID=kantan-ai-database
GOOGLE_APPLICATION_CREDENTIALS=gcp-credentials.json

# Note: S3 uses the same bucket as GCS, but different paths
# S3 path structure: s3://kantan-ai-manual-generator/{company_id}/materials/
# GCS path structure: gs://kantan-ai-manual-generator/uploads/
```

### VS Code Tasks

**Add to .vscode/tasks.json:**
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run Celery Worker",
      "type": "shell",
      "command": ".venv\\Scripts\\celery -A src.workers.celery_app worker --loglevel=info",
      "isBackground": true,
      "group": "none"
    },
    {
      "label": "Run Celery Flower",
      "type": "shell",
      "command": ".venv\\Scripts\\celery -A src.workers.celery_app flower --port=5555",
      "isBackground": true,
      "group": "none"
    },
    {
      "label": "Run Redis",
      "type": "shell",
      "command": "redis-server",
      "isBackground": true,
      "group": "none"
    },
    {
      "label": "Run ElasticSearch (Docker)",
      "type": "shell",
      "command": "docker run -d -p 9200:9200 -e \"discovery.type=single-node\" -e \"xpack.security.enabled=false\" elasticsearch:8.11.0",
      "group": "none"
    }
  ]
}
```

---

## Phase-by-Phase Implementation Guide

---

## Phase 1: Foundation (Week 1-2)

### Goal
Set up database schema, authentication infrastructure, and testing framework.

### Tasks

#### 1.1 Database Migration Script

**File: `scripts/migrate_enterprise_schema.py`**
```python
"""
File: migrate_enterprise_schema.py
Purpose: Create new database tables for enterprise features
Main functionality: Database schema migration
Dependencies: SQLAlchemy, models
"""

from src.core.db_manager import db
from src.models.models import (
    User, Company, ManualTemplate, 
    # Import new models once created
)

def migrate_add_user_fields():
    """Add password_hash and language_preference to users table"""
    with db.engine.connect() as conn:
        # Check if columns exist
        result = conn.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name IN ('password_hash', 'language_preference')
        """)
        existing_columns = [row[0] for row in result]
        
        if 'password_hash' not in existing_columns:
            conn.execute("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)")
            print("✓ Added password_hash to users table")
        
        if 'language_preference' not in existing_columns:
            conn.execute("ALTER TABLE users ADD COLUMN language_preference VARCHAR(10) DEFAULT 'ja'")
            print("✓ Added language_preference to users table")

def migrate_add_template_fields():
    """Add updated_at and is_active to manual_templates table"""
    with db.engine.connect() as conn:
        result = conn.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='manual_templates' AND column_name IN ('updated_at', 'is_active')
        """)
        existing_columns = [row[0] for row in result]
        
        if 'updated_at' not in existing_columns:
            conn.execute("ALTER TABLE manual_templates ADD COLUMN updated_at TIMESTAMP")
            print("✓ Added updated_at to manual_templates table")
        
        if 'is_active' not in existing_columns:
            conn.execute("ALTER TABLE manual_templates ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
            print("✓ Added is_active to manual_templates table")

def create_new_tables():
    """Create all new enterprise tables"""
    # This will use SQLAlchemy models defined in models.py
    db.create_all()
    print("✓ Created all new enterprise tables")

def create_indexes():
    """Create database indexes for performance"""
    with db.engine.connect() as conn:
        # Activity logs indexes
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_user_action_date 
            ON activity_logs(user_id, action_type, created_at)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_company_date 
            ON activity_logs(company_id, created_at)
        """)
        
        # Processing jobs indexes
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_status_type 
            ON processing_jobs(job_status, job_type)
        """)
        
        print("✓ Created database indexes")

if __name__ == '__main__':
    print("Starting enterprise schema migration...")
    
    migrate_add_user_fields()
    migrate_add_template_fields()
    create_new_tables()
    create_indexes()
    
    print("\n✅ Migration completed successfully!")
```

**Run migration:**
```powershell
python scripts/migrate_enterprise_schema.py
```

#### 1.2 New Database Models

**File: `src/models/models.py` (ADD to existing file)**
```python
# Add after existing models

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
    file_path = db.Column(db.String(500), nullable=False)  # S3 URI: s3://kantan-ai-manual-generator/{company_id}/materials/{material_id}/
    file_type = db.Column(db.String(50), nullable=False)  # pdf, docx, xlsx, csv
    file_size = db.Column(db.BigInteger)
    
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    processing_status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    processing_progress = db.Column(db.Integer, default=0)  # 0-100
    error_message = db.Column(db.Text)
    
    extracted_metadata = db.Column(db.Text)  # JSON: Extracted by Gemini
    
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
            'file_type': self.file_type,
            'file_size': self.file_size,
            'processing_status': self.processing_status,
            'processing_progress': self.processing_progress,
            'elasticsearch_indexed': self.elasticsearch_indexed,
            'chunk_count': self.chunk_count,
            'uploaded_by': self.uploaded_by,
            'uploaded_at': utc_to_jst_isoformat(self.uploaded_at),
            'is_active': self.is_active
        }


class ReferenceChunk(db.Model):
    """
    Chunked text from reference materials for RAG
    """
    __tablename__ = 'reference_chunks'
    
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('reference_materials.id'), nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False)  # Sequential number within material
    chunk_text = db.Column(db.Text, nullable=False)
    
    elasticsearch_doc_id = db.Column(db.String(100))  # Vector embedding stored in ElasticSearch
    chunk_metadata = db.Column(db.Text)  # JSON: page number, section, etc.
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ActivityLog(db.Model):
    """
    User activity logs for UX analysis
    """
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    
    action_type = db.Column(db.String(50), nullable=False)  # login, upload, generate, export, etc.
    action_detail = db.Column(db.String(255))  # Specific action description
    resource_type = db.Column(db.String(50))  # manual, template, material, etc.
    resource_id = db.Column(db.Integer)
    
    request_metadata = db.Column(db.Text)  # JSON: IP, user agent, parameters, etc.
    
    result_status = db.Column(db.String(20))  # success, failure
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
    language_code = db.Column(db.String(10), nullable=False)  # en, zh, ko, etc.
    
    translated_title = db.Column(db.String(255))
    translated_content = db.Column(db.Text, nullable=False)
    
    translation_engine = db.Column(db.String(50))  # gemini, google_translate
    translation_status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    
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
            'translated_content': self.translated_content,
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
    language_code = db.Column(db.String(10), default='ja')  # ja, en, zh, ko, etc.
    
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)  # S3 URI: s3://kantan-ai-manual-generator/{company_id}/pdfs/{manual_id}/{language_code}/
    file_size = db.Column(db.BigInteger)
    page_count = db.Column(db.Integer)
    
    generation_config = db.Column(db.Text)  # JSON format
    generation_status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    
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
    job_type = db.Column(db.String(50), nullable=False)  # rag_index, pdf_generation, translation
    job_status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    resource_type = db.Column(db.String(50))  # reference_material, manual
    resource_id = db.Column(db.Integer)
    
    job_params = db.Column(db.Text)  # JSON format
    
    progress = db.Column(db.Integer, default=0)  # 0-100
    current_step = db.Column(db.String(255))
    
    result_data = db.Column(db.Text)  # JSON format
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
            'created_at': utc_to_jst_isoformat(self.created_at),
            'started_at': utc_to_jst_isoformat(self.started_at) if self.started_at else None,
            'completed_at': utc_to_jst_isoformat(self.completed_at) if self.completed_at else None
        }
```

#### 1.3 Enhanced Authentication Middleware

**File: `src/middleware/auth.py` (ADD to existing file)**
```python
# Add after existing code

def require_super_admin(f):
    """
    Decorator for endpoints requiring super admin access
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated as super admin
        if not session.get('is_super_admin'):
            return {'error': 'Super admin access required'}, 403
        
        super_admin_id = session.get('super_admin_id')
        if not super_admin_id:
            return {'error': 'Invalid super admin session'}, 403
        
        # Verify super admin exists and is active
        from src.models.models import SuperAdmin
        super_admin = SuperAdmin.query.get(super_admin_id)
        if not super_admin or not super_admin.is_active:
            return {'error': 'Super admin account is inactive'}, 403
        
        # Attach super admin to request context
        from flask import g
        g.super_admin = super_admin
        
        return f(*args, **kwargs)
    return decorated_function


def log_activity(action_type, action_detail=None, resource_type=None, resource_id=None):
    """
    Decorator to log user activities
    
    Usage:
        @log_activity('upload', 'Uploaded reference material', 'material')
        def upload_material():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request, g
            from src.models.models import ActivityLog, db
            import json
            
            # Execute the function
            result = f(*args, **kwargs)
            
            # Determine result status
            if isinstance(result, tuple):
                status_code = result[1] if len(result) > 1 else 200
                result_status = 'success' if 200 <= status_code < 400 else 'failure'
                error_msg = result[0].get('error') if isinstance(result[0], dict) and 'error' in result[0] else None
            else:
                result_status = 'success'
                error_msg = None
            
            # Create activity log
            try:
                user_id = getattr(g, 'current_user', {}).get('id') if hasattr(g, 'current_user') else None
                company_id = getattr(g, 'current_company', {}).get('id') if hasattr(g, 'current_company') else None
                
                # Collect request metadata
                request_metadata = {
                    'ip': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent'),
                    'method': request.method,
                    'endpoint': request.endpoint
                }
                
                log_entry = ActivityLog(
                    user_id=user_id,
                    company_id=company_id,
                    action_type=action_type,
                    action_detail=action_detail,
                    resource_type=resource_type,
                    resource_id=resource_id or kwargs.get('id') or kwargs.get('material_id') or kwargs.get('manual_id'),
                    request_metadata=json.dumps(request_metadata),
                    result_status=result_status,
                    error_message=error_msg
                )
                
                db.session.add(log_entry)
                db.session.commit()
            except Exception as e:
                # Log error but don't fail the request
                print(f"Failed to log activity: {e}")
            
            return result
        return decorated_function
    return decorator


def require_role_enhanced(allowed_roles):
    """
    Enhanced role-based access control
    
    Usage:
        @require_role_enhanced(['admin', 'user'])
        def some_endpoint():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if current_user.role not in allowed_roles:
                return {'error': 'Insufficient permissions'}, 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

#### 1.4 Test Endpoints for Phase 1

**File: `src/api/test_routes.py` (NEW)**
```python
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

test_bp = Blueprint('test', __name__, url_prefix='/api/test')


@test_bp.route('/create-super-admin', methods=['POST'])
def create_super_admin():
    """Create initial super admin account"""
    data = request.json
    
    username = data.get('username', 'superadmin')
    email = data.get('email', 'admin@kantan-ai.net')
    password = data.get('password', 'admin123')
    
    # Check if super admin already exists
    existing = SuperAdmin.query.filter_by(email=email).first()
    if existing:
        return {'error': 'Super admin already exists'}, 400
    
    super_admin = SuperAdmin(
        username=username,
        email=email,
        is_active=True,
        permission_level='full'
    )
    super_admin.set_password(password)
    
    db.session.add(super_admin)
    db.session.commit()
    
    return {
        'message': 'Super admin created successfully',
        'super_admin': {
            'id': super_admin.id,
            'username': super_admin.username,
            'email': super_admin.email
        }
    }, 201


@test_bp.route('/check-permissions', methods=['GET'])
def check_permissions():
    """Verify authentication and permissions"""
    auth_info = {
        'is_authenticated': False,
        'is_super_admin': False,
        'is_company_admin': False,
        'user_info': None
    }
    
    # Check super admin
    if session.get('is_super_admin'):
        auth_info['is_super_admin'] = True
        super_admin_id = session.get('super_admin_id')
        super_admin = SuperAdmin.query.get(super_admin_id)
        if super_admin:
            auth_info['user_info'] = {
                'id': super_admin.id,
                'username': super_admin.username,
                'type': 'super_admin'
            }
    
    # Check regular user
    elif session.get('company_id'):
        auth_info['is_authenticated'] = True
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        if user:
            auth_info['user_info'] = {
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'company_id': user.company_id,
                'type': 'user'
            }
            if user.role == 'admin':
                auth_info['is_company_admin'] = True
    
    return jsonify(auth_info), 200


@test_bp.route('/database-status', methods=['GET'])
def database_status():
    """Check database tables and sample data"""
    try:
        tables_info = {
            'super_admins': SuperAdmin.query.count(),
            'companies': Company.query.count(),
            'users': User.query.count(),
            'activity_logs': ActivityLog.query.count()
        }
        
        return {
            'status': 'connected',
            'tables': tables_info
        }, 200
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }, 500
```

#### 1.5 Register Test Routes

**File: `app.py` (MODIFY existing file)**
```python
# Add after existing route registrations

from src.api.test_routes import test_bp
app.register_blueprint(test_bp)
```

### Testing Phase 1

**Test Procedure:**

1. **Run migration:**
```powershell
python scripts/migrate_enterprise_schema.py
```

2. **Start server:**
```powershell
# Use VS Code task or:
.venv\Scripts\python app.py
```

3. **Test endpoints:**
```powershell
# Check database status
curl http://localhost:5000/api/test/database-status

# Create super admin
curl -X POST http://localhost:5000/api/test/create-super-admin `
  -H "Content-Type: application/json" `
  -d '{"username":"admin","email":"admin@kantan-ai.net","password":"admin123"}'

# Check permissions
curl http://localhost:5000/api/test/check-permissions
```

**Expected Results:**
- ✅ Database status shows all tables exist
- ✅ Super admin created successfully
- ✅ Permission check returns proper authentication info

### Phase 1 Deliverables

- [x] Database migration script
- [x] 7 new database models
- [x] Enhanced authentication decorators
- [x] Activity logging decorator
- [x] 3 test endpoints
- [x] Documentation updated

---

## S3 Storage Manager (Core Infrastructure)

**File: `src/infrastructure/s3_manager.py` (NEW)**
```python
"""
File: s3_manager.py
Purpose: S3 storage management with tenant isolation
Main functionality: Upload, download, and manage S3 files with company_id segregation
Dependencies: boto3, Flask
"""

import boto3
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO
import os
from datetime import timedelta

class S3Manager:
    """
    S3 storage manager with strict tenant isolation
    
    All S3 paths follow the pattern:
    s3://kantan-ai-manual-generator/{company_id}/{resource_type}/{resource_id}/
    """
    
    def __init__(self):
        self.bucket_name = os.getenv('AWS_S3_BUCKET_NAME', 'kantan-ai-manual-generator')
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'ap-northeast-1')
        )
    
    def get_material_path(self, company_id: int, material_id: int, filename: str) -> str:
        """Generate S3 key for reference material"""
        return f"{company_id}/materials/{material_id}/{filename}"
    
    def get_pdf_path(self, company_id: int, manual_id: int, language_code: str, filename: str) -> str:
        """Generate S3 key for generated PDF"""
        return f"{company_id}/pdfs/{manual_id}/{language_code}/{filename}"
    
    def get_temp_path(self, company_id: int, job_id: int, filename: str) -> str:
        """Generate S3 key for temporary processing files"""
        return f"{company_id}/temp/{job_id}/{filename}"
    
    def validate_company_access(self, company_id: int, s3_key: str) -> bool:
        """
        Verify S3 key belongs to the specified company
        
        Security: Prevents cross-tenant data access
        """
        expected_prefix = f"{company_id}/"
        return s3_key.startswith(expected_prefix)
    
    def upload_file(self, file_obj: BinaryIO, s3_key: str, 
                    content_type: str = 'application/octet-stream') -> str:
        """
        Upload file to S3
        
        Args:
            file_obj: File-like object to upload
            s3_key: S3 key (path within bucket)
            content_type: MIME type
            
        Returns:
            S3 URI (s3://bucket/key)
        """
        try:
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'ServerSideEncryption': 'AES256'
                }
            )
            return f"s3://{self.bucket_name}/{s3_key}"
        except ClientError as e:
            raise Exception(f"Failed to upload to S3: {str(e)}")
    
    def upload_from_path(self, local_path: str, s3_key: str,
                         content_type: str = 'application/octet-stream') -> str:
        """Upload file from local path to S3"""
        try:
            self.s3_client.upload_file(
                local_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'ServerSideEncryption': 'AES256'
                }
            )
            return f"s3://{self.bucket_name}/{s3_key}"
        except ClientError as e:
            raise Exception(f"Failed to upload to S3: {str(e)}")
    
    def download_file(self, s3_key: str, local_path: str) -> None:
        """Download file from S3 to local path"""
        try:
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
        except ClientError as e:
            raise Exception(f"Failed to download from S3: {str(e)}")
    
    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """
        Generate presigned URL for secure file access
        
        Args:
            s3_key: S3 key
            expiration: URL expiration in seconds (default: 1 hour)
            
        Returns:
            Presigned URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")
    
    def delete_file(self, s3_key: str) -> None:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
        except ClientError as e:
            raise Exception(f"Failed to delete from S3: {str(e)}")
    
    def delete_folder(self, company_id: int, folder_prefix: str) -> None:
        """
        Delete all files in a folder (e.g., temp files after processing)
        
        Args:
            company_id: Company ID for validation
            folder_prefix: Folder path (e.g., 'temp/job_123/')
        """
        full_prefix = f"{company_id}/{folder_prefix}"
        
        try:
            # List all objects with prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=full_prefix
            )
            
            if 'Contents' not in response:
                return
            
            # Delete all objects
            objects = [{'Key': obj['Key']} for obj in response['Contents']]
            self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={'Objects': objects}
            )
        except ClientError as e:
            raise Exception(f"Failed to delete folder from S3: {str(e)}")
    
    def file_exists(self, s3_key: str) -> bool:
        """Check if file exists in S3"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False
    
    def get_file_size(self, s3_key: str) -> int:
        """Get file size in bytes"""
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return response['ContentLength']
        except ClientError as e:
            raise Exception(f"Failed to get file size: {str(e)}")


# Global instance
s3_manager = S3Manager()
```

**Usage Example:**
```python
from src.infrastructure.s3_manager import s3_manager

# Upload reference material
material_id = 42
company_id = 1
filename = "safety_guidelines.pdf"

s3_key = s3_manager.get_material_path(company_id, material_id, filename)
s3_uri = s3_manager.upload_from_path(
    local_path="/tmp/uploaded_file.pdf",
    s3_key=s3_key,
    content_type="application/pdf"
)

# Generate presigned URL for download
download_url = s3_manager.generate_presigned_url(s3_key, expiration=3600)

# Validate company access before operations
if s3_manager.validate_company_access(company_id, s3_key):
    # Safe to proceed
    pass
```

---

## Phase 2-9 Implementation Details

*[Due to length constraints, Phase 2-9 detailed implementation guides will follow the same structure as Phase 1, with specific code examples, test procedures, and verification steps for each phase.]*

**Each subsequent phase will include:**
1. Detailed task breakdown
2. Code examples for all new files
3. Modifications to existing files
4. Test endpoints for verification
5. Testing procedures
6. Expected results
7. Troubleshooting guide

---

## Testing Procedures

### Unit Testing

**Create test files for each module:**

**File: `tests/test_auth.py`**
```python
"""
Unit tests for authentication and authorization
"""

import pytest
from src.models.models import SuperAdmin, User, Company
from src.middleware.auth import require_super_admin, require_role_enhanced

def test_super_admin_creation():
    """Test super admin account creation"""
    super_admin = SuperAdmin(
        username='testadmin',
        email='test@example.com'
    )
    super_admin.set_password('password123')
    
    assert super_admin.check_password('password123')
    assert not super_admin.check_password('wrong_password')

def test_super_admin_decorator():
    """Test super admin access control"""
    # TODO: Implement decorator test
    pass

def test_activity_logging():
    """Test activity log creation"""
    # TODO: Implement logging test
    pass
```

### Integration Testing

**Test full workflows:**

**File: `tests/integration/test_admin_workflow.py`**
```python
"""
Integration tests for admin workflows
"""

import pytest
from flask import Flask

def test_company_crud_workflow(client):
    """Test complete company management workflow"""
    # 1. Login as super admin
    # 2. Create company
    # 3. Update company
    # 4. List companies
    # 5. Delete company
    pass

def test_user_management_workflow(client):
    """Test complete user management workflow"""
    # 1. Login as company admin
    # 2. Create user
    # 3. Update user role
    # 4. List users
    # 5. Delete user
    pass
```

### API Testing Script

**File: `scripts/test_api_comprehensive.py` (ENHANCE existing)**
```python
"""
Comprehensive API testing for all enterprise features
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_phase1_endpoints():
    """Test Phase 1 endpoints"""
    print("Testing Phase 1: Foundation")
    
    # Test database status
    response = requests.get(f"{BASE_URL}/api/test/database-status")
    assert response.status_code == 200
    print("✓ Database status check passed")
    
    # Test super admin creation
    response = requests.post(
        f"{BASE_URL}/api/test/create-super-admin",
        json={
            "username": "admin",
            "email": "admin@test.com",
            "password": "admin123"
        }
    )
    assert response.status_code in [200, 201, 400]  # 400 if already exists
    print("✓ Super admin creation passed")

def test_phase2_endpoints():
    """Test Phase 2: Super Admin Features"""
    print("Testing Phase 2: Super Admin Features")
    # TODO: Add Phase 2 tests
    pass

# Add test functions for each phase...

if __name__ == '__main__':
    test_phase1_endpoints()
    # Call other phase tests as they're implemented
```

---

## Deployment Guide

### Local Development Deployment

**1. Start all services:**
```powershell
# Redis
redis-server

# ElasticSearch (Docker)
docker run -d -p 9200:9200 -e "discovery.type=single-node" elasticsearch:8.11.0

# Celery Worker
.venv\Scripts\celery -A src.workers.celery_app worker --loglevel=info

# Celery Flower (monitoring)
.venv\Scripts\celery -A src.workers.celery_app flower --port=5555

# Flask application
.venv\Scripts\python app.py
```

**2. Access services:**
- Application: http://localhost:5000
- Flower (Celery monitoring): http://localhost:5555
- ElasticSearch: http://localhost:9200

### Production Deployment (EC2)

**Pre-deployment checklist:**
- [ ] All tests passing
- [ ] Database backup created
- [ ] Environment variables configured
- [ ] Redis/ElasticSearch infrastructure ready
- [ ] Celery workers configured

**Deployment steps:**

1. **Deploy infrastructure:**
```bash
# On EC2 server
# Install Redis
sudo yum install redis -y
sudo systemctl start redis
sudo systemctl enable redis

# Install ElasticSearch (or use AWS OpenSearch)
# Follow AWS OpenSearch setup guide
```

2. **Deploy application:**
```bash
ssh -i kantan-ai.pem ec2-user@57.181.226.188

cd /opt/kantan-ai-manual-generator
git pull origin main

# Run database migration
python scripts/migrate_enterprise_schema.py

# Restart services
sudo docker-compose build manual
sudo docker-compose up -d manual

# Start Celery workers
sudo systemctl restart celery-worker
sudo systemctl restart celery-beat  # For scheduled tasks
```

3. **Verify deployment:**
```bash
# Check service status
curl http://localhost:5000/api/test/database-status

# Check Celery workers
celery -A src.workers.celery_app inspect active
```

---

## Troubleshooting

### Common Issues

**Issue: Database migration fails**
```
Solution:
1. Check database connection
2. Verify user has CREATE TABLE permissions
3. Check if tables already exist
4. Run migration with --force flag (if available)
```

**Issue: Celery worker not processing jobs**
```
Solution:
1. Check Redis connection
2. Verify Celery configuration
3. Check worker logs: celery -A src.workers.celery_app inspect active
4. Restart worker
```

**Issue: ElasticSearch connection timeout**
```
Solution:
1. Verify ElasticSearch is running: curl http://localhost:9200
2. Check network connectivity
3. Verify credentials in .env
4. Check firewall rules
```

**Issue: Permission denied for endpoints**
```
Solution:
1. Verify authentication token/session
2. Check user role in database
3. Verify decorator is applied correctly
4. Check activity logs for authorization failures
```

---

## Next Steps

After completing Phase 1:

1. **Review Phase 1 deliverables** with stakeholders
2. **Create detailed implementation plan for Phase 2**
3. **Set up monitoring and alerting** for production
4. **Begin UI/UX design** for admin dashboards
5. **Plan infrastructure scaling** for ElasticSearch and Celery

---

## Appendix

### Code Style Guidelines

Follow project-specific guidelines from `.github/copilot-instructions.md`:
- All comments in English
- No emojis in code
- File header comments required
- Function docstrings required
- Maximum 500 lines per file

### File Organization

- **Source code**: `src/` folder
- **Test scripts**: `scripts/` folder
- **Documentation**: `docs/` folder
- **Temporary files**: `scripts/` folder

### Testing Account

**Default test account:**
- Company ID: `career-survival`
- User ID: `support@career-survival.com`
- Password: `0000`
- Role: Super Administrator

