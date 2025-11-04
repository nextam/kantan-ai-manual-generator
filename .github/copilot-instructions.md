# GitHub Copilot Custom Instructions

## Code Style Guidelines

### General Rules
- **NO EMOJIS** in code, comments, or any source files
- All comments must be written in **English only**
- Use clear, descriptive variable and function names
- Follow PEP 8 style guide for Python code
- Use consistent indentation (4 spaces for Python)

### File Header Requirements
Every source file must include a header comment block with:
```python
"""
File: <filename>
Purpose: <Brief description of what this file does>
Main functionality: <Key features or classes/functions>
Dependencies: <Main imports or requirements>
"""
```

For JavaScript/TypeScript files:
```javascript
/**
 * File: <filename>
 * Purpose: <Brief description of what this file does>
 * Main functionality: <Key features or classes/functions>
 * Dependencies: <Main imports or requirements>
 */
```

### File Organization

#### File Size Limits
- **Maximum 500 lines per file**
- If a file exceeds 500 lines, split it into:
  - Separate modules by functionality
  - Create utility/helper files
  - Use proper imports and module structure

#### Directory Structure

**Root level test/analysis files:**
- All temporary, test, and analysis files in project root
- Naming patterns: `test_*.py`, `check_*.py`, `debug_*.py`, `analyze_*.py`, `migrate_*.py`
- Examples: `test_streaming_api.py`, `check_database_structure.py`, `analyze_db_gcs_detailed.py`

