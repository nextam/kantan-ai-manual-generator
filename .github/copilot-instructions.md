# GitHub Copilot Custom Instructions

## Code Style Guidelines

### General Rules
- **NO EMOJIS** in code, comments, or any source files
- All comments must be written in **English only**
- Use clear, descriptive variable and function names
- Follow PEP 8 style guide for Python code
- Use consistent indentation (4 spaces for Python)

### Development Task Completion Requirements
- **CRITICAL**: Before reporting task completion to the user, you MUST:
  1. **Fix all syntax errors and reference errors** - Ensure code is syntactically correct
  2. **Perform thorough testing and debugging** - Test the implementation multiple times
  3. **Verify complete functionality** - Confirm everything works perfectly in production-like conditions
  4. **Never report completion** until the feature is fully functional and tested

### API-First Development Approach
- **Design all features to be testable via API endpoints**
- Implement comprehensive API interfaces for all core functionality
- Enable production-like testing through API calls rather than UI-only testing
- This ensures:
  - Faster and more reliable testing workflow
  - Better integration testing capabilities
  - Easier automation and CI/CD integration
  - Consistent behavior between different interfaces

### Problem-Solving and Debugging Guidelines
- **Root Cause Analysis**: When errors occur during testing or development:
  1. **Never apply temporary workarounds** or band-aid fixes
  2. **Investigate thoroughly** to identify the root cause of the problem
  3. **Implement fundamental solutions** that address the underlying issue
  4. **Ask the user** if substantial system changes are required for proper resolution
- **Avoid quick fixes** that only make tests pass without solving the actual problem
- **Document findings** when root cause analysis reveals systemic issues

### AI Prompt Design Principles
- **Design for generality**: Always create prompts assuming diverse, real-world usage scenarios
- **NEVER optimize prompts** solely to pass specific test cases
- **Avoid overfitting**: Do not create narrowly-focused prompts that only work for current test data
- **Think long-term**: Consider how the prompt will perform with:
  - Different input variations
  - Edge cases and unusual scenarios
  - Production data that differs from test data
  - Future use cases and requirements
- **Test broadly**: Validate prompts against multiple scenarios, not just the immediate test case

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

#### Workspace Navigation
- **ALWAYS use SERENA MCP tools** for file searching and workspace structure understanding
- Use `mcp_oraios_serena_list_dir` to explore directory structure
- Use `mcp_oraios_serena_find_file` to locate specific files
- Use `mcp_oraios_serena_search_for_pattern` to search code patterns
- Prefer SERENA tools over manual file navigation for accuracy and efficiency

#### Directory Structure

