"""
File: job_routes.py
Purpose: API endpoints for async job management and monitoring
Main functionality: Get job status, list jobs, cancel jobs
Dependencies: Flask, celery, models
"""

from flask import Blueprint, request, jsonify, session
from src.workers.celery_app import celery
from src.models.models import db, ProcessingJob
from src.middleware.auth import require_authentication
from celery.result import AsyncResult
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)

job_bp = Blueprint('jobs', __name__, url_prefix='/api/jobs')


@job_bp.route('', methods=['GET'])
@require_authentication
def list_all_jobs():
    """
    List all processing jobs for the current company
    
    GET /api/jobs?page=1&per_page=20&status=all&job_type=manual_generation
    
    Query params:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)
        - status: Filter by status (pending, processing, completed, failed, all)
        - job_type: Filter by job type (manual_generation, pdf_generation, translation, etc.)
    
    Response: {
        "jobs": [
            {
                "id": 1,
                "job_type": "manual_generation",
                "job_status": "processing",
                "progress": 50,
                "resource_type": "manual",
                "resource_id": 123,
                "created_at": "2025-01-05T10:30:00",
                "started_at": "2025-01-05T10:30:05",
                "completed_at": null,
                "current_step": "Extracting key frames"
            }
        ],
        "total": 10,
        "page": 1,
        "per_page": 20,
        "pages": 1
    }
    """
    try:
        company_id = session.get('company_id')
        if not company_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Base query with company isolation
        query = ProcessingJob.query.filter_by(company_id=company_id)
        
        # Status filter
        status = request.args.get('status', '').strip()
        if status and status != 'all':
            query = query.filter_by(job_status=status)
        
        # Job type filter
        job_type = request.args.get('job_type', '').strip()
        if job_type:
            query = query.filter_by(job_type=job_type)
        
        # Order by creation date (newest first)
        query = query.order_by(ProcessingJob.created_at.desc())
        
        # Execute pagination
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        jobs = []
        for job in paginated.items:
            jobs.append({
                'id': job.id,
                'job_type': job.job_type,
                'job_status': job.job_status,
                'progress': job.progress,
                'resource_type': job.resource_type,
                'resource_id': job.resource_id,
                'current_step': job.current_step,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'error_message': job.error_message
            })
        
        return jsonify({
            'jobs': jobs,
            'total': paginated.total,
            'page': page,
            'per_page': per_page,
            'pages': paginated.pages
        }), 200
        
    except Exception as e:
        logger.error(f"Error in list_all_jobs: {str(e)}")
        return jsonify({'error': str(e)}), 500


@job_bp.route('/<task_id>', methods=['GET'])
@require_authentication
def get_job_status(task_id):
    """
    Get job status by Celery task ID
    
    GET /api/jobs/{task_id}
    
    Response: {
        "task_id": "abc123...",
        "state": "PROGRESS",
        "current": 50,
        "total": 100,
        "status": "Processing...",
        "result": null
    }
    """
    try:
        company_id = session.get('company_id')
        if not company_id:
            return {'error': 'Not authenticated'}, 401
        
        # Get task result from Celery
        task = AsyncResult(task_id, app=celery)
        
        response = {
            'task_id': task_id,
            'state': task.state,
            'result': None
        }
        
        if task.state == 'PENDING':
            response.update({
                'status': 'Waiting for worker...',
                'current': 0,
                'total': 100
            })
        elif task.state == 'PROGRESS':
            # Task is in progress
            info = task.info or {}
            response.update({
                'current': info.get('current', 0),
                'total': info.get('total', 100),
                'status': info.get('status', 'Processing...')
            })
        elif task.state == 'SUCCESS':
            # Task completed successfully
            response.update({
                'status': 'Completed',
                'current': 100,
                'total': 100,
                'result': task.result
            })
        elif task.state == 'FAILURE':
            # Task failed
            response.update({
                'status': 'Failed',
                'error': str(task.info)
            })
        else:
            # Other states (RETRY, REVOKED, etc.)
            response.update({
                'status': task.state
            })
        
        return response, 200
        
    except Exception as e:
        logger.error(f"Error in get_job_status: {str(e)}")
        return {'error': str(e)}, 500


# Legacy /api/jobs/processing removed - use /api/jobs with status=processing filter instead
# Legacy /api/jobs/<task_id>/cancel removed - not implemented yet
# Legacy /api/jobs/statistics removed - not implemented yet  
# Legacy /api/jobs/worker-status removed - not implemented yet
