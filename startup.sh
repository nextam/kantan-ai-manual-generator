#!/bin/bash

echo "=== Manual Generator Startup Script ==="

# Ensure necessary directories exist with proper permissions
echo "Creating directories..."
mkdir -p uploads uploads/video temp_uploads

# Set proper permissions for app directories
echo "Setting permissions..."
chmod 755 uploads uploads/video temp_uploads

# Note: instance and logs are mounted from host, so we just verify them
echo "Verifying mounted directories..."
if [ -d "/instance" ]; then
    echo "✓ /instance directory is mounted"
    ls -la /instance || echo "/instance directory is empty"
else
    echo "⚠ /instance directory is not mounted! Creating it..."
    mkdir -p /instance
    chmod 755 /instance
fi

if [ -d "/logs" ]; then
    echo "✓ /logs directory is mounted"
else
    echo "⚠ /logs directory is not mounted! Creating it..."
    mkdir -p /logs
    chmod 755 /logs
fi

# Check if we can write to instance directory
echo "Testing write permissions..."
if touch /instance/test_write.tmp 2>/dev/null; then
    echo "✓ Instance directory is writable"
    rm -f /instance/test_write.tmp
else
    echo "❌ Instance directory is not writable, attempting to fix..."
    chmod 777 /instance
    # Try again
    if touch /instance/test_write.tmp 2>/dev/null; then
        echo "✓ Fixed: Instance directory is now writable"
        rm -f /instance/test_write.tmp
    else
        echo "❌ FATAL: Cannot write to instance directory"
        exit 1
    fi
fi

# Set environment variable for database path
export DATABASE_PATH="/instance/manual_generator.db"
echo "Database path: $DATABASE_PATH"

# Check for existing database
if [ -f "/instance/manual_generator.db" ]; then
    echo "✓ Database file exists"
    ls -la /instance/manual_generator.db
else
    echo "ℹ️ Database file will be created on first run"
fi

echo "Starting Gunicorn (Linux production server)..."
# Start the application with Gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 600 --log-level debug "app:app"
