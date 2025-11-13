"""
File: celery_app.py
Purpose: Celery configuration for async task processing
Main functionality: Celery app initialization, Redis connection, task routing
Dependencies: celery, redis
"""

import os
import logging
from datetime import datetime
from celery import Celery
from celery.signals import after_setup_logger, after_setup_task_logger
from kombu import Queue


def make_celery(app_name='manual_generator'):
    """
    Create and configure Celery application
    
    Configuration:
    - Redis as message broker
    - Redis as result backend
    - JSON serialization for security
    - Task routing to specific queues
    """
    
    # Redis URLs
    broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
    result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')
    
    # Create Celery app
    celery_app = Celery(
        app_name,
        broker=broker_url,
        backend=result_backend,
        include=[
            'src.workers.rag_tasks',
            'src.workers.manual_tasks'  # Add manual tasks module
        ]
    )
    
    # Configuration
    celery_app.conf.update(
        # Result settings
        result_expires=3600,  # Results expire after 1 hour
        result_persistent=True,  # Store results persistently
        
        # Task settings
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        timezone='UTC',
        enable_utc=True,
        
        # Task execution settings
        task_track_started=True,  # Track when tasks start
        task_time_limit=3600,  # 1 hour hard limit
        task_soft_time_limit=3000,  # 50 minutes soft limit
        
        # Worker settings
        worker_prefetch_multiplier=1,  # One task at a time
        worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
        
        # Queue settings
        task_default_queue='default',
        task_queues=(
            Queue('default', routing_key='task.#'),
            Queue('rag_processing', routing_key='rag.#'),
            Queue('pdf_generation', routing_key='pdf.#'),
            Queue('translation', routing_key='translation.#'),
        ),
        
        # Task routing
        task_routes={
            'src.workers.rag_tasks.process_material_task': {
                'queue': 'rag_processing',
                'routing_key': 'rag.process_material'
            },
            'src.workers.rag_tasks.reindex_material_task': {
                'queue': 'rag_processing',
                'routing_key': 'rag.reindex'
            }
        },
        
        # Error handling
        task_reject_on_worker_lost=True,
        task_acks_late=True,  # Acknowledge after task completion
        
        # Retry settings
        task_default_retry_delay=60,  # 1 minute
        task_max_retries=3
    )
    
    return celery_app


# Create global Celery instance
celery = make_celery()


# Automatically push Flask app context for all tasks
@celery.task(bind=True, name='celery.ping')
def ping_task(self):
    """Health check task"""
    return 'pong'


# Setup Flask app context for all Celery tasks
from celery.signals import task_prerun, task_postrun

@task_prerun.connect
def setup_app_context(sender=None, **kwargs):
    """Push Flask app context before task execution"""
    from src.core.app import app
    app.app_context().push()


@task_postrun.connect
def teardown_app_context(sender=None, **kwargs):
    """Pop Flask app context after task execution"""
    from flask import g
    from src.models.models import db
    # Cleanup database session
    db.session.remove()


# Configure Celery logging to use same timestamped log file as Flask
@after_setup_logger.connect
def setup_celery_logger(logger, *args, **kwargs):
    """Configure Celery worker logger to use same log file as Flask"""
    log_dir = os.getenv('LOG_DIR', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_timestamp = os.getenv('LOG_TIMESTAMP', datetime.now().strftime('%Y%m%d_%H%M%S'))
    log_file_path = os.path.join(log_dir, f'app_{log_timestamp}.log')
    
    # Add file handler to Celery logger
    handler = logging.FileHandler(log_file_path)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)


@after_setup_task_logger.connect
def setup_celery_task_logger(logger, *args, **kwargs):
    """Configure Celery task logger to use same log file as Flask"""
    log_dir = os.getenv('LOG_DIR', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_timestamp = os.getenv('LOG_TIMESTAMP', datetime.now().strftime('%Y%m%d_%H%M%S'))
    log_file_path = os.path.join(log_dir, f'app_{log_timestamp}.log')
    
    # Add file handler to task logger
    handler = logging.FileHandler(log_file_path)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)


# Optional: Flask integration
def init_celery(app=None):
    """
    Initialize Celery with Flask app context
    
    This allows Celery tasks to access Flask app context
    """
    if app is None:
        return celery
    
    celery.conf.update(app.config)
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery
