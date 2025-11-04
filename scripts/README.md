# Scripts Folder

## Purpose
This folder contains all temporary, test, and development scripts for the Manual Generator project.

## File Categories

### Test Scripts
- `test_*.py` - Unit tests, integration tests, API tests
- Example: `test_streaming_api.py`, `test_file_manager.py`

### Validation Scripts
- `check_*.py` - Database validation, configuration checks, system health checks
- Example: `check_database_structure.py`, `check_gcs_files.py`

### Analysis Tools
- `analyze_*.py` - Data analysis, performance analysis, debugging tools
- Example: `analyze_db_gcs_detailed.py`, `analyze_missing_vs_orphans.py`

### Migration Scripts
- `migrate_*.py` - Database migrations, data migrations, schema updates
- Example: `migrate_remove_storage_columns.py`

### Debug Utilities
- `debug_*.py` - Debugging helpers, diagnostic tools
- Example: `debug_db.py`

### Temporary Documentation
- `*.md` files - Temporary analysis reports, investigation notes
- Example: `DATABASE_GCS_ANALYSIS_REPORT.md`

### Configuration Files
- `*.json` - Temporary configuration files for testing
- Example: `cloudwatch-config-docker-logs.json`

## Guidelines

### DO:
✅ Place all temporary/test files in this folder
✅ Use descriptive naming conventions (test_*, check_*, analyze_*, etc.)
✅ Include file header comments explaining the purpose
✅ Clean up obsolete scripts regularly

### DON'T:
❌ Place production code in this folder
❌ Reference these scripts in production code
❌ Commit sensitive data (API keys, credentials) in scripts

## Cleanup
Regularly review and remove obsolete scripts that are no longer needed.
