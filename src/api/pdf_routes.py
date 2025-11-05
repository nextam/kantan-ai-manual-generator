"""
File: pdf_routes.py
Purpose: API endpoints for PDF generation and download
Main functionality: Generate PDF, check status, download PDF
Dependencies: Flask, models, pdf_generator, s3_manager
"""

from flask import Blueprint, request, jsonify, send_file, session
from src.models.models import db, Manual, ManualPDF, ProcessingJob, Company
from src.services.pdf_generator import ManualPDFGenerator
from src.middleware.auth import require_authentication
from datetime import datetime
import os
import tempfile
import logging
import json

logger = logging.getLogger(__name__)

pdf_bp = Blueprint('pdf', __name__, url_prefix='/api/manuals')


@pdf_bp.route('/<int:manual_id>/pdf', methods=['POST'])
@require_authentication
def generate_pdf(manual_id):
    """
    Generate PDF from manual
    
    POST /api/manuals/{manual_id}/pdf
    Body: {
        "language_code": "ja",  # Optional: Use translated version
        "config": {
            "include_toc": true,
            "include_page_numbers": true,
            "font_size": "12pt"
        }
    }
    
    Response: {
        "pdf": {
            "id": 1,
            "manual_id": 123,
            "filename": "manual_123_ja.pdf",
            "generation_status": "pending"
        },
        "message": "PDF generation started"
    }
    """
    try:
        company_id = session.get('company_id')
        if not company_id:
            return {'error': 'Not authenticated'}, 401
        
        # Get manual
        manual = Manual.query.filter_by(id=manual_id, company_id=company_id).first()
        if not manual:
            return {'error': 'Manual not found'}, 404
        
        # Parse request data
        data = request.get_json() or {}
        language_code = data.get('language_code', 'ja')
        config = data.get('config', {})
        
        # Check if PDF already exists for this language
        existing_pdf = ManualPDF.query.filter_by(
            manual_id=manual_id,
            language_code=language_code,
            generation_status='completed'
        ).first()
        
        if existing_pdf:
            return {
                'pdf': existing_pdf.to_dict(),
                'message': 'PDF already exists',
                'regenerate': False
            }, 200
        
        # Create new PDF record
        filename = f"manual_{manual_id}_{language_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # For now, store locally until S3 integration
        pdf_dir = os.path.join('instance', 'pdfs', str(company_id))
        os.makedirs(pdf_dir, exist_ok=True)
        file_path = os.path.join(pdf_dir, filename)
        
        pdf_record = ManualPDF(
            manual_id=manual_id,
            language_code=language_code,
            filename=filename,
            file_path=file_path,
            generation_config=json.dumps(config) if config else None,
            generation_status='pending'
        )
        
        db.session.add(pdf_record)
        db.session.commit()
        
        # Generate PDF synchronously for now (async in Phase 8)
        try:
            pdf_record.generation_status = 'processing'
            db.session.commit()
            
            # Prepare manual data for PDF generator
            manual_data = {
                'title': manual.title,
                'content': manual.content,
                'description': manual.description,
                'created_at': manual.created_at.isoformat() if manual.created_at else None,
                'analysis_result': {
                    'work_type': manual.title,
                    'summary': manual.description or '',
                    'steps': []
                }
            }
            
            # Parse content for steps if available
            if manual.content:
                # Simple parsing - improve this based on actual content structure
                lines = manual.content.split('\n')
                step_num = 1
                current_step = None
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('##') or line.startswith('手順'):
                        if current_step:
                            manual_data['analysis_result']['steps'].append(current_step)
                        current_step = {
                            'step_number': step_num,
                            'title': line.replace('#', '').replace('手順', '').strip(),
                            'description': '',
                            'key_points': [],
                            'timestamp_start': 0,
                            'timestamp_end': 0
                        }
                        step_num += 1
                    elif current_step and line:
                        if not current_step['description']:
                            current_step['description'] = line
                        else:
                            current_step['description'] += '\n' + line
                
                if current_step:
                    manual_data['analysis_result']['steps'].append(current_step)
            
            # Generate PDF using existing generator
            pdf_gen = ManualPDFGenerator()
            success = pdf_gen.generate_pdf(manual_data, file_path)
            
            if success:
                # Get file size
                file_size = os.path.getsize(file_path)
                
                pdf_record.generation_status = 'completed'
                pdf_record.file_size = file_size
                
                # TODO: Count pages (requires PyPDF2)
                pdf_record.page_count = 1
                
                db.session.commit()
                
                return {
                    'pdf': pdf_record.to_dict(),
                    'message': 'PDF generated successfully'
                }, 201
            else:
                pdf_record.generation_status = 'failed'
                db.session.commit()
                return {'error': 'PDF generation failed'}, 500
                
        except Exception as e:
            logger.error(f"PDF generation error: {str(e)}")
            pdf_record.generation_status = 'failed'
            db.session.commit()
            return {'error': f'PDF generation failed: {str(e)}'}, 500
        
    except Exception as e:
        logger.error(f"Error in generate_pdf: {str(e)}")
        return {'error': str(e)}, 500