**scripts/** folder (REQUIRED):
- **ALL temporary files** must be stored in `scripts/` folder
- **File types**: `.py`, `.sh`, `.bat`, `.ps1`, and any other temporary script files
- Includes: test files, check scripts, debug utilities, analysis tools, migration scripts
- Naming patterns: `test_*.py`, `check_*.py`, `debug_*.py`, `analyze_*.py`, `migrate_*.py`
- Temporary markdown files for analysis/reports
- Shell scripts for one-time operations
- Examples: `test_streaming_api.py`, `check_database_structure.py`, `analyze_db_gcs_detailed.py`
- **NEVER create temporary files in project root**

**docs/** folder (REQUIRED):
- **ALL permanent markdown documentation files** must be stored in `docs/` folder
- Task completion reports
- Architecture documents
- API documentation
- Technical specifications
- Examples: `SPECIFICATION_*.md`, `README_*.md`, `DEPLOY_*.md`
- **When creating a new markdown file**:
  1. First, update the main `README.md` in project root with a link to the new document
  2. Then, create the markdown file in `docs/` folder
  3. Ensure the document follows the project's documentation structure

**src/** folder:
- Main application code only
- Production-ready modules
- Core business logic
- Flask app, routes, models, templates

**infra/** folder:
- Infrastructure and deployment configurations
- AWS deployment scripts and configurations
- Examples: `DEPLOYMENT_AWS_ALB.md`, deployment scripts

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
If a module file exceeds 500 lines, split into:
- `src/core/app.py` - Main application entry point (Flask app initialization)
- `src/api/auth_routes.py` - Authentication and user management API routes
- `src/routes/` - Additional route definitions
- `src/core/db_manager.py` - Database operations
- `src/infrastructure/file_manager.py` - File and storage operations
- `src/services/gemini_service.py` - AI/Gemini integration

### Folder Structure

**Project Root (kantan-ai-manual-generator/)**:
```
kantan-ai-manual-generator/
├── app.py                      # Application entry point
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── .env.example                # Environment variables template
├── src/                        # Source code (main application)
│   ├── api/                   # API endpoints
│   │   └── auth_routes.py     # Authentication routes
│   ├── config/                # Configuration files
│   ├── core/                  # Core application logic
│   │   ├── app.py             # Flask application
│   │   ├── db_manager.py      # Database manager
│   │   └── init_db.py         # Database initialization
│   ├── infrastructure/        # External service integrations
│   │   └── file_manager.py    # File/GCS operations
│   ├── middleware/            # Middleware components
│   │   └── auth.py            # Authentication middleware
│   ├── models/                # Data models
│   │   └── models.py          # SQLAlchemy models
│   ├── routes/                # Additional routes
│   ├── services/              # Business logic services
│   │   ├── gemini_service.py          # Gemini AI service
│   │   ├── pdf_generator.py           # PDF generation
│   │   ├── video_manual_generator.py  # Video manual generation
│   │   └── terminology_db.py          # Terminology database
│   ├── static/                # Static files (CSS, JS, images)
│   │   ├── icons/             # Favicon files
│   │   └── js/                # JavaScript files
│   ├── tasks/                 # Background tasks
│   ├── templates/             # HTML templates
│   ├── uploads/               # User uploaded files
│   ├── utils/                 # Utility functions
│   │   ├── frame_orientation.py
│   │   └── path_normalization.py
│   └── workers/               # Background workers
├── instance/                   # Instance-specific data (database)
└── logs/                       # Application logs
```

**scripts/** folder (REQUIRED):
- **ALL temporary files** must be stored in `scripts/` folder
- Includes: test files, check scripts, debug utilities, analysis tools, migration scripts
- Naming patterns: `test_*.py`, `check_*.py`, `debug_*.py`, `analyze_*.py`, `migrate_*.py`
- **File types**: `.py`, `.sh`, `.bat`, `.ps1`, and any other temporary script files
- Temporary markdown files for analysis/reports
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
from src.models.models import Manual, User, ManualStep
from src.infrastructure.file_manager import FileManager
from src.core.db_manager import init_database
from src.services.gemini_service import GeminiService
from src.middleware.auth import require_authentication
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

# Google Cloud Configuration
# Use service account authentication (gcp-credentials.json)
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'gcp-credentials.json')
GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'kantan-ai-manual-generator')
PROJECT_ID = os.getenv('PROJECT_ID', 'kantan-ai-database')
VERTEX_AI_LOCATION = os.getenv('VERTEX_AI_LOCATION', 'us-central1')

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///instance/manual_generator.db')

# BAD: Hardcoding values
GCS_BUCKET_NAME = 'my-hardcoded-bucket'  # NEVER DO THIS
# Note: API key authentication is NOT used - use service account (gcp-credentials.json) instead
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

All files matching these patterns go in **scripts/** folder:
- `test_*.py` - Test scripts
- `check_*.py` - Validation scripts
- `debug_*.py` - Debugging utilities
- `analyze_*.py` - Analysis tools
- `migrate_*.py` - Migration scripts
- `*_example.py` - Example code
- Temporary `.sh`, `.bat`, `.ps1` scripts for one-time operations
- Temporary `.md` files for analysis reports
- **ANY temporary script file** regardless of extension (`.py`, `.sh`, `.bat`, `.ps1`, etc.)

### Documentation Files

**IMPORTANT**: When creating a new markdown file:
1. Update `README.md` in project root with a link to the new document
2. Create the markdown file in `docs/` folder (not in project root)
3. Use clear, descriptive filenames

Permanent markdown files go in **docs/** folder:
- `SPECIFICATION_*.md` - System specifications
- `DEPLOY_*.md` - Deployment guides
- `ARCHITECTURE_*.md` - Architecture documents
- `API_*.md` - API documentation
- Task completion reports
- Technical documentation
- All other `.md` files (except README.md in root)

Exceptions (allowed in project root):
- `README.md` - Main project README (ONLY this file in root)

## Summary Checklist

When creating or modifying files, ensure:
- [ ] No emojis anywhere in the code
- [ ] All comments are in English
- [ ] File has proper header comment block
- [ ] File is under 500 lines (split if needed)
- [ ] **Use SERENA MCP tools** for workspace navigation and file search
- [ ] **Test/check/temporary files are in `scripts/` folder**
- [ ] Documentation files are in `docs/` or root for specs
- [ ] Functions have descriptive docstrings
- [ ] Imports are organized by type
- [ ] Error handling uses English messages
- [ ] **No hardcoded values** - all config via environment variables
- [ ] **Verify existence** - all referenced variables/tables/fields actually exist
- [ ] Environment variables loaded from `.env` file
- [ ] Database schema verified before querying
- [ ] **Task completion**: All syntax/reference errors fixed and thoroughly tested before reporting completion
- [ ] **API-first approach**: Core features testable via API endpoints for production-like testing
- [ ] **Root cause analysis**: Errors resolved fundamentally, not with temporary workarounds
- [ ] **Prompt design**: AI prompts designed for general use, not optimized for specific test cases only

## Production Deployment (EC2)

### Deployment Target
- **Server**: EC2 instance at `57.181.226.188`
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
ssh -i kantan-ai.pem ec2-user@57.181.226.188 "cd /opt/kantan-ai-manual-generator && git pull origin main && sudo docker-compose build manual && sudo docker-compose up -d manual"
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
- **CRITICAL**: GCS credentials must be properly configured using service account
- Service account JSON file (`gcp-credentials.json`) must be in container
- Verify bucket access permissions before deployment
- **Environment Variables Required**:
  - `GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-credentials.json`
  - `GCS_BUCKET_NAME=kantan-ai-manual-generator`
  - `PROJECT_ID=kantan-ai-database`
  - `VERTEX_AI_LOCATION=us-central1`

**Note**: This project uses **service account authentication** via `gcp-credentials.json`, NOT API key authentication.

**GCS Configuration Verification:**
```bash
# Verify GCS credentials in container
sudo docker exec manual-generator ls -la /app/gcp-credentials.json

# Test GCS bucket access
sudo docker exec manual-generator python -c "
from google.cloud import storage
client = storage.Client()
bucket = client.bucket('kantan-ai-manual-generator')
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
# Google Cloud (Service Account Authentication)
GCS_BUCKET_NAME=kantan-ai-manual-generator
PROJECT_ID=kantan-ai-database
GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-credentials.json
VERTEX_AI_LOCATION=us-central1

# Database
DATABASE_URL=sqlite:///instance/manual_generator.db

# Flask
SECRET_KEY=<random-secret-key>
FLASK_ENV=production
```

**Note**: Authentication uses service account (`gcp-credentials.json`), not API key.

#### 6. Rollback Procedure
If deployment causes issues:
```bash
# SSH to server
ssh -i "kantan-ai.pem" ec2-user@57.181.226.188

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
- [ ] No syntax errors (`python -m py_compile src/**/*.py`)
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
   gsutil ls gs://kantan-ai-manual-generator/uploads/
   
   # Verify file access via signed URL
   # Should be visible in web interface
   ```

### Gemini-Specific Troubleshooting

If AI manual generation fails after deployment:

1. **Check GCS Service Account Credentials**:
   ```bash
   sudo docker exec manual-generator env | grep GOOGLE_APPLICATION_CREDENTIALS
   sudo docker exec manual-generator ls -la /app/gcp-credentials.json
   ```
   Verify service account file exists and has proper permissions

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
   client = Client(vertexai=True, project=os.getenv('PROJECT_ID'), location=os.getenv('VERTEX_AI_LOCATION'))
   print('Gemini client initialized successfully')
   "
   ```

5. **Common Error Messages**:
   - **"Could not automatically determine credentials"**: Check GOOGLE_APPLICATION_CREDENTIALS environment variable and gcp-credentials.json file
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