**docs/** folder:
- All markdown documentation files
- Task completion reports
- Architecture documents
- API documentation
- Examples: `SPECIFICATION_*.md`, `README_*.md`, `DEPLOY_*.md`

**manual_generator/** folder:
- Main application code only
- Production-ready modules
- Core business logic
- Flask app, routes, models, templates

**infra/** folder:
- Infrastructure and deployment configurations
- AWS, nginx, deployment scripts
- Examples: `DEPLOYMENT_AWS_ALB.md`, nginx configs

### Naming Conventions

#### Python Files
- Use snake_case: `file_manager.py`, `db_manager.py`, `auth_routes.py`
- Be descriptive: `gemini_service.py` not `service.py`
- Avoid generic names: `database_models.py` not `models.py`

#### Functions and Methods
- Use verb phrases: `process_video()`, `generate_manual()`, `validate_input()`
- Be specific about what the function does

#### Classes
- Use PascalCase: `FileManager`, `ManualModel`, `GeminiService`
- Use nouns that describe the entity

### Comments

#### Required Comments
1. **File header** (as shown above)
2. **Class docstrings**:
```python
class FileManager:
    """
    Manages file operations for Manual Generator system.
    
    Main responsibilities:
    - Upload files to Google Cloud Storage
    - Generate signed URLs for file access
    - Clean up temporary files
    
    Attributes:
        storage_client: GCS client instance
        bucket_name: Target GCS bucket
    """
```

3. **Function docstrings**:
```python
def upload_to_gcs(file_path: str, destination_blob: str) -> str:
    """
    Upload a file to Google Cloud Storage.
    
    Args:
        file_path: Local path to file
        destination_blob: Target path in GCS bucket
        
    Returns:
        Public URL of uploaded file
        
    Raises:
        FileNotFoundError: If file_path does not exist
        ValueError: If GCS credentials are invalid
    """
```

4. **Complex logic explanations**:
```python
# Extract key frames using Gemini's multimodal analysis
# This identifies critical steps in the manufacturing process
key_frames = await gemini_service.extract_key_frames(video_uri)
```

#### Avoid
- Obvious comments: `# increment counter` for `counter += 1`
- Commented-out code blocks (remove or document why kept)
- Japanese language comments

### Code Organization Best Practices

#### Module Splitting Example
If `app.py` exceeds 500 lines, split into:
- `app.py` - Main application entry point (Flask app initialization)
- `auth_routes.py` - Authentication and user management routes
- `api_routes.py` - API endpoint definitions
- `db_manager.py` - Database operations
- `file_manager.py` - File and storage operations
- `gemini_service.py` - AI/Gemini integration

#### Import Organization
```python
# Standard library imports
import os
import sys
from datetime import datetime
from typing import Optional, Dict, List

# Third-party imports
import numpy as np
from flask import Flask, request, jsonify
from google.cloud import storage
from google.genai import Client

# Local application imports
from models import Manual, User, ManualStep
from file_manager import FileManager
from db_manager import init_database
```

### Error Handling
- Use specific exception types
- Always include error messages in English
- Log errors with context
```python
try:
    result = upload_to_gcs(file_path, blob_name)
except FileNotFoundError as e:
    logger.error(f"File not found for upload: {file_path}")
    raise
except Exception as e:
    logger.error(f"GCS upload failed: {str(e)}")
    return None
```

### Environment Variables and Configuration
- **NO HARDCODING**: All configuration values must be controlled via environment variables
- Use `.env` file for environment-specific settings
- Load environment variables using `python-dotenv`
- Provide default values with `os.getenv()` when appropriate

```python
# GOOD: Using environment variables
import os
from dotenv import load_dotenv

load_dotenv()

GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'manual_generator')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')  # No default for sensitive data
PROJECT_ID = os.getenv('PROJECT_ID', 'career-survival')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///instance/manual_generator.db')

# BAD: Hardcoding values
GCS_BUCKET_NAME = 'my-hardcoded-bucket'  # NEVER DO THIS
GOOGLE_API_KEY = 'AIza...'  # NEVER DO THIS
```

### Hallucination Prevention
**CRITICAL**: Always verify that variables, tables, and fields actually exist before referencing them

#### Before Implementation Checklist:
1. **Variable References**:
   - Check that all variables are defined in scope
   - Verify environment variables exist in `.env` or have defaults
   - Confirm imported modules/functions are actually available

2. **Database References**:
   - Verify table names match actual database schema
   - Confirm column/field names exist in the table
   - Check foreign key relationships are valid

3. **API/Model References**:
   - Verify API endpoints exist
   - Confirm model attributes/methods are defined
   - Check that data structures match actual implementation

```python
# GOOD: Verify before using
from models import Manual

# Check if the attribute exists
if hasattr(Manual, 'description'):
    manual_desc = manual.description
else:
    logger.error("Manual model does not have 'description' attribute")
    raise AttributeError("Missing description attribute")

# Verify environment variable
gcs_bucket = os.getenv('GCS_BUCKET_NAME')
if not gcs_bucket:
    raise ValueError("GCS_BUCKET_NAME environment variable is not set")

# BAD: Assuming things exist
manual_desc = manual.description  # What if 'description' doesn't exist?
gcs_bucket = os.getenv('GCS_BUCKET_NAME')  # What if it's None?
storage_client.upload_file(gcs_bucket, file)  # This will fail if gcs_bucket is None
```

#### Database Schema Verification:
```python
# When working with database models, always verify schema first
from sqlalchemy import inspect

def verify_table_exists(engine, table_name):
    """Verify that a table exists in the database."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    if table_name not in tables:
        raise ValueError(f"Table '{table_name}' does not exist. Available tables: {tables}")
    return True

def verify_column_exists(engine, table_name, column_name):
    """Verify that a column exists in a table."""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    if column_name not in columns:
        raise ValueError(f"Column '{column_name}' does not exist in table '{table_name}'. Available columns: {columns}")
    return True
```

### Testing and Development Files

All files matching these patterns stay in **project root**:
- `test_*.py` - Test scripts
- `check_*.py` - Validation scripts
- `debug_*.py` - Debugging utilities
- `analyze_*.py` - Analysis tools
- `migrate_*.py` - Migration scripts
- `*_example.py` - Example code

### Documentation Files

All markdown files go in **docs/** or **project root** (for major specs):
- `*.md` - General documentation
- `SPECIFICATION_*.md` - System specifications (can be in root)
- `README_*.md` - Feature-specific documentation
- `DEPLOY_*.md` - Deployment guides
- `*_GUIDE.md` - Implementation guides
- `README.md` - Main project README (in root)

## Summary Checklist

When creating or modifying files, ensure:
- [ ] No emojis anywhere in the code
- [ ] All comments are in English
- [ ] File has proper header comment block
- [ ] File is under 500 lines (split if needed)
- [ ] Test/check files are in project root
- [ ] Documentation files are in `docs/` or root for specs
- [ ] Functions have descriptive docstrings
- [ ] Imports are organized by type
- [ ] Error handling uses English messages
- [ ] **No hardcoded values** - all config via environment variables
- [ ] **Verify existence** - all referenced variables/tables/fields actually exist
- [ ] Environment variables loaded from `.env` file
- [ ] Database schema verified before querying

## Production Deployment (EC2)

### Deployment Target
- **Server**: EC2 instance at `ec2-52-198-123-171.ap-northeast-1.compute.amazonaws.com`
- **SSH Key**: `kantan-ai.pem` (in project root)
- **Project Path**: `/opt/kantan-ai-manual-generator`
- **User**: `ec2-user`

### Services to Restart
After deployment, restart Docker services:
```bash
sudo docker-compose restart manual  # Manual Generator service
```

### Standard Deployment Command
```bash
ssh -i kantan-ai.pem ec2-user@ec2-52-198-123-171.ap-northeast-1.compute.amazonaws.com "cd /opt/kantan-ai-manual-generator && git pull origin main && sudo docker-compose build manual && sudo docker-compose up -d manual"
```

### CRITICAL WARNINGS

#### 1. Never Deploy During Active Manual Generation
- Check if manual generation is running before deploying
- Active Gemini API calls may be interrupted
- Check container logs: `sudo docker-compose logs manual`

#### 2. Database Schema Changes
- **ALWAYS** create a backup before schema migration:
  ```bash
  cp instance/manual_generator.db instance/manual_generator.db.backup_$(date +%Y%m%d_%H%M%S)
  ```
- Test migrations locally first
- Use migration scripts in project root
- Never modify schema directly in production

#### 3. Service Verification
After deployment, verify service is running:
```bash
# Check Docker container status
sudo docker ps -a | grep manual-generator

# Check application health
curl http://localhost:8080/

# View container logs
sudo docker-compose logs -f manual
```

#### 4. Google Cloud Storage Integration
- **CRITICAL**: GCS credentials must be properly configured
- Service account JSON file (`gcp-credentials.json`) must be in container
- Verify bucket access permissions before deployment
- **Environment Variables Required**:
  - `GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-credentials.json`
  - `GCS_BUCKET_NAME=manual_generator`
  - `PROJECT_ID=career-survival`
  - `GOOGLE_API_KEY` (for Gemini API)

**GCS Configuration Verification:**
```bash
# Verify GCS credentials in container
sudo docker exec manual-generator ls -la /app/gcp-credentials.json

# Test GCS bucket access
sudo docker exec manual-generator python -c "
from google.cloud import storage
client = storage.Client()
bucket = client.bucket('manual_generator')
print(f'Bucket exists: {bucket.exists()}')
"

# Verify environment variables
sudo docker exec manual-generator env | grep GOOGLE
```

**Common GCS Issues:**
- **Symptom**: "Could not automatically determine credentials"
- **Cause**: GOOGLE_APPLICATION_CREDENTIALS not set or file not accessible
- **Solution**: Verify environment variable in docker-compose.yml and file exists in container

- **Symptom**: "Permission denied" when uploading to GCS
- **Cause**: Service account lacks Storage Object Admin role
- **Solution**: Update IAM permissions in Google Cloud Console

#### 5. Service-Specific Notes

**Manual Generator (Flask):**
- Port: 5000 (internal), 8080 (external via docker-compose)
- Framework: Flask + Gunicorn/Waitress
- **Dependencies**: 
  - Google Cloud Storage for file uploads
  - Google Gemini API for AI manual generation
  - SQLite database for metadata
  - OpenCV for video processing
- Log: Docker container logs

**Required Environment Variables:**
```bash
# Google Cloud
GOOGLE_API_KEY=<gemini-api-key>
GCS_BUCKET_NAME=manual_generator
PROJECT_ID=career-survival
GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-credentials.json
VERTEX_AI_LOCATION=us-central1

# Database
DATABASE_URL=sqlite:///instance/manual_generator.db

# Flask
SECRET_KEY=<random-secret-key>
FLASK_ENV=production
```

#### 6. Rollback Procedure
If deployment causes issues:
```bash
# SSH to server
ssh -i "kantan-ai.pem" ec2-user@ec2-52-198-123-171.ap-northeast-1.compute.amazonaws.com

# Navigate to project
cd /opt/kantan-ai-manual-generator

# Rollback to previous commit
git log --oneline -5  # Find previous commit hash
git reset --hard <previous-commit-hash>

# Rebuild and restart
sudo docker-compose build manual
sudo docker-compose up -d manual

# If database was migrated, restore backup
cp instance/manual_generator.db.backup_YYYYMMDD_HHMMSS instance/manual_generator.db
sudo docker-compose restart manual
```

#### 7. Log Monitoring
Monitor logs after deployment:
```bash
# Docker container logs
sudo docker-compose logs -f manual

# Check for errors
sudo docker-compose logs manual | grep -i error

# Check recent logs (last 100 lines)
sudo docker-compose logs --tail=100 manual
```

### Pre-Deployment Checklist
- [ ] Code tested locally with GCS + Gemini API
- [ ] No syntax errors (`python -m py_compile manual_generator/**/*.py`)
- [ ] Database schema changes tested locally
- [ ] `.env` variables documented if new ones added
- [ ] Breaking changes documented
- [ ] No active manual generation on production
- [ ] Git commit pushed to `main` branch
- [ ] GCS credentials file included in build context

### Post-Deployment Verification
- [ ] Docker container running: `sudo docker ps | grep manual-generator`
- [ ] Health endpoint responds: `curl http://localhost:8080/`
- [ ] Web interface accessible via ALB: https://manual-generator.kantan-ai.net
- [ ] **GCS accessible**: Upload test file via UI
- [ ] **Gemini API working**: Generate test manual
- [ ] Database accessible: Check manual list loads
- [ ] Can create new manual entry
- [ ] Can upload video file to GCS
- [ ] AI manual generation completes successfully
- [ ] **UI changes reflected**: Hard refresh browser (Ctrl+Shift+R)
- [ ] Check logs for errors (first 5 minutes)

