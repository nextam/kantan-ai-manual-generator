# Enterprise Features Specification - Manual Generator System

## Document Purpose
This document specifies the detailed requirements, database schema, API endpoints, and implementation guidelines for transforming the Manual Generator into a full-fledged enterprise SaaS service.

## Table of Contents
1. [Overview](#overview)
2. [User Roles & Permissions](#user-roles--permissions)
3. [Database Schema](#database-schema)
4. [API Endpoints](#api-endpoints)
5. [Technology Stack](#technology-stack)
6. [Implementation Phases](#implementation-phases)

---

## Overview

### Objective
Add multi-tenant enterprise features including:
- Super admin company/user management
- Company-level template and user management
- RAG-based reference material system
- PDF export and multi-language translation
- Async processing for heavy operations

### Target User Groups
1. **Super Administrators** - System-wide management
2. **Company Administrators** - Company-level management
3. **General Users** - End users creating manuals

---

## User Roles & Permissions

### Role Hierarchy
```
SuperAdmin (permission_level: full)
  ├─ Company Administrator (User.role: admin)
  └─ General User (User.role: user)
```

### Permission Matrix

| Feature | Super Admin | Company Admin | General User |
|---------|-------------|---------------|--------------|
| Company Management | ✓ | - | - |
| All Users Management | ✓ | - | - |
| Activity Logs (All) | ✓ | - | - |
| Company Users Management | ✓ | ✓ | - |
| Template Management | ✓ | ✓ | - |
| Reference Material Management | ✓ | ✓ | ✓ |
| Manual Generation | ✓ | ✓ | ✓ |
| PDF Export | ✓ | ✓ | ✓ |
| Multi-language Translation | ✓ | ✓ | ✓ |

---

## Database Schema

### 1. Existing Tables (Enhancement Required)

#### `users` table (EXISTING - Add fields)
```python
# Add new fields to User model:
password_hash = db.Column(db.String(255), nullable=True)  # NEW: For user password
language_preference = db.Column(db.String(10), default='ja')  # NEW: UI language
```

#### `manual_templates` table (EXISTING - Enhance)
```python
class ManualTemplate(db.Model):
    # EXISTING fields
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    template_content = db.Column(db.Text, nullable=False)  # JSON format
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_default = db.Column(db.Boolean, default=False)
    
    # NEW fields
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Template configuration (JSON format):
    # {
    #   "background_info": "Manufacturing process manual for factory workers",
    #   "structure": "step-by-step",
    #   "detail_level": "high",  # low, medium, high
    #   "writing_style": "formal",  # formal, casual, technical
    #   "language": "ja",  # ja, en, zh, etc.
    #   "layout": "standard",  # standard, compact, detailed
    #   "output_length": "medium"  # short, medium, long
    # }
```

### 2. New Tables Required

#### `reference_materials` table
```python
class ReferenceMaterial(db.Model):
    """RAG reference materials for manual generation"""
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
    
    # Processing status
    processing_status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    processing_progress = db.Column(db.Integer, default=0)  # 0-100
    error_message = db.Column(db.Text)
    
    # Metadata extraction result (JSON format)
    extracted_metadata = db.Column(db.Text)  # Extracted by Gemini
    
    # RAG registration
    elasticsearch_indexed = db.Column(db.Boolean, default=False)
    elasticsearch_index_name = db.Column(db.String(100))
    chunk_count = db.Column(db.Integer, default=0)
    
    is_active = db.Column(db.Boolean, default=True)
```

#### `reference_chunks` table
```python
class ReferenceChunk(db.Model):
    """Chunked text from reference materials for RAG"""
    __tablename__ = 'reference_chunks'
    
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('reference_materials.id'), nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False)  # Sequential number within material
    chunk_text = db.Column(db.Text, nullable=False)
    
    # Vector embedding (stored in ElasticSearch)
    elasticsearch_doc_id = db.Column(db.String(100))
    
    # Chunk metadata (JSON format)
    chunk_metadata = db.Column(db.Text)  # page number, section, etc.
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

#### `activity_logs` table
```python
class ActivityLog(db.Model):
    """User activity logs for UX analysis"""
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    
    # Activity details
    action_type = db.Column(db.String(50), nullable=False)  # login, upload, generate, export, etc.
    action_detail = db.Column(db.String(255))  # Specific action description
    resource_type = db.Column(db.String(50))  # manual, template, material, etc.
    resource_id = db.Column(db.Integer)
    
    # Request metadata (JSON format)
    request_metadata = db.Column(db.Text)  # IP, user agent, parameters, etc.
    
    # Result
    result_status = db.Column(db.String(20))  # success, failure
    error_message = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Indexes for efficient querying
    __table_args__ = (
        db.Index('idx_user_action_date', 'user_id', 'action_type', 'created_at'),
        db.Index('idx_company_date', 'company_id', 'created_at'),
    )
```

#### `manual_translations` table
```python
class ManualTranslation(db.Model):
    """Translated versions of manuals"""
    __tablename__ = 'manual_translations'
    
    id = db.Column(db.Integer, primary_key=True)
    manual_id = db.Column(db.Integer, db.ForeignKey('manuals.id'), nullable=False)
    language_code = db.Column(db.String(10), nullable=False)  # en, zh, ko, etc.
    
    # Translated content
    translated_title = db.Column(db.String(255))
    translated_content = db.Column(db.Text, nullable=False)
    
    # Translation metadata
    translation_engine = db.Column(db.String(50))  # gemini, google_translate
    translation_status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('manual_id', 'language_code', name='unique_manual_translation'),
    )
```

#### `manual_pdfs` table
```python
class ManualPDF(db.Model):
    """Generated PDF files from manuals"""
    __tablename__ = 'manual_pdfs'
    
    id = db.Column(db.Integer, primary_key=True)
    manual_id = db.Column(db.Integer, db.ForeignKey('manuals.id'), nullable=False)
    language_code = db.Column(db.String(10), default='ja')  # Language of the PDF
    
    # PDF file info
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)  # S3 URI: s3://kantan-ai-manual-generator/{company_id}/pdfs/{manual_id}/{language_code}/
    file_size = db.Column(db.BigInteger)
    page_count = db.Column(db.Integer)
    
    # Generation config (JSON format)
    generation_config = db.Column(db.Text)  # Paper size, orientation, etc.
    
    generation_status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # For A4 fitting
    # {
    #   "paper_size": "A4",
    #   "orientation": "portrait",
    #   "margin": {"top": 20, "bottom": 20, "left": 15, "right": 15},
    #   "include_toc": true,
    #   "include_images": true
    # }
```

#### `processing_jobs` table
```python
class ProcessingJob(db.Model):
    """Async job management for heavy processing"""
    __tablename__ = 'processing_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    job_type = db.Column(db.String(50), nullable=False)  # rag_index, pdf_generation, translation
    job_status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Related resource
    resource_type = db.Column(db.String(50))  # reference_material, manual
    resource_id = db.Column(db.Integer)
    
    # Job parameters (JSON format)
    job_params = db.Column(db.Text)
    
    # Progress tracking
    progress = db.Column(db.Integer, default=0)  # 0-100
    current_step = db.Column(db.String(255))
    
    # Result
    result_data = db.Column(db.Text)  # JSON format
    error_message = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    __table_args__ = (
        db.Index('idx_job_status_type', 'job_status', 'job_type'),
    )
```

---

## API Endpoints

### Authentication & Authorization

All endpoints require authentication. Role-based access control is enforced.

**Existing auth patterns to reuse:**
- `@require_role('admin')` decorator for company admin
- Custom `@require_super_admin` decorator (NEW)
- Session management via `AuthManager`

### 1. Super Admin Endpoints

#### Company Management

**List Companies**
```
GET /api/admin/companies
Query params: page, per_page, search (name/code), status (active/inactive)
Response: {
  "companies": [
    {
      "id": 1,
      "name": "Example Corp",
      "company_code": "example-corp",
      "is_active": true,
      "user_count": 15,
      "manual_count": 42,
      "created_at": "2025-01-01T00:00:00+09:00"
    }
  ],
  "total": 100,
  "page": 1,
  "per_page": 20
}
```

**Create Company**
```
POST /api/admin/companies
Body: {
  "name": "New Company",
  "company_code": "new-company",
  "password": "initial_password",
  "settings": {}
}
Response: { "company": {...}, "message": "Company created successfully" }
```

**Update Company**
```
PUT /api/admin/companies/{company_id}
Body: { "name": "...", "is_active": true, "settings": {...} }
Response: { "company": {...}, "message": "Company updated successfully" }
```

**Delete Company**
```
DELETE /api/admin/companies/{company_id}
Response: { "message": "Company deleted successfully" }
```

#### User Management (All Companies)

**List All Users**
```
GET /api/admin/users
Query params: page, per_page, company_id, role, search (username/email)
Response: {
  "users": [
    {
      "id": 1,
      "username": "user@example.com",
      "email": "user@example.com",
      "company_id": 1,
      "company_name": "Example Corp",
      "role": "admin",
      "is_active": true,
      "last_login": "2025-01-15T10:30:00+09:00",
      "created_at": "2025-01-01T00:00:00+09:00"
    }
  ],
  "total": 500,
  "page": 1,
  "per_page": 20
}
```

**Create User**
```
POST /api/admin/users
Body: {
  "username": "newuser",
  "email": "newuser@example.com",
  "company_id": 1,
  "role": "user",
  "password": "initial_password"
}
Response: { "user": {...}, "message": "User created successfully" }
```

**Update User**
```
PUT /api/admin/users/{user_id}
Body: { "role": "admin", "is_active": true }
Response: { "user": {...}, "message": "User updated successfully" }
```

**Delete User**
```
DELETE /api/admin/users/{user_id}
Response: { "message": "User deleted successfully" }
```

**Proxy Login (代理ログイン)**
```
POST /api/admin/users/{user_id}/proxy-login
Response: {
  "redirect_url": "/",
  "message": "Logged in as {username}"
}
# Creates a session as the target user while preserving super admin session
```

#### Activity Logs

**List Activity Logs**
```
GET /api/admin/activity-logs
Query params: 
  - page, per_page
  - company_id
  - user_id
  - action_type (login, upload, generate, export, etc.)
  - date_from, date_to
  - result_status (success, failure)
Response: {
  "logs": [
    {
      "id": 1,
      "user_id": 5,
      "username": "user@example.com",
      "company_name": "Example Corp",
      "action_type": "generate",
      "action_detail": "Generated manual 'Assembly Process'",
      "resource_type": "manual",
      "resource_id": 42,
      "result_status": "success",
      "created_at": "2025-01-15T14:30:00+09:00"
    }
  ],
  "total": 10000,
  "page": 1,
  "per_page": 50
}
```

**Export Activity Logs (CSV)**
```
GET /api/admin/activity-logs/export
Query params: Same as list endpoint
Response: CSV file download
```

### 2. Company Admin Endpoints

#### User Management (Own Company)

**List Company Users**
```
GET /api/company/users
Query params: page, per_page, role, search (username/email)
Response: {
  "users": [
    {
      "id": 1,
      "username": "user@example.com",
      "email": "user@example.com",
      "role": "user",
      "is_active": true,
      "last_login": "2025-01-15T10:30:00+09:00",
      "created_at": "2025-01-01T00:00:00+09:00"
    }
  ],
  "total": 15,
  "page": 1,
  "per_page": 20
}
```

**Create Company User**
```
POST /api/company/users
Body: {
  "username": "newuser",
  "email": "newuser@example.com",
  "role": "user",
  "password": "initial_password"
}
Response: { "user": {...}, "message": "User created successfully" }
```

**Update Company User**
```
PUT /api/company/users/{user_id}
Body: { "role": "admin", "is_active": true }
Response: { "user": {...}, "message": "User updated successfully" }
```

**Delete Company User**
```
DELETE /api/company/users/{user_id}
Response: { "message": "User deleted successfully" }
```

#### Template Management

**List Templates**
```
GET /api/company/templates
Query params: page, per_page, search (name)
Response: {
  "templates": [
    {
      "id": 1,
      "name": "Standard Assembly Process",
      "description": "Template for standard assembly procedures",
      "is_default": true,
      "created_by": 1,
      "created_by_username": "admin@example.com",
      "created_at": "2025-01-01T00:00:00+09:00",
      "updated_at": "2025-01-10T15:00:00+09:00"
    }
  ],
  "total": 5,
  "page": 1,
  "per_page": 20
}
```

**Get Template**
```
GET /api/company/templates/{template_id}
Response: {
  "id": 1,
  "name": "Standard Assembly Process",
  "description": "...",
  "template_content": {
    "background_info": "Manufacturing process manual for factory workers",
    "structure": "step-by-step",
    "detail_level": "high",
    "writing_style": "formal",
    "language": "ja",
    "layout": "standard",
    "output_length": "medium"
  },
  "is_default": true,
  "created_by": 1,
  "created_at": "...",
  "updated_at": "..."
}
```

**Create Template**
```
POST /api/company/templates
Body: {
  "name": "New Template",
  "description": "Template description",
  "template_content": {
    "background_info": "...",
    "structure": "step-by-step",
    ...
  },
  "is_default": false
}
Response: { "template": {...}, "message": "Template created successfully" }
```

**Update Template**
```
PUT /api/company/templates/{template_id}
Body: { "name": "...", "template_content": {...}, "is_default": true }
Response: { "template": {...}, "message": "Template updated successfully" }
```

**Delete Template**
```
DELETE /api/company/templates/{template_id}
Response: { "message": "Template deleted successfully" }
```

### 3. General User Endpoints

#### Reference Materials Management

**List Reference Materials**
```
GET /api/materials
Query params: page, per_page, file_type, processing_status, search (title/filename)
Response: {
  "materials": [
    {
      "id": 1,
      "title": "Safety Guidelines 2025",
      "description": "Updated safety procedures",
      "original_filename": "safety_guidelines.pdf",
      "file_type": "pdf",
      "file_size": 2048576,
      "processing_status": "completed",
      "elasticsearch_indexed": true,
      "chunk_count": 45,
      "uploaded_by": 5,
      "uploaded_by_username": "user@example.com",
      "uploaded_at": "2025-01-10T09:00:00+09:00"
    }
  ],
  "total": 20,
  "page": 1,
  "per_page": 20
}
```

**Upload Reference Material**
```
POST /api/materials
Content-Type: multipart/form-data
Body: {
  "file": <file>,
  "title": "Document Title",
  "description": "Document description"
}
Response: {
  "material": {
    "id": 1,
    "processing_status": "pending",
    "job_id": 42
  },
  "message": "Material uploaded. Processing started."
}
# Triggers async processing job
```

**Get Material Processing Status**
```
GET /api/materials/{material_id}/status
Response: {
  "id": 1,
  "processing_status": "processing",
  "processing_progress": 65,
  "current_step": "Extracting metadata with Gemini",
  "job_id": 42
}
```

**Update Reference Material**
```
PUT /api/materials/{material_id}
Body: { "title": "...", "description": "...", "is_active": true }
Response: { "material": {...}, "message": "Material updated successfully" }
```

**Delete Reference Material**
```
DELETE /api/materials/{material_id}
Response: { "message": "Material deleted successfully" }
# Also removes from ElasticSearch index
```

#### Manual Generation with Templates

**Get Available Templates**
```
GET /api/manuals/templates
Response: {
  "templates": [
    {
      "id": 1,
      "name": "Standard Assembly",
      "description": "...",
      "is_default": true
    },
    {
      "id": 2,
      "name": "Detailed Technical",
      "description": "..."
    }
  ]
}
```

**Generate Manual with Template(s)**
```
POST /api/manuals/generate
Body: {
  "title": "Assembly Process Manual",
  "video_files": [1, 2],  # UploadedFile IDs
  "template_ids": [1, 3],  # Generate multiple versions
  "custom_template": {  # Optional: Override template
    "background_info": "Custom background",
    "detail_level": "high",
    ...
  },
  "use_rag": true  # Enable RAG search
}
Response: {
  "manuals": [
    {
      "id": 101,
      "title": "Assembly Process Manual (Standard Assembly)",
      "template_id": 1,
      "generation_status": "pending"
    },
    {
      "id": 102,
      "title": "Assembly Process Manual (Detailed Technical)",
      "template_id": 3,
      "generation_status": "pending"
    }
  ],
  "message": "Manual generation started for 2 templates"
}
# Creates multiple Manual records for each template
```

#### PDF Export

**Generate PDF**
```
POST /api/manuals/{manual_id}/pdf
Body: {
  "language_code": "ja",  # Optional: Use translated version
  "config": {
    "paper_size": "A4",
    "orientation": "portrait",
    "include_toc": true,
    "include_images": true
  }
}
Response: {
  "pdf": {
    "id": 1,
    "generation_status": "pending",
    "job_id": 55
  },
  "message": "PDF generation started"
}
# Triggers async PDF generation
```

**Get PDF Status**
```
GET /api/manuals/{manual_id}/pdf/{pdf_id}/status
Response: {
  "id": 1,
  "generation_status": "completed",
  "file_path": "s3://...",
  "download_url": "/api/manuals/{manual_id}/pdf/{pdf_id}/download"
}
```

**Download PDF**
```
GET /api/manuals/{manual_id}/pdf/{pdf_id}/download
Response: PDF file download with proper headers
```

#### Multi-language Translation

**Translate Manual**
```
POST /api/manuals/{manual_id}/translate
Body: {
  "language_codes": ["en", "zh", "ko"]  # Multiple languages
}
Response: {
  "translations": [
    {
      "id": 1,
      "language_code": "en",
      "translation_status": "pending",
      "job_id": 60
    },
    {
      "id": 2,
      "language_code": "zh",
      "translation_status": "pending",
      "job_id": 61
    }
  ],
  "message": "Translation started for 3 languages"
}
```

**Get Translation Status**
```
GET /api/manuals/{manual_id}/translations/{translation_id}/status
Response: {
  "id": 1,
  "language_code": "en",
  "translation_status": "completed",
  "job_id": 60
}
```

**Get Translated Manual**
```
GET /api/manuals/{manual_id}/translations/{language_code}
Response: {
  "id": 1,
  "manual_id": 42,
  "language_code": "en",
  "translated_title": "Assembly Process Manual",
  "translated_content": "...",
  "translation_status": "completed"
}
```

#### Async Job Status

**Get Job Status**
```
GET /api/jobs/{job_id}
Response: {
  "id": 42,
  "job_type": "rag_index",
  "job_status": "processing",
  "progress": 75,
  "current_step": "Creating embeddings (chunk 30/40)",
  "created_at": "...",
  "started_at": "..."
}
```

---

## Technology Stack

### New Technology Components

#### 1. RAG System

**ElasticSearch**
- Version: 8.x
- Purpose: Semantic search for reference materials
- Features:
  - Vector similarity search
  - Text search with BM25
  - Hybrid search combining vector + keyword

**Vector Embeddings**
- Model: Vertex AI Text Embedding (text-embedding-004)
- Dimension: 768
- Storage: ElasticSearch dense_vector field

**Chunking Strategy**
- PDF: Extract text → Split by semantic boundaries (paragraphs/sections)
- Word/Excel: Convert to text → Split by sections/rows
- Chunk size: 500-1000 tokens (configurable)
- Overlap: 50 tokens between chunks

**Processing Pipeline:**
1. Upload to S3: `{company_id}/materials/{material_id}/{filename}`
2. Extract text (stored temporarily in `{company_id}/temp/{job_id}/`)
3. Gemini metadata extraction
4. Chunk text and generate embeddings
5. Index in ElasticSearch with company_id field
6. Clean up temporary files
7. Update database with processing status

#### 2. PDF Generation

**Library: WeasyPrint**
```python
# Install: pip install weasyprint
# A4 size: 210mm × 297mm
# Render HTML to PDF with CSS Paged Media support
```

**Features:**
- HTML/CSS to PDF conversion
- A4 page fitting with auto-scaling
- Table of contents generation
- Image embedding
- Custom fonts support

#### 3. Multi-language Translation

**Primary: Vertex AI Gemini**
```python
# Use gemini-2.0-flash-exp for cost-effective translation
# Batch translation for efficiency
# Preserve markdown formatting
```

**Fallback: Google Cloud Translation API**
- For simple text translation
- Cost-effective for large volumes

#### 4. Async Processing

**Celery + Redis**
```python
# Task queue: Celery 5.x
# Message broker: Redis 7.x
# Result backend: Redis
```

**Job Types:**
- RAG indexing (long-running)
- PDF generation (medium)
- Translation (medium)
- Batch operations (variable)

**Monitoring:**
- Flower (Celery monitoring tool)
- Job status API endpoints

#### 5. Storage

**AWS S3 (Unified Bucket with Tenant Isolation)**
- **Bucket Name**: `kantan-ai-manual-generator` (same as GCS for consistency)
- **Path Structure**: Strictly segregated by company_id for data isolation
  ```
  s3://kantan-ai-manual-generator/
    ├── {company_id}/
    │   ├── materials/           # Reference materials
    │   │   └── {material_id}/
    │   │       └── original_file.pdf
    │   ├── pdfs/                # Generated PDFs
    │   │   └── {manual_id}/
    │   │       └── {language_code}/
    │   │           └── manual.pdf
    │   └── temp/                # Temporary processing files
    │       └── {job_id}/
  ```
- **GCS Usage**: Keep existing video uploads in GCS
  ```
  gs://kantan-ai-manual-generator/
    └── uploads/
        └── {company_id}/
            └── videos/
  ```

**Path Examples:**
- Reference material: `s3://kantan-ai-manual-generator/1/materials/42/safety_guidelines.pdf`
- Generated PDF: `s3://kantan-ai-manual-generator/1/pdfs/101/en/manual.pdf`
- Temporary chunk: `s3://kantan-ai-manual-generator/1/temp/job_55/chunk_10.txt`
- Video (GCS): `gs://kantan-ai-manual-generator/uploads/1/videos/video_123.mp4`

**Security:**
- IAM policies enforce company_id path prefix access
- Signed URLs with expiration for downloads
- Server-side encryption (AES-256) at rest
- TLS 1.2+ for data in transit

**S3 Path Helper Functions (Implementation Reference):**
```python
def get_s3_material_path(company_id: int, material_id: int, filename: str) -> str:
    """Generate S3 path for reference material"""
    return f"s3://kantan-ai-manual-generator/{company_id}/materials/{material_id}/{filename}"

def get_s3_pdf_path(company_id: int, manual_id: int, language_code: str, filename: str) -> str:
    """Generate S3 path for generated PDF"""
    return f"s3://kantan-ai-manual-generator/{company_id}/pdfs/{manual_id}/{language_code}/{filename}"

def get_s3_temp_path(company_id: int, job_id: int, filename: str) -> str:
    """Generate S3 path for temporary processing files"""
    return f"s3://kantan-ai-manual-generator/{company_id}/temp/{job_id}/{filename}"

def validate_company_access(user_company_id: int, s3_path: str) -> bool:
    """Verify user can only access their company's S3 paths"""
    expected_prefix = f"s3://kantan-ai-manual-generator/{user_company_id}/"
    return s3_path.startswith(expected_prefix)
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Database Schema**
- [ ] Create migration script for new tables
- [ ] Add new fields to existing tables
- [ ] Create database indexes
- [ ] Test schema with sample data

**Authentication & Authorization**
- [ ] Implement `@require_super_admin` decorator
- [ ] Enhance `require_role` for fine-grained permissions
- [ ] Add activity logging decorator
- [ ] Create super admin initialization script

**Test Endpoints (for verification):**
- `POST /api/test/create-super-admin` - Create initial super admin
- `GET /api/test/check-permissions` - Verify role-based access

**Deliverables:**
- Database migration scripts
- Enhanced auth middleware
- Super admin creation tool

---

### Phase 2: Super Admin Features (Week 3-4)

**Company Management**
- [ ] List/Search companies endpoint
- [ ] Create/Update/Delete company endpoints
- [ ] Company detail view with statistics
- [ ] Admin UI for company management

**User Management (All Companies)**
- [ ] List/Search all users endpoint
- [ ] Create/Update/Delete user endpoints
- [ ] Proxy login functionality
- [ ] Admin UI for user management

**Activity Logs**
- [ ] Activity logging middleware
- [ ] Log list/search endpoint with filters
- [ ] CSV export endpoint
- [ ] Admin UI for log viewing

**Test Endpoints:**
- `POST /api/test/admin/create-test-company` - Create test company
- `POST /api/test/admin/create-test-users` - Bulk create test users
- `POST /api/test/admin/generate-test-logs` - Generate sample activity logs
- `GET /api/test/admin/export-logs-sample` - Test CSV export

**Deliverables:**
- Super admin API endpoints (8 endpoints)
- Admin dashboard UI
- Activity logging system
- CSV export functionality

---

### Phase 3: Company Admin Features (Week 5)

**User Management (Own Company)**
- [ ] Company user CRUD endpoints
- [ ] User invitation email system (optional)
- [ ] Company admin UI for users

**Template Management**
- [ ] Template CRUD endpoints
- [ ] Template preview functionality
- [ ] Default template selection
- [ ] Template editor UI

**Test Endpoints:**
- `POST /api/test/company/create-test-template` - Create sample template
- `POST /api/test/company/bulk-create-templates` - Create multiple test templates
- `GET /api/test/company/validate-template` - Validate template JSON structure

**Deliverables:**
- Company admin API endpoints (8 endpoints)
- Template management UI
- User management UI (company-scoped)

---

### Phase 4: RAG System (Week 6-7)

**Infrastructure Setup**
- [ ] Deploy ElasticSearch cluster
- [ ] Configure vector search settings
- [ ] Set up index templates
- [ ] Test vector embeddings

**Reference Materials API**
- [ ] Upload material endpoint
- [ ] List/Search materials endpoint
- [ ] Material CRUD operations
- [ ] File validation and processing

**RAG Processing Pipeline**
- [ ] PDF text extraction (PyPDF2/pdfplumber)
- [ ] Word/Excel extraction (python-docx/openpyxl)
- [ ] Gemini metadata extraction
- [ ] Text chunking algorithm
- [ ] Vector embedding generation
- [ ] ElasticSearch indexing
- [ ] Async job management

**Semantic Search**
- [ ] Query embedding generation
- [ ] Hybrid search (vector + keyword)
- [ ] Relevance ranking
- [ ] Context retrieval for prompts

**Test Endpoints:**
- `POST /api/test/rag/upload-sample-material` - Upload test PDF
- `GET /api/test/rag/processing-status/{job_id}` - Check processing status
- `POST /api/test/rag/search` - Test semantic search
- `GET /api/test/rag/chunk-preview/{material_id}` - View chunks
- `POST /api/test/rag/reindex/{material_id}` - Force reindex for testing

**Deliverables:**
- ElasticSearch deployment
- RAG processing pipeline (async)
- Material management API (6 endpoints)
- Semantic search functionality

---

### Phase 5: Enhanced Manual Generation (Week 8)

**Template Integration**
- [ ] Get available templates endpoint
- [ ] Template selection in generation UI
- [ ] Multi-template generation
- [ ] Template override in request

**RAG-Enhanced Generation**
- [ ] Semantic search during generation
- [ ] Context injection into prompts
- [ ] Relevance scoring
- [ ] Source citation in output

**Batch Generation**
- [ ] Multiple template versions
- [ ] Async job tracking
- [ ] Progress notifications
- [ ] Error handling and retry

**Test Endpoints:**
- `POST /api/test/manuals/generate-with-template` - Test single template
- `POST /api/test/manuals/generate-multi-template` - Test multiple templates
- `POST /api/test/manuals/generate-with-rag` - Test RAG integration
- `GET /api/test/manuals/check-rag-sources/{manual_id}` - Verify RAG sources used

**Deliverables:**
- Enhanced manual generation API
- Multi-template generation
- RAG-integrated prompts
- Updated generation UI

---

### Phase 6: PDF Export (Week 9)

**PDF Generation Infrastructure**
- [ ] Install WeasyPrint
- [ ] Configure fonts and assets
- [ ] Create PDF templates (HTML/CSS)
- [ ] A4 page fitting algorithm

**PDF Generation Pipeline**
- [ ] HTML template rendering
- [ ] Image embedding
- [ ] Table of contents generation
- [ ] Page numbering
- [ ] Header/Footer customization

**API Endpoints**
- [ ] Generate PDF endpoint
- [ ] PDF status endpoint
- [ ] PDF download endpoint
- [ ] PDF regeneration

**Test Endpoints:**
- `POST /api/test/pdf/generate-sample` - Generate test PDF
- `GET /api/test/pdf/preview/{manual_id}` - Preview HTML before PDF
- `POST /api/test/pdf/test-a4-fitting` - Test A4 page fitting
- `GET /api/test/pdf/download-sample` - Download sample PDF

**Deliverables:**
- PDF generation pipeline (async)
- PDF API endpoints (4 endpoints)
- PDF download functionality
- A4-optimized templates

---

### Phase 7: Multi-language Translation (Week 10)

**Translation Infrastructure**
- [ ] Gemini translation setup
- [ ] Language code management
- [ ] Translation prompt templates
- [ ] Batch translation optimization

**Translation Pipeline**
- [ ] Content extraction
- [ ] Gemini translation API
- [ ] Formatting preservation
- [ ] Quality validation
- [ ] Async job processing

**API Endpoints**
- [ ] Translate manual endpoint
- [ ] Translation status endpoint
- [ ] Get translated manual endpoint
- [ ] List available languages

**UI Components**
- [ ] Language selector
- [ ] Translation progress display
- [ ] Translated content viewer

**Test Endpoints:**
- `POST /api/test/translate/single-language` - Test single language
- `POST /api/test/translate/multi-language` - Test batch translation
- `GET /api/test/translate/preview/{manual_id}/{lang}` - Preview translation
- `POST /api/test/translate/validate-formatting` - Verify format preservation

**Deliverables:**
- Translation pipeline (async)
- Translation API endpoints (4 endpoints)
- Multi-language UI
- Language management system

---

### Phase 8: Async Job Management & Monitoring (Week 11)

**Celery Setup**
- [ ] Install Celery + Redis
- [ ] Configure task queues
- [ ] Set up task routing
- [ ] Error handling and retry logic

**Job Monitoring**
- [ ] Install Flower (Celery monitoring)
- [ ] Job status API
- [ ] Progress tracking
- [ ] Job history

**UI Integration**
- [ ] Real-time progress updates (WebSocket/Polling)
- [ ] Job status notifications
- [ ] Error display and retry options

**Test Endpoints:**
- `POST /api/test/jobs/create-long-job` - Create long-running test job
- `GET /api/test/jobs/list-active` - List active jobs
- `POST /api/test/jobs/cancel/{job_id}` - Test job cancellation
- `GET /api/test/jobs/worker-status` - Check Celery worker status

**Deliverables:**
- Celery worker deployment
- Job management API (3 endpoints)
- Flower monitoring dashboard
- Real-time progress UI

---

### Phase 9: UI/UX Polish & Testing (Week 12)

**UI Components**
- [ ] Admin dashboard (super admin)
- [ ] Company dashboard (company admin)
- [ ] Material management UI
- [ ] Template editor
- [ ] Multi-language selector
- [ ] PDF preview/download

**End-to-End Testing**
- [ ] Super admin workflows
- [ ] Company admin workflows
- [ ] User workflows
- [ ] Cross-browser testing
- [ ] Mobile responsive testing

**Performance Optimization**
- [ ] Database query optimization
- [ ] API response caching
- [ ] Frontend lazy loading
- [ ] Image optimization

**Documentation**
- [ ] API documentation (Swagger/OpenAPI)
- [ ] User manual
- [ ] Admin guide
- [ ] Developer guide

**Test Endpoints:**
- `GET /api/test/ui/health-check` - System health check
- `POST /api/test/ui/load-test` - Simulate concurrent users
- `GET /api/test/ui/performance-metrics` - Get performance stats

**Deliverables:**
- Complete UI implementation
- End-to-end test suite
- Performance benchmarks
- Documentation package

---

## Testing Strategy

### API Testing Endpoints

Each phase includes dedicated test endpoints for:
- Feature verification
- Data generation (test companies, users, materials)
- Performance testing
- Error condition testing

### Test Account Setup

**Default Test Accounts** (use existing):
- Company: `career-survival`
- Super Admin: Create via test endpoint
- Company Admin: `support@career-survival.com` (role: admin)
- Regular User: Create additional via test endpoints

### Integration Testing

**RAG System Testing:**
1. Upload test PDFs with known content
2. Verify chunking and indexing
3. Test semantic search accuracy
4. Validate generation with RAG context

**Multi-template Testing:**
1. Create 3-5 test templates
2. Generate manual with all templates
3. Verify distinct outputs per template
4. Test custom template override

**Translation Testing:**
1. Generate manual in Japanese
2. Translate to EN, ZH, KO
3. Verify formatting preservation
4. Test PDF generation from translations

### Performance Testing

**Load Testing:**
- Concurrent uploads
- Simultaneous RAG indexing
- Batch PDF generation
- Heavy translation workloads

**Metrics to Track:**
- API response times
- Job processing duration
- ElasticSearch query performance
- PDF generation speed

---

## Deployment Considerations

### Infrastructure Requirements

**New Services:**
- ElasticSearch cluster (AWS OpenSearch Service or EC2)
- Redis instance (AWS ElastiCache)
- Celery workers (EC2 instances)
- S3 bucket for materials/PDFs

**Scaling:**
- Horizontal scaling for Celery workers
- ElasticSearch cluster scaling
- Redis replica for high availability

### Configuration Management

**Environment Variables:**
```bash
# ElasticSearch
ELASTICSEARCH_URL=https://...
ELASTICSEARCH_USERNAME=...
ELASTICSEARCH_PASSWORD=...

# Redis
REDIS_URL=redis://...

# Celery
CELERY_BROKER_URL=redis://...
CELERY_RESULT_BACKEND=redis://...

# AWS S3 (Unified bucket with tenant isolation)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET_NAME=kantan-ai-manual-generator
AWS_REGION=ap-northeast-1

# Translation
GEMINI_TRANSLATION_MODEL=gemini-2.0-flash-exp
```

### Migration Strategy

**Database Migration:**
1. Create backup of production database
2. Test migration on staging environment
3. Run migration during low-traffic period
4. Verify data integrity

**Rollout Plan:**
1. Deploy infrastructure (ElasticSearch, Redis)
2. Deploy Phase 1-2 (Super admin features)
3. Enable for internal testing
4. Deploy Phase 3-8 incrementally
5. Monitor performance and errors
6. Full production release

---

## Security Considerations

### Authentication & Authorization

- All endpoints require authentication
- Role-based access control strictly enforced
- Activity logging for audit trail
- Super admin proxy login with audit logging

### Data Protection

- Encrypt sensitive data at rest (S3, database)
- Use HTTPS for all API communications
- Sanitize user inputs
- Validate file uploads (type, size, content)

### Rate Limiting

- API rate limits per user/company
- Job queue limits to prevent abuse
- ElasticSearch query limits

---

## Success Metrics

### Phase Completion Criteria

Each phase considered complete when:
1. All endpoints functional and tested
2. Test endpoints verify core functionality
3. UI components implemented (if applicable)
4. Documentation updated
5. Performance benchmarks met

### Overall Success Metrics

- ✅ All 9 phases implemented
- ✅ 50+ API endpoints functional
- ✅ RAG system indexes materials in < 5 minutes
- ✅ PDF generation completes in < 30 seconds
- ✅ Translation accuracy > 95%
- ✅ System handles 100+ concurrent users
- ✅ Zero critical security vulnerabilities

---

## Conclusion

This specification provides a comprehensive blueprint for transforming the Manual Generator into an enterprise-grade SaaS platform. The phased approach ensures incremental value delivery while maintaining system stability.

**Next Steps:**
1. Review and approve this specification
2. Create detailed work breakdown for Phase 1
3. Set up development environment with new infrastructure
4. Begin implementation following the phase sequence

