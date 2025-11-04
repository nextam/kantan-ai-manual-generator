"""
Google Cloud Platform configuration helper

Automatically loads GCP project configuration from service account credentials.
"""

import os
import json
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def get_project_id_from_credentials() -> Optional[str]:
    """
    Extract project_id from GCP service account credentials file.
    
    Returns:
        Project ID if found, None otherwise
    """
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if not creds_path:
        logger.debug("GOOGLE_APPLICATION_CREDENTIALS not set")
        return None
    
    # Convert to absolute path if relative
    if not os.path.isabs(creds_path):
        # Assume relative to project root
        project_root = Path(__file__).resolve().parents[2]
        creds_path = str(project_root / creds_path)
    
    if not os.path.exists(creds_path):
        logger.warning(f"Credentials file not found: {creds_path}")
        return None
    
    try:
        with open(creds_path, 'r', encoding='utf-8') as f:
            credentials = json.load(f)
            project_id = credentials.get('project_id')
            
            if project_id:
                logger.info(f"Loaded project_id from credentials: {project_id}")
                return project_id
            else:
                logger.warning("project_id not found in credentials file")
                return None
                
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse credentials file: {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading credentials file: {e}")
        return None


def get_gcp_project_id() -> str:
    """
    Get GCP project ID from environment variables or credentials file.
    
    Priority:
    1. PROJECT_ID environment variable
    2. GOOGLE_CLOUD_PROJECT_ID environment variable
    3. project_id from gcp-credentials.json
    
    Returns:
        Project ID
        
    Raises:
        ValueError: If project ID cannot be determined
    """
    # Check environment variables first
    project_id = os.getenv('PROJECT_ID') or os.getenv('GOOGLE_CLOUD_PROJECT_ID')
    
    if project_id:
        logger.info(f"Using project_id from environment: {project_id}")
        return project_id
    
    # Try to load from credentials file
    project_id = get_project_id_from_credentials()
    
    if project_id:
        return project_id
    
    raise ValueError(
        "GCP Project ID not found. Please set PROJECT_ID environment variable "
        "or ensure GOOGLE_APPLICATION_CREDENTIALS points to a valid service account key file."
    )


def get_gcp_config() -> dict:
    """
    Get complete GCP configuration.
    
    Returns:
        Dictionary with GCP configuration:
        - project_id: GCP project ID
        - location: Vertex AI location
        - bucket_name: GCS bucket name
        - credentials_path: Path to credentials file
    """
    return {
        'project_id': get_gcp_project_id(),
        'location': os.getenv('VERTEX_AI_LOCATION', 'us-central1'),
        'bucket_name': os.getenv('GCS_BUCKET_NAME'),
        'credentials_path': os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    }
