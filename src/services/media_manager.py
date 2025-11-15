"""
File: media_manager.py
Purpose: Media management service with GCS integration and tenant isolation
Main functionality: Upload, retrieve, delete media files with strict tenant separation
Dependencies: Google Cloud Storage, FileManager, PIL/OpenCV for image processing
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from werkzeug.utils import secure_filename
from google.cloud import storage
from google.cloud.exceptions import NotFound
import cv2
import numpy as np
from PIL import Image
import io

from src.models.models import db, Media, Company, User
from src.infrastructure.file_manager import FileManager

logger = logging.getLogger(__name__)


class MediaManager:
    """
    Media Management Service
    
    CRITICAL: All operations MUST enforce tenant isolation via company_id
    """
    
    def __init__(self):
        # Get bucket name based on environment
        environment = os.getenv('ENVIRONMENT', 'development')
        if environment == 'production':
            bucket_name = os.getenv('GCS_BUCKET_NAME', 'kantan-ai-manual-generator-live')
        else:
            bucket_name = os.getenv('GCS_BUCKET_NAME', 'kantan-ai-manual-generator-dev')
        
        # Initialize FileManager with proper configuration
        storage_config = {
            'bucket_name': bucket_name,
            'credentials_path': os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        }
        self.file_manager = FileManager(storage_type='gcs', storage_config=storage_config)
        self.storage_client = storage.Client() if self.file_manager.storage_type == 'gcs' else None
        self.bucket_name = bucket_name
        
    def _enforce_tenant_isolation(self, company_id: int, media_id: int = None) -> bool:
        """
        CRITICAL: Verify that media belongs to the specified company
        
        Args:
            company_id: Company ID to check
            media_id: Media ID to verify (optional)
            
        Returns:
            True if validation passes, False otherwise
        """
        if media_id is not None:
            media = Media.query.get(media_id)
            if not media:
                logger.error(f"Media {media_id} not found")
                return False
            
            if media.company_id != company_id:
                logger.error(f"TENANT ISOLATION VIOLATION: Media {media_id} belongs to company {media.company_id}, not {company_id}")
                return False
        
        return True
    
    def upload_media(
        self,
        file_obj,
        company_id: int,
        user_id: int,
        media_type: str,
        title: str = None,
        description: str = None,
        tags: List[str] = None,
        source_type: str = 'upload'
    ) -> Optional[Media]:
        """
        Upload media file to GCS and create Media record
        
        Args:
            file_obj: File object to upload
            company_id: Company ID (tenant isolation)
            user_id: User ID who uploaded
            media_type: 'image' or 'video'
            title: Media title
            description: Media description
            tags: List of tags
            source_type: Source type ('upload', 'video_capture', etc.)
            
        Returns:
            Media object if successful, None otherwise
        """
        try:
            # Validate inputs
            if not file_obj or not company_id or not user_id:
                logger.error("Missing required parameters for media upload")
                return None
            
            # Secure filename
            original_filename = secure_filename(file_obj.filename)
            filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{original_filename}"
            
            # Determine folder structure: company_{company_id}/media/{media_type}/
            folder = f"company_{company_id}/media/{media_type}"
            
            logger.info(f"Uploading media: {filename} to {folder}")
            
            # Upload using FileManager
            result = self.file_manager.save_file(
                file_obj=file_obj,
                filename=filename,
                file_type=media_type,
                folder=folder,
                company_id=company_id
            )
            
            if not result:
                logger.error("FileManager.save_file returned None")
                return None
            
            # Get GCS URI
            gcs_uri = result.get('gcs_uri') or result.get('file_path')
            file_size = result.get('file_size', 0)
            mime_type = result.get('content_type', file_obj.content_type)
            
            # Parse GCS path
            gcs_bucket = self.bucket_name
            gcs_path = gcs_uri.replace(f"gs://{gcs_bucket}/", "") if gcs_uri.startswith('gs://') else gcs_uri
            
            # Extract metadata based on media type
            metadata = {}
            if media_type == 'image':
                metadata = self._extract_image_metadata(file_obj)
            elif media_type == 'video':
                metadata = self._extract_video_metadata(gcs_uri)
            
            # Create Media record
            media = Media(
                company_id=company_id,
                uploaded_by=user_id,
                media_type=media_type,
                filename=filename,
                original_filename=original_filename,
                file_size=file_size,
                mime_type=mime_type,
                gcs_uri=gcs_uri,
                gcs_bucket=gcs_bucket,
                gcs_path=gcs_path,
                title=title or original_filename,
                description=description,
                source_type=source_type,
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            # Set tags
            if tags:
                media.set_tags(tags)
            
            # Set metadata
            if media_type == 'image':
                media.set_image_metadata(metadata)
            elif media_type == 'video':
                media.set_video_metadata(metadata)
            
            db.session.add(media)
            db.session.commit()
            
            logger.info(f"Media created successfully: ID={media.id}, GCS URI={gcs_uri}")
            
            return media
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to upload media: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def capture_frame_from_video(
        self,
        video_media_id: int,
        timestamp: float,
        company_id: int,
        user_id: int,
        title: str = None,
        description: str = None
    ) -> Optional[Media]:
        """
        Capture a frame from video and save as image
        
        Args:
            video_media_id: Source video Media ID
            timestamp: Timestamp in seconds
            company_id: Company ID (tenant isolation)
            user_id: User ID
            title: Image title
            description: Image description
            
        Returns:
            Media object for captured frame, None if failed
        """
        try:
            # Verify tenant isolation
            if not self._enforce_tenant_isolation(company_id, video_media_id):
                return None
            
            # Get video media
            video_media = Media.query.get(video_media_id)
            if not video_media or video_media.media_type != 'video':
                logger.error(f"Invalid video media ID: {video_media_id}")
                return None
            
            # Download video temporarily
            local_video_path = self._download_temp_file(video_media.gcs_uri)
            if not local_video_path:
                return None
            
            # Capture frame using OpenCV
            cap = cv2.VideoCapture(local_video_path)
            
            # Set position to timestamp
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_number = int(timestamp * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                logger.error(f"Failed to capture frame at {timestamp}s")
                os.remove(local_video_path)
                return None
            
            # Convert to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            pil_image = Image.fromarray(frame_rgb)
            
            # Save to BytesIO
            image_bytes = io.BytesIO()
            pil_image.save(image_bytes, format='PNG')
            image_bytes.seek(0)
            
            # Create filename
            filename = f"frame_{video_media.id}_{int(timestamp)}s.png"
            
            # Upload as new media
            from werkzeug.datastructures import FileStorage
            file_obj = FileStorage(
                stream=image_bytes,
                filename=filename,
                content_type='image/png'
            )
            
            media = self.upload_media(
                file_obj=file_obj,
                company_id=company_id,
                user_id=user_id,
                media_type='image',
                title=title or f"Frame at {timestamp}s",
                description=description or f"Captured from {video_media.title}",
                source_type='video_capture'
            )
            
            if media:
                media.source_media_id = video_media_id
                media.source_video_timestamp = timestamp
                db.session.commit()
            
            # Cleanup
            os.remove(local_video_path)
            
            return media
            
        except Exception as e:
            logger.error(f"Failed to capture frame: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def get_media_list(
        self,
        company_id: int,
        media_type: str = None,
        tags: List[str] = None,
        search_query: str = None,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = 'created_at',
        sort_order: str = 'desc'
    ) -> Dict:
        """
        Get paginated media list with filtering
        
        CRITICAL: Only returns media for specified company_id
        
        Args:
            company_id: Company ID (tenant isolation)
            media_type: Filter by media type
            tags: Filter by tags
            search_query: Search in title/description
            page: Page number
            per_page: Items per page
            sort_by: Sort field
            sort_order: 'asc' or 'desc'
            
        Returns:
            Dict with items, total, page info
        """
        try:
            # Base query with tenant isolation
            query = Media.query.filter_by(
                company_id=company_id,
                is_active=True
            )
            
            # Apply filters
            if media_type:
                query = query.filter_by(media_type=media_type)
            
            if search_query:
                search_pattern = f"%{search_query}%"
                query = query.filter(
                    db.or_(
                        Media.title.ilike(search_pattern),
                        Media.description.ilike(search_pattern),
                        Media.filename.ilike(search_pattern)
                    )
                )
            
            if tags:
                # Filter by tags (stored as JSON array)
                for tag in tags:
                    query = query.filter(Media.tags.contains(f'"{tag}"'))
            
            # Apply sorting
            sort_column = getattr(Media, sort_by, Media.created_at)
            if sort_order == 'desc':
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
            
            # Paginate
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            
            # Convert to dict
            items = [media.to_dict() for media in pagination.items]
            
            # Generate signed URLs for each media
            for item in items:
                try:
                    item['signed_url'] = self.get_signed_url(item['gcs_uri'])
                except:
                    item['signed_url'] = None
            
            return {
                'items': items,
                'total': pagination.total,
                'page': page,
                'per_page': per_page,
                'total_pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
            
        except Exception as e:
            logger.error(f"Failed to get media list: {str(e)}")
            return {'items': [], 'total': 0, 'page': 1, 'per_page': per_page}
    
    def get_media_by_id(self, media_id: int, company_id: int) -> Optional[Media]:
        """
        Get media by ID with tenant isolation check
        
        Args:
            media_id: Media ID
            company_id: Company ID (tenant isolation)
            
        Returns:
            Media object if found and belongs to company, None otherwise
        """
        if not self._enforce_tenant_isolation(company_id, media_id):
            return None
        
        return Media.query.get(media_id)
    
    def delete_media(self, media_id: int, company_id: int) -> bool:
        """
        Delete media (soft delete)
        
        Args:
            media_id: Media ID
            company_id: Company ID (tenant isolation)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self._enforce_tenant_isolation(company_id, media_id):
                return False
            
            media = Media.query.get(media_id)
            if not media:
                return False
            
            # Soft delete
            media.is_active = False
            db.session.commit()
            
            logger.info(f"Media {media_id} soft deleted")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to delete media: {str(e)}")
            return False
    
    def get_signed_url(self, gcs_uri: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate signed URL for GCS file
        
        Args:
            gcs_uri: GCS URI (gs://bucket/path)
            expiration: URL expiration in seconds
            
        Returns:
            Signed URL string, None if failed
        """
        try:
            if not self.storage_client:
                logger.warning("GCS client not initialized")
                return gcs_uri
            
            # Parse GCS URI
            if not gcs_uri.startswith('gs://'):
                return gcs_uri
            
            parts = gcs_uri.replace('gs://', '').split('/', 1)
            if len(parts) != 2:
                return gcs_uri
            
            bucket_name, blob_path = parts
            
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            # Generate signed URL
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expiration),
                method="GET"
            )
            
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {str(e)}")
            return gcs_uri
    
    def _extract_image_metadata(self, file_obj) -> Dict:
        """Extract image metadata using PIL"""
        try:
            file_obj.seek(0)
            image = Image.open(file_obj)
            
            metadata = {
                'width': image.width,
                'height': image.height,
                'format': image.format,
                'mode': image.mode
            }
            
            file_obj.seek(0)
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract image metadata: {str(e)}")
            return {}
    
    def _extract_video_metadata(self, gcs_uri: str) -> Dict:
        """Extract video metadata using OpenCV"""
        try:
            local_path = self._download_temp_file(gcs_uri)
            if not local_path:
                return {}
            
            cap = cv2.VideoCapture(local_path)
            
            metadata = {
                'duration': cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS),
                'fps': cap.get(cv2.CAP_PROP_FPS),
                'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            }
            
            cap.release()
            os.remove(local_path)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract video metadata: {str(e)}")
            return {}
    
    def update_media(self, media_id: int, company_id: str, data: Dict) -> Optional[Dict]:
        """
        Update media metadata
        
        Args:
            media_id: Media ID to update
            company_id: Company ID for tenant isolation
            data: Update data (title, description, alt_text, tags)
            
        Returns:
            Updated media dict or None if failed
        """
        try:
            from src.models.models import Media
            from src.core.db_manager import db
            
            # Get media with tenant isolation
            media = db.session.query(Media).filter_by(
                id=media_id,
                company_id=company_id,
                is_active=True
            ).first()
            
            if not media:
                logger.warning(f"Media not found or access denied: {media_id}")
                return None
            
            # Update fields
            if 'title' in data:
                media.title = data['title']
            if 'description' in data:
                media.description = data['description']
            if 'alt_text' in data:
                media.alt_text = data['alt_text']
            if 'tags' in data:
                media.tags = data['tags']
            
            db.session.commit()
            
            logger.info(f"Media updated: {media_id}")
            return media.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to update media: {str(e)}")
            db.session.rollback()
            return None
    
    def _download_temp_file(self, gcs_uri: str) -> Optional[str]:
        """Download GCS file to temporary location"""
        try:
            if not self.storage_client:
                return None
            
            parts = gcs_uri.replace('gs://', '').split('/', 1)
            if len(parts) != 2:
                return None
            
            bucket_name, blob_path = parts
            
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            # Create temp file
            temp_path = f"/tmp/{os.path.basename(blob_path)}"
            blob.download_to_filename(temp_path)
            
            return temp_path
            
        except Exception as e:
            logger.error(f"Failed to download temp file: {str(e)}")
            return None