@pdf_bp.route('/<int:manual_id>/pdf/<int:pdf_id>/status', methods=['GET'])
@require_authentication
def get_pdf_status(manual_id, pdf_id):
    """
    Get PDF generation status
    
    GET /api/manuals/{manual_id}/pdf/{pdf_id}/status
    
    Response: {
        "id": 1,
        "generation_status": "completed",
        "file_size": 1024000,
        "download_url": "/api/manuals/123/pdf/1/download"
    }
    """
    try:
        company_id = session.get('company_id')
        if not company_id:
            return {'error': 'Not authenticated'}, 401
        
        # Get PDF record
        pdf_record = ManualPDF.query.filter_by(id=pdf_id, manual_id=manual_id).first()
        if not pdf_record:
            return {'error': 'PDF not found'}, 404
        
        # Verify manual belongs to company
        manual = Manual.query.filter_by(id=manual_id, company_id=company_id).first()
        if not manual:
            return {'error': 'Manual not found'}, 404
        
        response = pdf_record.to_dict()
        if pdf_record.generation_status == 'completed':
            response['download_url'] = f'/api/manuals/{manual_id}/pdf/{pdf_id}/download'
        
        return response, 200
        
    except Exception as e:
        logger.error(f"Error in get_pdf_status: {str(e)}")
        return {'error': str(e)}, 500


@pdf_bp.route('/<int:manual_id>/pdf/<int:pdf_id>/download', methods=['GET'])
@require_authentication
def download_pdf(manual_id, pdf_id):
    """
    Download PDF file
    
    GET /api/manuals/{manual_id}/pdf/{pdf_id}/download
    
    Response: PDF file download with proper headers
    """
    try:
        company_id = session.get('company_id')
        if not company_id:
            return {'error': 'Not authenticated'}, 401
        
        # Get PDF record
        pdf_record = ManualPDF.query.filter_by(id=pdf_id, manual_id=manual_id).first()
        if not pdf_record:
            return {'error': 'PDF not found'}, 404
        
        # Verify manual belongs to company
        manual = Manual.query.filter_by(id=manual_id, company_id=company_id).first()
        if not manual:
            return {'error': 'Manual not found'}, 404
        
        # Check if PDF is ready
        if pdf_record.generation_status != 'completed':
            return {'error': f'PDF generation not completed. Status: {pdf_record.generation_status}'}, 400
        
        # Check if file exists
        if not os.path.exists(pdf_record.file_path):
            return {'error': 'PDF file not found on server'}, 404
        
        # Send file
        return send_file(
            pdf_record.file_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=pdf_record.filename
        )
        
    except Exception as e:
        logger.error(f"Error in download_pdf: {str(e)}")
        return {'error': str(e)}, 500


@pdf_bp.route('/<int:manual_id>/pdfs', methods=['GET'])
@require_authentication
def list_manual_pdfs(manual_id):
    """
    List all PDFs for a manual
    
    GET /api/manuals/{manual_id}/pdfs
    
    Response: {
        "pdfs": [
            {
                "id": 1,
                "language_code": "ja",
                "filename": "manual_123_ja.pdf",
                "generation_status": "completed",
                "created_at": "2025-01-05T10:30:00+09:00"
            }
        ]
    }
    """
    try:
        company_id = session.get('company_id')
        if not company_id:
            return {'error': 'Not authenticated'}, 401
        
        # Verify manual belongs to company
        manual = Manual.query.filter_by(id=manual_id, company_id=company_id).first()
        if not manual:
            return {'error': 'Manual not found'}, 404
        
        # Get all PDFs for this manual
        pdfs = ManualPDF.query.filter_by(manual_id=manual_id).order_by(ManualPDF.created_at.desc()).all()
        
        return {
            'pdfs': [pdf.to_dict() for pdf in pdfs],
            'total': len(pdfs)
        }, 200
        
    except Exception as e:
        logger.error(f"Error in list_manual_pdfs: {str(e)}")
        return {'error': str(e)}, 500
