"""
Manual Generator Application Entry Point

This file serves as the entry point for the Manual Generator application.
It imports and runs the main Flask application from the src.core module.
"""

import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and run the main application
from src.core.app import app

if __name__ == '__main__':
    # Run the Flask application
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False
    )
