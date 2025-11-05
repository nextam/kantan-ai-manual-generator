"""
File: test_ui_phase9.py
Purpose: Phase 9 UI/UX test endpoints for comprehensive testing
Main functionality: Health check, load testing, performance metrics
Dependencies: Flask, models
"""

from flask import Blueprint, jsonify, request
from src.models.models import db, Manual, User, Company
from datetime import datetime
import psutil
import time

test_ui_bp = Blueprint('test_ui', __name__, url_prefix='/api/test/ui')


@test_ui_bp.route('/health-check', methods=['GET'])
def health_check():
    """
    System health check endpoint
    Returns overall system health status
    """
    try:
        health_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'healthy',
            'checks': {}
        }
        
        # Database check
        try:
            db.session.execute('SELECT 1')
            health_status['checks']['database'] = {
                'status': 'ok',
                'message': 'Database connection successful'
            }
        except Exception as e:
            health_status['checks']['database'] = {
                'status': 'error',
                'message': str(e)
            }
            health_status['status'] = 'unhealthy'
        
        # Memory check
        memory = psutil.virtual_memory()
        health_status['checks']['memory'] = {
            'status': 'ok' if memory.percent < 90 else 'warning',
            'usage_percent': memory.percent,
            'available_mb': memory.available / (1024 * 1024)
        }
        
        # CPU check
        cpu_percent = psutil.cpu_percent(interval=1)
        health_status['checks']['cpu'] = {
            'status': 'ok' if cpu_percent < 80 else 'warning',
            'usage_percent': cpu_percent
        }
        
        # Count records
        health_status['checks']['data_counts'] = {
            'companies': Company.query.count(),
            'users': User.query.count(),
            'manuals': Manual.query.count()
        }
        
        return jsonify(health_status), 200
        
    except Exception as e:
        return jsonify({
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'error',
            'error': str(e)
        }), 500


@test_ui_bp.route('/load-test', methods=['POST'])
def load_test():
    """
    Simulate concurrent users for load testing
    """
    data = request.json
    concurrent_users = data.get('concurrent_users', 10)
    duration_seconds = data.get('duration_seconds', 60)
    
    # Note: This is a placeholder for actual load testing
    # Real implementation would use tools like Locust or Apache JMeter
    
    return jsonify({
        'message': 'Load test configuration received',
        'config': {
            'concurrent_users': concurrent_users,
            'duration_seconds': duration_seconds
        },
        'note': 'Use external tools (Locust, JMeter) for actual load testing',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@test_ui_bp.route('/performance-metrics', methods=['GET'])
def performance_metrics():
    """
    Get current performance metrics
    """
    try:
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'system': {
                'cpu': {
                    'usage_percent': psutil.cpu_percent(interval=1),
                    'count': psutil.cpu_count()
                },
                'memory': {
                    'total_mb': psutil.virtual_memory().total / (1024 * 1024),
                    'available_mb': psutil.virtual_memory().available / (1024 * 1024),
                    'used_mb': psutil.virtual_memory().used / (1024 * 1024),
                    'percent': psutil.virtual_memory().percent
                },
                'disk': {
                    'total_gb': psutil.disk_usage('/').total / (1024 * 1024 * 1024),
                    'used_gb': psutil.disk_usage('/').used / (1024 * 1024 * 1024),
                    'free_gb': psutil.disk_usage('/').free / (1024 * 1024 * 1024),
                    'percent': psutil.disk_usage('/').percent
                }
            },
            'database': {
                'companies': Company.query.count(),
                'users': User.query.count(),
                'manuals': Manual.query.count(),
                'manuals_processing': Manual.query.filter_by(generation_status='processing').count(),
                'manuals_completed': Manual.query.filter_by(generation_status='completed').count()
            }
        }
        
        return jsonify({
            'success': True,
            'metrics': metrics
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@test_ui_bp.route('/response-time-test', methods=['GET'])
def response_time_test():
    """
    Test API response times for various operations
    """
    results = {}
    
    # Test 1: Simple query
    start = time.time()
    Company.query.count()
    results['simple_query_ms'] = (time.time() - start) * 1000
    
    # Test 2: Join query
    start = time.time()
    Manual.query.join(User).limit(10).all()
    results['join_query_ms'] = (time.time() - start) * 1000
    
    # Test 3: Count aggregation
    start = time.time()
    db.session.query(
        Company.id,
        db.func.count(User.id).label('user_count')
    ).join(User).group_by(Company.id).all()
    results['aggregation_query_ms'] = (time.time() - start) * 1000
    
    return jsonify({
        'success': True,
        'response_times': results,
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@test_ui_bp.route('/database-stats', methods=['GET'])
def database_stats():
    """
    Get detailed database statistics
    """
    try:
        stats = {
            'timestamp': datetime.utcnow().isoformat(),
            'tables': {
                'companies': {
                    'total': Company.query.count(),
                    'active': Company.query.filter_by(is_active=True).count()
                },
                'users': {
                    'total': User.query.count(),
                    'active': User.query.filter_by(is_active=True).count(),
                    'by_role': {
                        'admin': User.query.filter_by(role='admin').count(),
                        'user': User.query.filter_by(role='user').count()
                    }
                },
                'manuals': {
                    'total': Manual.query.count(),
                    'by_status': {
                        'completed': Manual.query.filter_by(generation_status='completed').count(),
                        'processing': Manual.query.filter_by(generation_status='processing').count(),
                        'error': Manual.query.filter_by(generation_status='error').count()
                    }
                }
            }
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@test_ui_bp.route('/clear-cache', methods=['POST'])
def clear_cache():
    """
    Clear application caches (placeholder for future caching implementation)
    """
    # This is a placeholder for future cache clearing functionality
    # When Redis or other caching is implemented, this endpoint will clear those caches
    
    return jsonify({
        'success': True,
        'message': 'Cache clearing not implemented yet',
        'timestamp': datetime.utcnow().isoformat()
    }), 200
