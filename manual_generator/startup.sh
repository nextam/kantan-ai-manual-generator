#!/bin/bash

echo "=== Manual Generator Startup Script ==="

# Ensure necessary directories exist with proper permissions
echo "Creating directories..."
mkdir -p instance uploads uploads/video logs temp_uploads

# Set proper permissions
echo "Setting permissions..."
chmod 755 instance uploads uploads/video logs temp_uploads

# Check if we can write to instance directory
echo "Testing write permissions..."
if touch instance/test_write.tmp 2>/dev/null; then
    echo "✁EInstance directory is writable"
    rm -f instance/test_write.tmp
else
    echo "❁EInstance directory is not writable, attempting to fix..."
    chmod 777 instance
    # Try again
    if touch instance/test_write.tmp 2>/dev/null; then
        echo "✁EFixed: Instance directory is now writable"
        rm -f instance/test_write.tmp
    else
        echo "❁EFATAL: Cannot write to instance directory"
        exit 1
    fi
fi

# Set environment variable for database path
export DATABASE_PATH="/app/instance/manual_generator.db"
echo "Database path: $DATABASE_PATH"

# Check for existing database
if [ -f "instance/manual_generator.db" ]; then
    echo "✁EDatabase file exists"
    ls -la instance/manual_generator.db
else
    echo "ℹ�E�EDatabase file will be created on first run"
fi

# List current directory contents
echo "Current directory contents:"
ls -la

echo "Instance directory contents:"
ls -la instance/ || echo "Instance directory is empty or inaccessible"

echo "Starting Gunicorn (Linux production server)..."
# Start the application with Gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 600 --log-level debug "app:app"
