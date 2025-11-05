"""
File: material_routes.py
Purpose: Reference materials management API for RAG system
Main functionality: Upload, list, update, delete reference materials with company isolation
Dependencies: Flask, S3Manager, authentication middleware
"""

from flask import Blueprint, request, jsonify, g
from flask_login import current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import mimetypes

from src.models.models import db, ReferenceMaterial, ProcessingJob
from src.infrastructure.s3_manager import s3_manager
from src.middleware.auth import require_role_enhanced, log_activity

material_bp = Blueprint('materials', __name__, url_prefix='/api/materials')

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'xlsx', 'xls', 'csv'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_type(filename: str) -> str:
    """Get standardized file type from filename"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    if ext in ['pdf']:
        return 'pdf'
    elif ext in ['docx', 'doc']:
        return 'docx'
    elif ext in ['xlsx', 'xls']:
        return 'xlsx'
    elif ext in ['csv']:
        return 'csv'
    else:
        return 'unknown'


@material_bp.route('', methods=['GET'])
@require_role_enhanced(['admin', 'user'])
@log_activity('list_materials', 'Listed reference materials', 'material')
def list_materials():
    """
    List reference materials for current company
    
    Query params:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)
        - file_type: Filter by file type (pdf, docx, xlsx, csv)
        - processing_status: Filter by status (pending, processing, completed, failed)
        - search: Search in title or filename
    """
    try:
        company_id = current_user.company_id
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Base query with company isolation
        query = ReferenceMaterial.query.filter_by(
            company_id=company_id,
            is_active=True
        )
        
        # Filters
        file_type = request.args.get('file_type')
        if file_type:
            query = query.filter_by(file_type=file_type)
        
        processing_status = request.args.get('processing_status')
        if processing_status:
            query = query.filter_by(processing_status=processing_status)
        
        search = request.args.get('search')
        if search:
            query = query.filter(
                db.or_(
                    ReferenceMaterial.title.ilike(f'%{search}%'),
                    ReferenceMaterial.original_filename.ilike(f'%{search}%')
                )
            )
        
        # Order by upload date (newest first)
        query = query.order_by(ReferenceMaterial.uploaded_at.desc())
        
        # Execute pagination
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'materials': [material.to_dict() for material in paginated.items],
            'total': paginated.total,
            'page': page,
            'per_page': per_page,
            'total_pages': paginated.pages
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to list materials: {str(e)}'}), 500


@material_bp.route('', methods=['POST'])
@require_role_enhanced(['admin', 'user'])
@log_activity('upload_material', 'Uploaded reference material', 'material')
def upload_material():
    """
    Upload reference material
    
    Content-Type: multipart/form-data
    Body:
        - file: File to upload (required)
        - title: Material title (required)
        - description: Material description (optional)
    """
    try:
        company_id = current_user.company_id
        user_id = current_user.id
        
        # Validate file
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Validate title
        title = request.form.get('title', '').strip()
        if not title:
            return jsonify({'error': 'Title is required'}), 400
        
        description = request.form.get('description', '').strip()
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({'error': f'File size exceeds maximum of {MAX_FILE_SIZE / (1024**2)}MB'}), 400
        
        # Create database record
        original_filename = secure_filename(file.filename)
        file_type = get_file_type(original_filename)
        
        # Generate unique stored filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        stored_filename = f"{timestamp}_{original_filename}"
        
        material = ReferenceMaterial(
            title=title,
            description=description,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_type=file_type,
            file_size=file_size,
            company_id=company_id,
            uploaded_by=user_id,
            processing_status='pending'
        )
        
        db.session.add(material)
        db.session.flush()  # Get material.id
        
        # Upload to S3
        s3_key = s3_manager.get_material_path(company_id, material.id, stored_filename)
        
        # Detect content type
        content_type, _ = mimetypes.guess_type(original_filename)
        if not content_type:
            content_type = 'application/octet-stream'
        
        print(f"DEBUG: Uploading to S3 key: {s3_key}")
        s3_uri = s3_manager.upload_file(file, s3_key, content_type)
        print(f"DEBUG: S3 URI returned: {s3_uri}")
        
        # Update material with S3 path
        material.file_path = s3_uri
        print(f"DEBUG: Material file_path set to: {material.file_path}")
        
        # Create processing job
        job = ProcessingJob(
            job_type='rag_index',
            job_status='pending',
            company_id=company_id,
            user_id=user_id,
            resource_type='reference_material',
            resource_id=material.id
        )
        
        db.session.add(job)
        db.session.commit()
        
        # Trigger async RAG processing task
        try:
            from src.workers.rag_tasks import process_material_task
            process_material_task.delay(material.id, job.id)
        except Exception as e:
            print(f"Warning: Failed to trigger async task: {e}")
            # Job will remain in 'pending' state
        
        return jsonify({
            'material': material.to_dict(),
            'job_id': job.id,
            'message': 'Material uploaded. Processing started.'
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


@material_bp.route('/<int:material_id>', methods=['GET'])
@require_role_enhanced(['admin', 'user'])
@log_activity('get_material', 'Retrieved material details', 'material', 'material_id')
def get_material(material_id):
    """
    Get material details
    
    Returns:
        Material details with download URL
    """
    try:
        company_id = current_user.company_id
        
        material = ReferenceMaterial.query.filter_by(
            id=material_id,
            company_id=company_id,
            is_active=True
        ).first()
        
        if not material:
            return jsonify({'error': 'Material not found'}), 404
        
        # Generate presigned URL for download
        s3_key = material.file_path.replace(f's3://{s3_manager.bucket_name}/', '')
        
        # Validate company access to this S3 key
        if not s3_manager.validate_company_access(company_id, s3_key):
            return jsonify({'error': 'Access denied'}), 403
        
        download_url = s3_manager.generate_presigned_url(s3_key, expiration=3600)
        
        result = material.to_dict()
        result['download_url'] = download_url
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to get material: {str(e)}'}), 500


@material_bp.route('/<int:material_id>/status', methods=['GET'])
@require_role_enhanced(['admin', 'user'])
def get_material_status(material_id):
    """
    Get material processing status
    
    Returns:
        Processing status and progress
    """
    try:
        company_id = current_user.company_id
        
        material = ReferenceMaterial.query.filter_by(
            id=material_id,
            company_id=company_id,
            is_active=True
        ).first()
        
        if not material:
            return jsonify({'error': 'Material not found'}), 404
        
        # Get latest processing job
        job = ProcessingJob.query.filter_by(
            resource_type='reference_material',
            resource_id=material_id
        ).order_by(ProcessingJob.created_at.desc()).first()
        
        return jsonify({
            'id': material.id,
            'processing_status': material.processing_status,
            'processing_progress': material.processing_progress,
            'error_message': material.error_message,
            'elasticsearch_indexed': material.elasticsearch_indexed,
            'chunk_count': material.chunk_count,
            'job': job.to_dict() if job else None
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Failed to get status: {str(e)}'}), 500


@material_bp.route('/<int:material_id>', methods=['PUT'])
@require_role_enhanced(['admin', 'user'])
@log_activity('update_material', 'Updated material metadata', 'material', 'material_id')
def update_material(material_id):
    """
    Update material metadata
    
    Body:
        - title: Material title (optional)
        - description: Material description (optional)
        - is_active: Active status (optional)
    """
    try:
        company_id = current_user.company_id
        
        material = ReferenceMaterial.query.filter_by(
            id=material_id,
            company_id=company_id
        ).first()
        
        if not material:
            return jsonify({'error': 'Material not found'}), 404
        
        data = request.get_json()
        
        # Update fields
        if 'title' in data:
            title = data['title'].strip()
            if not title:
                return jsonify({'error': 'Title cannot be empty'}), 400
            material.title = title
        
        if 'description' in data:
            material.description = data['description'].strip()
        
        if 'is_active' in data:
            material.is_active = bool(data['is_active'])
        
        db.session.commit()
        
        return jsonify({
            'material': material.to_dict(),
            'message': 'Material updated successfully'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Update failed: {str(e)}'}), 500


@material_bp.route('/<int:material_id>', methods=['DELETE'])
@require_role_enhanced(['admin', 'user'])
@log_activity('delete_material', 'Deleted reference material', 'material', 'material_id')
def delete_material(material_id):
    """
    Delete material (soft delete)
    
    Also removes from ElasticSearch index
    """
    try:
        company_id = current_user.company_id
        
        material = ReferenceMaterial.query.filter_by(
            id=material_id,
            company_id=company_id
        ).first()
        
        if not material:
            return jsonify({'error': 'Material not found'}), 404
        
        # Soft delete
        material.is_active = False
        
        # Remove from ElasticSearch
        try:
            from src.services.elasticsearch_service import elasticsearch_service
            elasticsearch_service.delete_material_chunks(material_id, company_id)
        except Exception as e:
            print(f"Warning: Failed to delete from ElasticSearch: {e}")
        
        # Optional: Delete from S3 (commented out for safety)
        # s3_key = material.file_path.replace(f's3://{s3_manager.bucket_name}/', '')
        # if s3_manager.validate_company_access(company_id, s3_key):
        #     s3_manager.delete_file(s3_key)
        
        db.session.commit()
        
        return jsonify({'message': 'Material deleted successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Delete failed: {str(e)}'}), 500
