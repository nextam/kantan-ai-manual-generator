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
from src.models.models import db, Manual, ManualTemplate, ReferenceMaterial, ProcessingJob, User, Company
from src.middleware.auth import require_role_enhanced, log_activity
from src.services.elasticsearch_service import elasticsearch_service
from src.services.rag_processor import rag_processor
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

manual_bp = Blueprint('manual_api', __name__, url_prefix='/api/manuals')


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


@manual_bp.route('/generate', methods=['POST'])
@require_role_enhanced(['admin', 'user'])
@log_activity('generate_manual', 'Generated manual with RAG', 'manual')
def generate_manual_with_rag():
    """
    Generate manual(s) with template integration and RAG enhancement
    
    Request body: {
      "title": "Assembly Process Manual",
      "video_uri": "gs://...",
      "template_ids": [1, 2, 3],  # Optional: Generate with multiple templates
      "template_override": {...},  # Optional: Custom template content override
      "use_rag": true,  # Optional: Enable RAG search (default: true)
      "rag_query": "safety procedures",  # Optional: Custom RAG query
      "max_rag_results": 5  # Optional: Number of RAG results to include (default: 5)
    }
    
    Response: {
      "manuals": [
        {
          "id": 101,
          "title": "Assembly Process Manual - Standard Manufacturing",
          "template_id": 1,
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
        
        # Get user info
        user_id = session.get('user_id')
        company_id = session.get('company_id')
        
        if not user_id or not company_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
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
        
        if use_rag:
            try:
                # Perform semantic search
                rag_query = data.get('rag_query') or data.get('title')
                max_results = data.get('max_rag_results', 5)
                
                logger.info(f"Performing RAG search for: {rag_query}")
                
                # Use hybrid search (vector + keyword)
                search_results = elasticsearch_service.hybrid_search(
                    query_text=rag_query,
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
            # Merge template with override if provided
            template_content = template.template_content
            if data.get('template_override'):
                template_content = {**template_content, **data['template_override']}
            
            # Create manual record
            manual = Manual(
                title=f"{data['title']} - {template.name}",
                company_id=company_id,
                created_by=user_id,
                video_uri=data['video_uri'],
                template_id=template.id,
                generation_status='pending',
                created_at=datetime.utcnow()
            )
            
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
                    'template_content': template_content,
                    'rag_context': rag_context,
                    'use_rag': use_rag
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