### AI Manual Generation Verification

After deploying changes to Gemini integration:

1. **Upload a test video**:
   - Use a short manufacturing process video (< 2 minutes recommended)
   - Upload through web interface

2. **Monitor generation process**:
   ```bash
   sudo docker-compose logs -f manual
   # Watch for: "Starting AI manual generation for video: <uri>"
   # Watch for errors: "Gemini API error" or "Failed to generate manual"
   ```

3. **Verify result in database**:
   ```bash
   sudo docker exec manual-generator sqlite3 instance/manual_generator.db "SELECT id, title, created_at FROM manuals ORDER BY id DESC LIMIT 5;"
   ```

4. **Test manual display**:
   - Open the manual detail page in browser
   - Verify content is structured correctly
   - Check that all manual steps are displayed
   - Verify timestamps are accurate

5. **Verify GCS integration**:
   ```bash
   # Check uploaded video exists in GCS
   gsutil ls gs://manual_generator/uploads/
   
   # Verify file access via signed URL
   # Should be visible in web interface
   ```

### Gemini-Specific Troubleshooting

If AI manual generation fails after deployment:

1. **Check Gemini API Key**:
   ```bash
   sudo docker exec manual-generator env | grep GOOGLE_API_KEY
   ```
   Should return the API key (partially masked)

2. **Verify Gemini SDK version**:
   ```bash
   sudo docker exec manual-generator pip list | grep google-genai
   ```
   Should show version >= 0.3.0

3. **Check API quota and limits**:
   - Review Google Cloud Console for API quota
   - Check for rate limiting errors in logs
   - Verify billing is enabled for the project

4. **Test Gemini API directly**:
   ```bash
   sudo docker exec manual-generator python -c "
   from google.genai import Client
   import os
   client = Client(api_key=os.getenv('GOOGLE_API_KEY'))
   print('Gemini client initialized successfully')
   "
   ```

5. **Common Error Messages**:
   - **"API key not valid"**: Check GOOGLE_API_KEY environment variable
   - **"Quota exceeded"**: Wait for quota reset or increase quota in GCP
   - **"Video file too large"**: GCS upload failed, check bucket permissions
   - **"Invalid video format"**: Gemini supports MP4, MOV, AVI, WebM, MKV

### Emergency Contact
If deployment fails and you cannot resolve:
1. Immediately rollback using above procedure
2. Check logs for specific error messages
3. Restore database backup if schema migration failed
4. Verify AWS resources (ALB, EC2) are healthy
5. Check Google Cloud resources (GCS bucket, Gemini API) are accessible
