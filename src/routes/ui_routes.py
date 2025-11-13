"""
File: ui_routes.py
Purpose: UI routes for admin and company dashboards
Main functionality: Render templates for admin interfaces
Dependencies: Flask, auth middleware
"""

from flask import Blueprint, render_template, redirect, url_for, session, g
from src.middleware.auth import require_role

# Super Admin UI Blueprint
super_admin_ui_bp = Blueprint('super_admin_ui', __name__, url_prefix='/super-admin')

@super_admin_ui_bp.route('/companies')
def companies():
    """Company management page"""
    if not session.get('is_super_admin'):
        return redirect(url_for('super_admin_login'))
    return render_template('super_admin_companies.html')

@super_admin_ui_bp.route('/users')
def users():
    """User management page (all companies)"""
    if not session.get('is_super_admin'):
        return redirect(url_for('super_admin_login'))
    return render_template('super_admin_users.html')

@super_admin_ui_bp.route('/activity-logs')
def activity_logs():
    """Activity logs page"""
    if not session.get('is_super_admin'):
        return redirect(url_for('super_admin_login'))
    return render_template('super_admin_logs.html')


# Company Admin UI Blueprint
company_ui_bp = Blueprint('company_ui', __name__, url_prefix='/company')

@company_ui_bp.route('/dashboard')
@require_role('admin')
def dashboard():
    """Company admin dashboard"""
    return render_template('company_dashboard.html')

@company_ui_bp.route('/users')
@require_role('admin')
def users():
    """User management page (own company)"""
    return render_template('company_users.html')

@company_ui_bp.route('/templates')
@require_role('admin')
def templates():
    """Template management page"""
    return render_template('company_templates.html')


# General UI Blueprint
ui_bp = Blueprint('ui', __name__)

@ui_bp.route('/materials')
def materials():
    """Reference materials management page"""
    if not session.get('company_id') and not session.get('is_super_admin'):
        return redirect(url_for('login_page'))
    return render_template('materials.html')

@ui_bp.route('/jobs')
def jobs():
    """Job status page"""
    if not session.get('company_id') and not session.get('is_super_admin'):
        return redirect(url_for('login_page'))
    return render_template('jobs.html')

@ui_bp.route('/manuals/create')
def create_manual():
    """Unified manual creation page"""
    if not session.get('company_id') and not session.get('is_super_admin'):
        return redirect(url_for('login_page'))
    return render_template('manual_create_unified.html')
