"""
File: check_session_debug.py
Purpose: Debug session variables by adding a test endpoint
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.app import app

# Add temporary debug route
@app.route('/debug/session')
def debug_session():
    from flask import session, jsonify
    from flask_login import current_user
    
    return jsonify({
        'session_data': dict(session),
        'current_user': {
            'is_authenticated': current_user.is_authenticated,
            'id': current_user.id if current_user.is_authenticated else None,
            'username': current_user.username if current_user.is_authenticated else None,
            'role': current_user.role if current_user.is_authenticated else None,
            'company_id': current_user.company_id if current_user.is_authenticated else None
        }
    })

print("Debug route added: /debug/session")
print("Access http://localhost:5000/debug/session after logging in")
