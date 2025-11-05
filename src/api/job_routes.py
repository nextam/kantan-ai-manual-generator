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


@job_bp.route('/processing', methods=['GET'])
@require_authentication
def list_processing_jobs():
    """
    List processing jobs for the current company
    
    GET /api/jobs/processing?page=1&per_page=20&job_type=pdf_generation
    
    Response: {
        "jobs": [
            {
                "id": 1,
                "job_type": "pdf_generation",
                "job_status": "processing",
                "progress": 50,
                "created_at": "2025-01-05T10:30:00"
            }
        ],
        "total": 10,
        "page": 1,
        "per_page": 20
    }
    """
    try:
        company_id = session.get('company_id')
        if not company_id:
            return {'error': 'Not authenticated'}, 401
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        job_type = request.args.get('job_type')
        job_status = request.args.get('job_status')
        
        # Build query
        query = ProcessingJob.query.filter_by(company_id=company_id)
        
        if job_type:
            query = query.filter_by(job_type=job_type)
        
        if job_status:
            query = query.filter_by(job_status=job_status)
        
        # Order by creation date (newest first)
        query = query.order_by(ProcessingJob.created_at.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        jobs = [job.to_dict() for job in pagination.items]
        
        return {
            'jobs': jobs,
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }, 200
        
    except Exception as e:
        logger.error(f"Error in list_processing_jobs: {str(e)}")
        return {'error': str(e)}, 500


@job_bp.route('/<task_id>/cancel', methods=['POST'])
@require_authentication
def cancel_job(task_id):
    """
    Cancel a running job
    
    POST /api/jobs/{task_id}/cancel
    
    Response: {
        "message": "Job cancelled successfully",
        "task_id": "abc123..."
    }
    """
    try:
        company_id = session.get('company_id')
        if not company_id:
            return {'error': 'Not authenticated'}, 401
        
        # Revoke task in Celery
        celery.control.revoke(task_id, terminate=True)
        
        # Update ProcessingJob record if exists
        job = ProcessingJob.query.filter_by(
            company_id=company_id
        ).filter(
            ProcessingJob.job_params.contains(task_id)
        ).first()
        
        if job:
            job.job_status = 'cancelled'
            db.session.commit()
        
        return {
            'message': 'Job cancelled successfully',
            'task_id': task_id
        }, 200
        
    except Exception as e:
        logger.error(f"Error in cancel_job: {str(e)}")
        return {'error': str(e)}, 500


@job_bp.route('/statistics', methods=['GET'])
@require_authentication
def get_job_statistics():
    """
    Get job statistics for the current company
    
    GET /api/jobs/statistics?days=7
    
    Response: {
        "total_jobs": 100,
        "pending": 5,
        "processing": 10,
        "completed": 80,
        "failed": 5,
        "by_type": {
            "pdf_generation": 30,
            "translation": 40,
            "rag_indexing": 30
        }
    }
    """
    try:
        company_id = session.get('company_id')
        if not company_id:
            return {'error': 'Not authenticated'}, 401
        
        # Get days parameter
        days = request.args.get('days', 7, type=int)
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get job counts
        query = ProcessingJob.query.filter(
            ProcessingJob.company_id == company_id,
            ProcessingJob.created_at >= cutoff_date
        )
        
        total_jobs = query.count()
        
        # Count by status
        pending = query.filter_by(job_status='pending').count()
        processing = query.filter_by(job_status='processing').count()
        completed = query.filter_by(job_status='completed').count()
        failed = query.filter_by(job_status='failed').count()
        
        # Count by type
        job_types = db.session.query(
            ProcessingJob.job_type,
            db.func.count(ProcessingJob.id)
        ).filter(
            ProcessingJob.company_id == company_id,
            ProcessingJob.created_at >= cutoff_date
        ).group_by(ProcessingJob.job_type).all()
        
        by_type = {job_type: count for job_type, count in job_types}
        
        return {
            'total_jobs': total_jobs,
            'pending': pending,
            'processing': processing,
            'completed': completed,
            'failed': failed,
            'by_type': by_type,
            'period_days': days
        }, 200
        
    except Exception as e:
        logger.error(f"Error in get_job_statistics: {str(e)}")
        return {'error': str(e)}, 500


@job_bp.route('/worker-status', methods=['GET'])
@require_authentication
def get_worker_status():
    """
    Get Celery worker status
    
    GET /api/jobs/worker-status
    
    Response: {
        "workers": {
            "celery@worker1": {
                "status": "online",
                "active_tasks": 2,
                "total_tasks": 150
            }
        },
        "active_queues": ["default", "rag_processing", "pdf_generation"]
    }
    """
    try:
        company_id = session.get('company_id')
        if not company_id:
            return {'error': 'Not authenticated'}, 401
        
        # Only super admin or admin can view worker status
        user_role = session.get('user_role')
        if user_role not in ['admin', 'super_admin']:
            return {'error': 'Insufficient permissions'}, 403
        
        # Get worker stats
        inspect = celery.control.inspect()
        
        # Get active workers
        stats = inspect.stats() or {}
        active_tasks = inspect.active() or {}
        
        workers = {}
        for worker_name, worker_stats in stats.items():
            workers[worker_name] = {
                'status': 'online',
                'active_tasks': len(active_tasks.get(worker_name, [])),
                'total_tasks': worker_stats.get('total', {}).get('tasks', 0)
            }
        
        # Get active queues
        active_queues = list(set(
            task.get('delivery_info', {}).get('routing_key', 'default')
            for tasks in active_tasks.values()
            for task in tasks
        ))
        
        return {
            'workers': workers,
            'active_queues': active_queues,
            'total_workers': len(workers)
        }, 200
        
    except Exception as e:
        logger.error(f"Error in get_worker_status: {str(e)}")
        return {'error': str(e)}, 500
