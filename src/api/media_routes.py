"""
File: media_routes.py
Purpose: Media Library REST API with tenant isolation
Main functionality: CRUD operations for media, video capture, image editing
Dependencies: Flask, MediaManager, authentication middleware
"""

import os
import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from src.models.models import db, Media, Company, User
from src.services.media_manager import MediaManager
from src.middleware.auth import require_role_enhanced

logger = logging.getLogger(__name__)

# Create Blueprint
media_bp = Blueprint('media', __name__, url_prefix='/api/media')


@media_bp.route('/library', methods=['GET'])
@require_role_enhanced(['admin', 'user'])
def get_media_library():
    """
    Get media library with filtering and pagination
    
    Query params:
      - media_type: 'image' or 'video' (optional)
      - tags: Comma-separated tags (optional)
      - search: Search query (optional)
      - page: Page number (default: 1)
      - per_page: Items per page (default: 20)
      - sort_by: Sort field (default: 'created_at')
      - sort_order: 'asc' or 'desc' (default: 'desc')
    
    Response: {
      "items": [...],
      "total": 100,
      "page": 1,
      "per_page": 20,
      "total_pages": 5,
      "has_next": true,
      "has_prev": false
    }
    """
    try:
        # CRITICAL: Tenant isolation
        company_id = current_user.company_id
        if not company_id:
            return jsonify({'error': 'User not associated with company'}), 401
        
        # Parse query parameters
        media_type = request.args.get('media_type')
        tags_str = request.args.get('tags')
        tags = tags_str.split(',') if tags_str else None
        search_query = request.args.get('search')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Get media list
        manager = MediaManager()
        result = manager.get_media_list(
            company_id=company_id,
            media_type=media_type,
            tags=tags,
            search_query=search_query,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Failed to get media library: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Failed to retrieve media library', 'details': str(e)}), 500


@media_bp.route('/upload', methods=['POST'])
@require_role_enhanced(['admin', 'user'])
def upload_media():
    """
    Upload media file
    
    Form data:
      - file: File object (required)
      - media_type: 'image' or 'video' (required)
      - title: Media title (optional)
      - description: Description (optional)
      - tags: JSON array of tags (optional)
    
    Response: {
      "success": true,
      "media": {...}
    }
    """
    try:
        # CRITICAL: Tenant isolation
        company_id = current_user.company_id
        user_id = current_user.id
        
        if not company_id or not user_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
        # Validate file
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get parameters
        media_type = request.form.get('media_type')
        if media_type not in ['image', 'video']:
            return jsonify({'error': 'Invalid media_type. Must be "image" or "video"'}), 400
        
        title = request.form.get('title')
        description = request.form.get('description')
        
        # Parse tags
        tags = None
        tags_json = request.form.get('tags')
        if tags_json:
            try:
                tags = json.loads(tags_json)
            except:
                pass
        
        # Upload media
        manager = MediaManager()
        media = manager.upload_media(
            file_obj=file,
            company_id=company_id,
            user_id=user_id,
            media_type=media_type,
            title=title,
            description=description,
            tags=tags,
            source_type='upload'
        )
        
        if not media:
            return jsonify({'error': 'Failed to upload media'}), 500
        
        # Get media dict with signed URL
        media_dict = media.to_dict()
        media_dict['signed_url'] = manager.get_signed_url(media.gcs_uri)
        
        return jsonify({
            'success': True,
            'media': media_dict
        }), 201
        
    except Exception as e:
        logger.error(f"Media upload failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Media upload failed', 'details': str(e)}), 500


@media_bp.route('/capture-frame', methods=['POST'])
@require_role_enhanced(['admin', 'user'])
def capture_frame():
    """
    Capture frame from video
    
    Request body: {
      "video_media_id": 123,
      "timestamp": 45.5,
      "title": "Frame title",
      "description": "Description"
    }
    
    Response: {
      "success": true,
      "media": {...}
    }
    """
    try:
        # CRITICAL: Tenant isolation
        company_id = current_user.company_id
        user_id = current_user.id
        
        if not company_id or not user_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
        data = request.json
        
        # Validate parameters
        video_media_id = data.get('video_media_id')
        timestamp = data.get('timestamp')
        
        if not video_media_id or timestamp is None:
            return jsonify({'error': 'video_media_id and timestamp are required'}), 400
        
        title = data.get('title')
        description = data.get('description')
        
        # Capture frame
        manager = MediaManager()
        media = manager.capture_frame_from_video(
            video_media_id=video_media_id,
            timestamp=float(timestamp),
            company_id=company_id,
            user_id=user_id,
            title=title,
            description=description
        )
        
        if not media:
            return jsonify({'error': 'Failed to capture frame'}), 500
        
        # Get media dict with signed URL
        media_dict = media.to_dict()
        media_dict['signed_url'] = manager.get_signed_url(media.gcs_uri)
        
        return jsonify({
            'success': True,
            'media': media_dict
        }), 201
        
    except Exception as e:
        logger.error(f"Frame capture failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Frame capture failed', 'details': str(e)}), 500


@media_bp.route('/<int:media_id>', methods=['GET'])
@require_role_enhanced(['admin', 'user'])
def get_media_detail(media_id):
    """
    Get media detail by ID
    
    Response: Media object directly (for backward compatibility with frontend)
    """
    try:
        # CRITICAL: Tenant isolation
        company_id = current_user.company_id
        if not company_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
        manager = MediaManager()
        media = manager.get_media_by_id(media_id, company_id)
        
        if not media:
            return jsonify({'error': 'Media not found or access denied'}), 404
        
        # Get media dict with signed URL
        media_dict = media.to_dict()
        media_dict['signed_url'] = manager.get_signed_url(media.gcs_uri)
        
        # Return media object directly (not wrapped) for frontend compatibility
        return jsonify(media_dict), 200
        
    except Exception as e:
        logger.error(f"Failed to get media detail: {str(e)}")
        return jsonify({'error': 'Failed to retrieve media', 'details': str(e)}), 500


@media_bp.route('/<int:media_id>', methods=['PUT'])
@require_role_enhanced(['admin', 'user'])
def update_media(media_id):
    """
    Update media metadata
    
    Request body: {
      "title": "New title",
      "description": "New description",
      "alt_text": "Alt text",
      "tags": ["tag1", "tag2"]
    }
    
    Response: {
      "success": true,
      "media": {...}
    }
    """
    try:
        # CRITICAL: Tenant isolation
        company_id = current_user.company_id
        if not company_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
        manager = MediaManager()
        media = manager.get_media_by_id(media_id, company_id)
        
        if not media:
            return jsonify({'error': 'Media not found or access denied'}), 404
        
        data = request.json
        
        # Update fields
        if 'title' in data:
            media.title = data['title']
        if 'description' in data:
            media.description = data['description']
        if 'alt_text' in data:
            media.alt_text = data['alt_text']
        if 'tags' in data:
            media.set_tags(data['tags'])
        
        media.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Get updated media dict
        media_dict = media.to_dict()
        media_dict['signed_url'] = manager.get_signed_url(media.gcs_uri)
        
        return jsonify({
            'success': True,
            'media': media_dict
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to update media: {str(e)}")
        return jsonify({'error': 'Failed to update media', 'details': str(e)}), 500


@media_bp.route('/<int:media_id>', methods=['DELETE'])
@require_role_enhanced(['admin', 'user'])
def delete_media(media_id):
    """
    Delete media (soft delete)
    
    Response: {
      "success": true
    }
    """
    try:
        # CRITICAL: Tenant isolation
        company_id = current_user.company_id
        if not company_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
        manager = MediaManager()
        success = manager.delete_media(media_id, company_id)
        
        if not success:
            return jsonify({'error': 'Failed to delete media or access denied'}), 404
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        logger.error(f"Failed to delete media: {str(e)}")
        return jsonify({'error': 'Failed to delete media', 'details': str(e)}), 500


@media_bp.route('/stats', methods=['GET'])
@require_role_enhanced(['admin', 'user'])
def get_media_stats():
    """
    Get media library statistics
    
    Response: {
      "total_media": 100,
      "images": 80,
      "videos": 20,
      "total_size_mb": 1024.5,
      "recent_uploads": [...]
    }
    """
    try:
        # CRITICAL: Tenant isolation
        company_id = current_user.company_id
        if not company_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
        # Get stats
        total_media = Media.query.filter_by(
            company_id=company_id,
            is_active=True
        ).count()
        
        images_count = Media.query.filter_by(
            company_id=company_id,
            media_type='image',
            is_active=True
        ).count()
        
        videos_count = Media.query.filter_by(
            company_id=company_id,
            media_type='video',
            is_active=True
        ).count()
        
        # Calculate total size
        media_list = Media.query.filter_by(
            company_id=company_id,
            is_active=True
        ).all()
        
        total_size_bytes = sum(m.file_size or 0 for m in media_list)
        total_size_mb = total_size_bytes / (1024 * 1024)
        
        # Get recent uploads
        recent = Media.query.filter_by(
            company_id=company_id,
            is_active=True
        ).order_by(Media.created_at.desc()).limit(5).all()
        
        manager = MediaManager()
        recent_uploads = []
        for media in recent:
            media_dict = media.to_dict()
            media_dict['signed_url'] = manager.get_signed_url(media.gcs_uri)
            recent_uploads.append(media_dict)
        
        return jsonify({
            'total_media': total_media,
            'images': images_count,
            'videos': videos_count,
            'total_size_mb': round(total_size_mb, 2),
            'recent_uploads': recent_uploads
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get media stats: {str(e)}")
        return jsonify({'error': 'Failed to retrieve statistics', 'details': str(e)}), 500


@media_bp.route('/<int:media_id>/proxy', methods=['GET'])
@require_role_enhanced(['admin', 'user'])
def proxy_media(media_id):
    """
    Proxy media file to avoid CORS issues
    
    This endpoint fetches the media from GCS and returns it with proper CORS headers,
    allowing the frontend to use it in Canvas and other contexts that require CORS.
    
    Response: Binary file data with appropriate Content-Type
    """
    try:
        # CRITICAL: Tenant isolation
        company_id = current_user.company_id
        if not company_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
        manager = MediaManager()
        media = manager.get_media_by_id(media_id, company_id)
        
        if not media:
            return jsonify({'error': 'Media not found or access denied'}), 404
        
        # Get signed URL
        signed_url = manager.get_signed_url(media.gcs_uri)
        
        if not signed_url:
            return jsonify({'error': 'Failed to generate signed URL'}), 500
        
        # Fetch file from GCS
        import requests
        response = requests.get(signed_url, stream=True)
        
        if response.status_code != 200:
            return jsonify({'error': 'Failed to fetch media from storage'}), 500
        
        # Return file with proper CORS headers
        from flask import Response
        
        # Determine content type
        content_type = media.mime_type or 'application/octet-stream'
        
        return Response(
            response.content,
            mimetype=content_type,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'public, max-age=3600'
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to proxy media: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Failed to proxy media', 'details': str(e)}), 500
