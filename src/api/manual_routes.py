"""
File: manual_routes.py
Purpose: Enhanced manual generation API endpoints with template integration and RAG support
Main functionality: 
  - Template listing and selection
  - RAG-enhanced manual generation
  - Multi-template batch generation
Dependencies: Flask, models, RAGProcessor, ElasticSearchService, Gemini
"""

from flask import Blueprint, request, jsonify, session
from flask_login import current_user
from werkzeug.utils import secure_filename
from src.models.models import db, Manual, ManualTemplate, ReferenceMaterial, ProcessingJob, User, Company
from src.middleware.auth import require_role_enhanced, log_activity
from src.services.elasticsearch_service import elasticsearch_service
from src.services.rag_processor import rag_processor
from src.infrastructure.file_manager import FileManager
from datetime import datetime
import logging
import json
import os

logger = logging.getLogger(__name__)

manual_bp = Blueprint('manual_api', __name__, url_prefix='/api/manuals')

# Initialize file manager
file_manager = FileManager()

# Allowed video formats
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'webm', 'mkv', 'flv', 'wmv', 'mpeg', 'mpg', '3gp'}
MAX_VIDEO_SIZE = 10 * 1024 * 1024 * 1024  # 10GB


def allowed_video_file(filename: str) -> bool:
    """Check if file is an allowed video format"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS


@manual_bp.route('/upload-file', methods=['POST'])
@require_role_enhanced(['admin', 'user'])
@log_activity('upload_video', 'Uploaded video file for manual generation', 'manual')
def upload_video_file():
    """
    Upload video file to GCS for manual generation
    
    Form data:
        - file: Video file (required)
    
    Response: {
      "success": true,
      "gcs_uri": "gs://bucket/path/to/video.mp4",
      "file_name": "video.mp4",
      "file_size": 12345678,
      "content_type": "video/mp4"
    }
    """
    try:
        logger.info("=" * 80)
        logger.info("VIDEO UPLOAD REQUEST RECEIVED")
        logger.info("=" * 80)
        
        # Check if file is present
        logger.info(f"Request files: {list(request.files.keys())}")
        logger.info(f"Request form: {list(request.form.keys())}")
        
        if 'file' not in request.files:
            logger.error("No file in request.files")
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        logger.info(f"File object received: {file}")
        logger.info(f"Filename: {file.filename}")
        
        if file.filename == '':
            logger.error("Empty filename")
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file extension
        logger.info(f"Validating file extension for: {file.filename}")
        if not allowed_video_file(file.filename):
            logger.error(f"Invalid file type: {file.filename}")
            return jsonify({
                'error': 'Invalid file type',
                'allowed_formats': list(ALLOWED_VIDEO_EXTENSIONS)
            }), 400
        
        logger.info("File extension validated successfully")
        
        # Check file size (read first to get size)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        logger.info(f"File size: {file_size} bytes ({file_size / (1024*1024):.2f} MB)")
        
        if file_size > MAX_VIDEO_SIZE:
            logger.error(f"File too large: {file_size} > {MAX_VIDEO_SIZE}")
            return jsonify({
                'error': 'File too large',
                'max_size_gb': MAX_VIDEO_SIZE / (1024 * 1024 * 1024),
                'file_size_gb': file_size / (1024 * 1024 * 1024)
            }), 400
        
        # Secure filename
        filename = secure_filename(file.filename)
        company_id = current_user.company_id
        
        logger.info(f"Secure filename: {filename}")
        logger.info(f"Company ID: {company_id}")
        
        # Create folder path: company_{company_id}/videos
        folder = f'company_{company_id}/videos'
        
        # Upload using file manager
        logger.info(f"Uploading video: {filename} to folder: {folder}")
        logger.info(f"File manager storage type: {file_manager.storage_type}")
        
        result = file_manager.save_file(
            file_obj=file,
            filename=filename,
            file_type='video',
            folder=folder
        )
        
        logger.info(f"Upload result: {result}")
        
        if not result:
            logger.error("file_manager.save_file returned None or empty result")
            return jsonify({'error': 'Failed to upload file'}), 500
        
        # Construct GCS URI for compatibility
        # If using GCS backend, it will already be in the result
        # If using local, construct a file:// URI
        if file_manager.storage_type == 'gcs':
            gcs_uri = result.get('gcs_uri', result.get('file_path'))
        else:
            # For local storage, return the file path
            gcs_uri = result.get('full_path', result.get('file_path'))
        
        logger.info(f"Video uploaded successfully: {gcs_uri}")
        logger.info(f"Returning response with GCS URI: {gcs_uri}")
        
        response_data = {
            'success': True,
            'gcs_uri': gcs_uri,
            'uri': gcs_uri,  # For compatibility
            'file_name': filename,
            'file_size': file_size,
            'content_type': file.content_type or 'video/mp4'
        }
        
        logger.info(f"Response data: {response_data}")
        logger.info("=" * 80)
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error("VIDEO UPLOAD ERROR")
        logger.error("=" * 80)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        logger.error("=" * 80)
        
        return jsonify({
            'error': 'Failed to upload video file',
            'details': str(e)
        }), 500


@manual_bp.route('/templates', methods=['GET'])
@require_role_enhanced(['admin', 'user'])
@log_activity('list_templates', 'Listed available templates', 'template')
def get_available_templates():
    """
    Get available templates for manual generation
    
    Query params:
      - company_id (optional): Filter by company
      - include_default (optional, default=true): Include default templates
    
    Response: {
      "templates": [
        {
          "id": 1,
          "name": "Standard Manufacturing Manual",
          "description": "...",
          "template_content": {...},
          "is_default": true,
          "company_id": null,
          "created_at": "...",
          "updated_at": "..."
        }
      ],
      "count": 3
    }
    """
    try:
        # Get user's company_id from session
        user_company_id = session.get('company_id')
        
        if not user_company_id:
            return jsonify({
                'error': 'User not authenticated or no company association'
            }), 401
        
        # Build query
        query = ManualTemplate.query.filter_by(is_active=True)
        
        # Include default templates (company_id = null) and company-specific templates
        include_default = request.args.get('include_default', 'true').lower() == 'true'
        
        if include_default:
            query = query.filter(
                (ManualTemplate.company_id == user_company_id) | 
                (ManualTemplate.company_id == None)
            )
        else:
            query = query.filter_by(company_id=user_company_id)
        
        # Order by: default first, then by creation date
        templates = query.order_by(
            ManualTemplate.is_default.desc(),
            ManualTemplate.created_at.desc()
        ).all()
        
        return jsonify({
            'templates': [template.to_dict() for template in templates],
            'count': len(templates)
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get templates: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve templates',
            'details': str(e)
        }), 500



@manual_bp.route('/output-formats', methods=['GET'])
@require_role_enhanced(['admin', 'user'])
@log_activity('list_output_formats', 'Listed available output formats', 'manual')
def get_output_formats():
    """
    Get available output formats for manual generation
    
    Response: {
      "formats": [
        {
          "key": "text_with_images",
          "name": "テキスト + 画像",
          "name_en": "Text with Images",
          "description": "テキストに画像切り抜きを挿入",
          "description_en": "Text manual with image snapshots",
          "use_case": "現場作業者向け",
          "icon": "🖼️",
          "recommended": true,
          "features": {...}
        }
      ],
      "count": 5
    }
    """
    try:
        from src.config.output_formats import get_format_list
        
        formats = get_format_list()
        
        return jsonify({
            'formats': formats,
            'count': len(formats)
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get output formats: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve output formats',
            'details': str(e)
        }), 500


@manual_bp.route('/<int:manual_id>/convert', methods=['POST'])
@require_role_enhanced(['admin', 'user'])
@log_activity('convert_manual_format', 'Converted manual to different format', 'manual')
def convert_manual_format(manual_id):
    """
    Convert existing manual to different output format
    
    Request: {
      "target_format": "text_with_video_clips",
      "regenerate_analysis": false,
      "custom_prompt": "..."
    }
    
    Response: {
      "status": "success",
      "manual_id": 123,
      "new_format": "text_with_video_clips",
      "job_id": 456
    }
    """
    try:
        data = request.json
        
        # Get manual
        manual = Manual.query.get_or_404(manual_id)
        
        # Check permission
        user_id = session.get('user_id')
        company_id = session.get('company_id')
        
        if manual.company_id != company_id:
            return jsonify({'error': 'No permission to access this manual'}), 403
        
        # Validate target format
        from src.config.output_formats import is_valid_format, get_default_format
        
        target_format = data.get('target_format')
        if not target_format or not is_valid_format(target_format):
            return jsonify({
                'error': 'Invalid target format',
                'details': f'Format "{target_format}" is not supported'
            }), 400
        
        regenerate = data.get('regenerate_analysis', False)
        custom_prompt = data.get('custom_prompt')
        
        # Create processing job for conversion
        job = ProcessingJob(
            job_type='manual_format_conversion',
            job_status='pending',
            company_id=company_id,
            user_id=user_id,
            resource_type='manual',
            resource_id=manual.id,
            job_params=json.dumps({
                'target_format': target_format,
                'regenerate_analysis': regenerate,
                'custom_prompt': custom_prompt,
                'source_format': manual.output_format
            }),
            created_at=datetime.utcnow()
        )
        
        db.session.add(job)
        db.session.flush()
        
        # Update manual status
        manual.generation_status = 'pending'
        manual.generation_progress = 0
        
        db.session.commit()
        
        # Trigger async processing
        try:
            from src.workers.manual_tasks import process_manual_conversion_task
            process_manual_conversion_task.delay(job.id)
            logger.info(f"Triggered format conversion for manual {manual_id} to {target_format}")
        except Exception as task_error:
            logger.error(f"Failed to trigger async conversion task: {str(task_error)}")
            # Job will remain in 'pending' status for manual retry
        
        return jsonify({
            'status': 'success',
            'manual_id': manual.id,
            'new_format': target_format,
            'job_id': job.id,
            'message': f'Format conversion to {target_format} started'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Manual format conversion failed: {str(e)}")
        return jsonify({
            'error': 'Format conversion failed',
            'details': str(e)
        }), 500


@manual_bp.route('/generate', methods=['POST'])
@require_role_enhanced(['admin', 'user'])
@log_activity('generate_manual', 'Generated manual with RAG', 'manual')
def generate_manual_with_rag():
    """
    Generate manual(s) with template integration and RAG enhancement
    
    Request body: {
      "title": "Assembly Process Manual",
      "video_uri": "gs://...",
      "output_format": "text_with_images",  # NEW: text_only, text_with_images, text_with_video_clips, subtitle_video, hybrid
      "template_ids": [1, 2, 3],  # Optional: Generate with multiple templates
      "template_override": {...},  # Optional: Custom template content override
      "use_rag": true,  # Optional: Enable RAG search (default: true)
      "rag_query": "safety procedures",  # Optional: Custom RAG query
      "max_rag_results": 5,  # Optional: Number of RAG results to include (default: 5)
      "custom_prompt": "..."  # NEW: Optional custom prompt override
    }
    
    Response: {
      "manuals": [
        {
          "id": 101,
          "title": "Assembly Process Manual - Standard Manufacturing",
          "template_id": 1,
          "output_format": "text_with_images",
          "status": "processing",
          "job_id": 42
        }
      ],
      "message": "Manual generation started for 3 templates"
    }
    """
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('title'):
            return jsonify({'error': 'Title is required'}), 400
        
        if not data.get('video_uri'):
            return jsonify({'error': 'Video URI is required'}), 400
        
        # Validate output format
        from src.config.output_formats import is_valid_format, get_default_format
        
        output_format = data.get('output_format', get_default_format())
        if not is_valid_format(output_format):
            return jsonify({
                'error': 'Invalid output format',
                'details': f'Format "{output_format}" is not supported'
            }), 400
        
        # Get user info from current_user (Flask-Login)
        if not current_user.is_authenticated:
            logger.error("User not authenticated")
            return jsonify({'error': 'User not authenticated'}), 401
        
        user_id = current_user.id
        company_id = current_user.company_id
        
        logger.info(f"Authenticated user: ID={user_id}, Company={company_id}")
        
        # Get template IDs (default to all active templates if not specified)
        template_ids = data.get('template_ids', [])
        
        if not template_ids:
            # Use default template or company's default template
            default_template = ManualTemplate.query.filter(
                (ManualTemplate.company_id == company_id) | (ManualTemplate.company_id == None),
                ManualTemplate.is_default == True,
                ManualTemplate.is_active == True
            ).first()
            
            if default_template:
                template_ids = [default_template.id]
            else:
                return jsonify({
                    'error': 'No templates specified and no default template found'
                }), 400
        
        # Validate templates
        templates = ManualTemplate.query.filter(
            ManualTemplate.id.in_(template_ids),
            ManualTemplate.is_active == True
        ).all()
        
        if len(templates) != len(template_ids):
            return jsonify({
                'error': 'One or more invalid template IDs'
            }), 400
        
        # Check template access permissions
        for template in templates:
            if template.company_id and template.company_id != company_id:
                return jsonify({
                    'error': f'No permission to use template {template.id}'
                }), 403
        
        # RAG enhancement
        use_rag = data.get('use_rag', True)
        rag_context = None
        
        logger.info("=" * 80)
        logger.info("MANUAL GENERATION REQUEST")
        logger.info("=" * 80)
        logger.info(f"Title: {data.get('title')}")
        logger.info(f"Video URI: {data.get('video_uri')}")
        logger.info(f"Output format: {output_format}")
        logger.info(f"Use RAG: {use_rag}")
        logger.info(f"Template IDs: {template_ids}")
        logger.info(f"Company ID: {company_id}")
        logger.info(f"User ID: {user_id}")
        
        if use_rag:
            try:
                # Perform semantic search
                rag_query = data.get('rag_query') or data.get('title')
                max_results = data.get('max_rag_results', 5)
                
                logger.info(f"Performing RAG search for: {rag_query}")
                
                # Generate query embedding using Gemini
                from src.services.gemini_service import GeminiUnifiedService
                gemini_service = GeminiUnifiedService()
                
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    query_embedding = loop.run_until_complete(
                        gemini_service.generate_embedding(rag_query)
                    )
                finally:
                    loop.close()
                
                # Use hybrid search (vector + keyword)
                search_results = elasticsearch_service.hybrid_search(
                    query_text=rag_query,
                    query_embedding=query_embedding,
                    company_id=company_id,
                    top_k=max_results
                )
                
                if search_results:
                    # Format RAG context for prompt injection
                    rag_context = {
                        'reference_materials': [],
                        'total_results': len(search_results)
                    }
                    
                    for result in search_results:
                        rag_context['reference_materials'].append({
                            'material_id': result.get('material_id'),
                            'material_title': result.get('material_title'),
                            'chunk_text': result.get('chunk_text'),
                            'relevance_score': result.get('score'),
                            'metadata': result.get('metadata', {})
                        })
                    
                    logger.info(f"RAG search found {len(search_results)} relevant chunks")
                else:
                    logger.warning("RAG search returned no results")
                    
            except Exception as rag_error:
                logger.error(f"RAG search failed: {str(rag_error)}")
                # Continue without RAG context
                rag_context = None
        
        # Create manuals for each template
        created_manuals = []
        
        for template in templates:
            # Get template content (may be JSON string or dict)
            template_content = template.template_content
            if isinstance(template_content, str):
                try:
                    template_content = json.loads(template_content)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse template_content for template {template.id}")
                    template_content = {}
            
            # Merge template with override if provided
            if data.get('template_override'):
                template_content = {**template_content, **data['template_override']}
            
            # Create manual record
            manual = Manual(
                title=f"{data['title']} - {template.name}",
                company_id=company_id,
                created_by=user_id,
                video_uri=data['video_uri'],
                template_id=template.id,
                output_format=output_format,
                generation_status='pending',
                content='',  # Initialize with empty string to satisfy NOT NULL constraint
                created_at=datetime.utcnow()
            )
            
            # Set generation options
            manual.set_generation_options({
                'custom_prompt': data.get('custom_prompt'),
                'detail_level': template_content.get('content_structure', {}).get('detail_level', 'normal'),
                'writing_style': template_content.get('content_structure', {}).get('writing_style', 'formal'),
                'sections': template_content.get('content_structure', {}).get('sections', [])
            })
            
            db.session.add(manual)
            db.session.flush()  # Get manual.id
            
            # Create processing job
            job = ProcessingJob(
                job_type='manual_generation',
                job_status='pending',
                company_id=company_id,
                user_id=user_id,
                resource_type='manual',
                resource_id=manual.id,
                job_params=json.dumps({
                    'video_uri': data['video_uri'],
                    'output_format': output_format,
                    'template_content': template_content,
                    'rag_context': rag_context,
                    'use_rag': use_rag,
                    'custom_prompt': data.get('custom_prompt')
                }),
                created_at=datetime.utcnow()
            )
            
            db.session.add(job)
            db.session.flush()
            
            # Update manual with job_id
            manual.processing_job_id = job.id
            
            created_manuals.append({
                'id': manual.id,
                'title': manual.title,
                'template_id': template.id,
                'template_name': template.name,
                'output_format': output_format,
                'status': manual.generation_status,
                'job_id': job.id
            })
        
        db.session.commit()
        
        # Trigger async processing (import here to avoid circular dependency)
        try:
            from src.workers.manual_tasks import process_manual_generation_task
            
            for manual_info in created_manuals:
                process_manual_generation_task.delay(manual_info['job_id'])
                logger.info(f"Triggered async generation for manual {manual_info['id']}")
                
        except Exception as task_error:
            logger.error(f"Failed to trigger async task: {str(task_error)}")
            # Manual will remain in 'pending' status for manual retry
        
        return jsonify({
            'manuals': created_manuals,
            'message': f"Manual generation started for {len(created_manuals)} template(s)",
            'rag_enabled': use_rag,
            'rag_results_count': len(rag_context['reference_materials']) if rag_context else 0
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Manual generation failed: {str(e)}")
        return jsonify({
            'error': 'Manual generation failed',
            'details': str(e)
        }), 500


@manual_bp.route('/<int:manual_id>/status', methods=['GET'])
@require_role_enhanced(['admin', 'user'])
def get_manual_generation_status(manual_id):
    """
    Get manual generation status
    
    Response: {
      "id": 101,
      "title": "...",
      "status": "processing",
      "progress": 45,
      "job_id": 42,
      "job_status": "processing",
      "current_step": "Extracting key frames",
      "created_at": "...",
      "started_at": "...",
      "completed_at": null
    }
    """
    try:
        company_id = session.get('company_id')
        
        manual = Manual.query.filter_by(
            id=manual_id,
            company_id=company_id
        ).first()
        
        if not manual:
            return jsonify({'error': 'Manual not found'}), 404
        
        # Get associated job if exists
        job = None
        if hasattr(manual, 'processing_job_id') and manual.processing_job_id:
            job = ProcessingJob.query.get(manual.processing_job_id)
        
        response = {
            'id': manual.id,
            'title': manual.title,
            'status': manual.generation_status,
            'created_at': manual.created_at.isoformat() if manual.created_at else None,
        }
        
        if job:
            response.update({
                'job_id': job.id,
                'job_status': job.job_status,
                'progress': job.progress,
                'current_step': job.current_step,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'error_message': job.error_message
            })
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Failed to get manual status: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve manual status',
            'details': str(e)
        }), 500
