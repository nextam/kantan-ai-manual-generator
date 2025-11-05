"""
File: pdf_tasks.py
Purpose: Celery tasks for PDF generation
Main functionality: Async PDF generation from manuals
Dependencies: celery, pdf_generator, models
"""

from src.workers.celery_app import celery
from src.models.models import db, Manual, ManualPDF, ProcessingJob
from src.services.pdf_generator import ManualPDFGenerator
from datetime import datetime
import logging
import os
import json

logger = logging.getLogger(__name__)


@celery.task(bind=True, name='src.workers.pdf_tasks.generate_pdf_task')
def generate_pdf_task(self, manual_id, language_code='ja', config=None):
    """
    Generate PDF from manual (Celery task)
    
    Args:
        manual_id: ID of the manual
        language_code: Language code for the PDF
        config: Optional generation configuration
        
    Returns:
        Dictionary with pdf_id and status
    """
    try:
        # Update task state
        self.update_state(state='PROGRESS', meta={'current': 0, 'total': 100, 'status': 'Starting PDF generation'})
        
        # Get manual from database
        from src.core.app import app
        with app.app_context():
            manual = Manual.query.get(manual_id)
            if not manual:
                raise Exception(f'Manual {manual_id} not found')
            
            # Create PDF record
            filename = f"manual_{manual_id}_{language_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            pdf_dir = os.path.join('instance', 'pdfs', str(manual.company_id))
            os.makedirs(pdf_dir, exist_ok=True)
            file_path = os.path.join(pdf_dir, filename)
            
            pdf_record = ManualPDF(
                manual_id=manual_id,
                language_code=language_code,
                filename=filename,
                file_path=file_path,
                generation_config=json.dumps(config) if config else None,
                generation_status='processing'
            )
            
            db.session.add(pdf_record)
            db.session.commit()
            
            pdf_id = pdf_record.id
            
            # Update progress
            self.update_state(state='PROGRESS', meta={'current': 20, 'total': 100, 'status': 'Preparing manual data'})
            
            # Prepare manual data
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
            
            # Parse content for steps
            if manual.content:
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
            
            # Update progress
            self.update_state(state='PROGRESS', meta={'current': 50, 'total': 100, 'status': 'Generating PDF'})
            
            # Generate PDF
            pdf_gen = ManualPDFGenerator()
            success = pdf_gen.generate_pdf(manual_data, file_path)
            
            if not success:
                raise Exception('PDF generation failed')
            
            # Update progress
            self.update_state(state='PROGRESS', meta={'current': 90, 'total': 100, 'status': 'Finalizing'})
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Update PDF record
            pdf_record.generation_status = 'completed'
            pdf_record.file_size = file_size
            pdf_record.page_count = 1  # TODO: Count actual pages
            
            db.session.commit()
            
            # Update progress to complete
            self.update_state(state='SUCCESS', meta={'current': 100, 'total': 100, 'status': 'PDF generated successfully'})
            
            return {
                'pdf_id': pdf_id,
                'status': 'completed',
                'file_path': file_path,
                'file_size': file_size
            }
            
    except Exception as e:
        logger.error(f"PDF generation task failed: {str(e)}")
        
        # Update PDF record to failed
        try:
            from src.core.app import app
            with app.app_context():
                if 'pdf_id' in locals():
                    pdf_record = ManualPDF.query.get(pdf_id)
                    if pdf_record:
                        pdf_record.generation_status = 'failed'
                        db.session.commit()
        except:
            pass
        
        raise


@celery.task(name='src.workers.pdf_tasks.batch_generate_pdfs_task')
def batch_generate_pdfs_task(manual_ids, language_codes=['ja']):
    """
    Generate PDFs for multiple manuals
    
    Args:
        manual_ids: List of manual IDs
        language_codes: List of language codes
        
    Returns:
        Dictionary with results
    """
    try:
        results = []
        
        for manual_id in manual_ids:
            for lang_code in language_codes:
                try:
                    result = generate_pdf_task.delay(manual_id, lang_code)
                    results.append({
                        'manual_id': manual_id,
                        'language_code': lang_code,
                        'task_id': result.id,
                        'status': 'pending'
                    })
                except Exception as e:
                    results.append({
                        'manual_id': manual_id,
                        'language_code': lang_code,
                        'error': str(e),
                        'status': 'failed'
                    })
        
        return {
            'total': len(results),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Batch PDF generation failed: {str(e)}")
        raise
