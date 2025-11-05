"""
File: translation_tasks.py
Purpose: Celery tasks for manual translation
Main functionality: Async translation processing
Dependencies: celery, translation_service, models
"""

from src.workers.celery_app import celery
from src.models.models import db, Manual, ManualTranslation, ProcessingJob
from src.services.translation_service import translation_service
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


@celery.task(bind=True, name='src.workers.translation_tasks.translate_manual_task')
def translate_manual_task(self, manual_id, language_code, source_lang='ja'):
    """
    Translate manual to target language (Celery task)
    
    Args:
        manual_id: ID of the manual to translate
        language_code: Target language code
        source_lang: Source language code (default: ja)
        
    Returns:
        Dictionary with translation_id and status
    """
    try:
        # Update task state
        self.update_state(state='PROGRESS', meta={'current': 0, 'total': 100, 'status': 'Starting translation'})
        
        # Get manual from database
        from src.core.app import app
        with app.app_context():
            manual = Manual.query.get(manual_id)
            if not manual:
                raise Exception(f'Manual {manual_id} not found')
            
            # Check if translation already exists
            translation = ManualTranslation.query.filter_by(
                manual_id=manual_id,
                language_code=language_code
            ).first()
            
            if not translation:
                translation = ManualTranslation(
                    manual_id=manual_id,
                    language_code=language_code,
                    translated_title='',
                    translated_content='',
                    translation_engine='gemini',
                    translation_status='processing'
                )
                db.session.add(translation)
            else:
                translation.translation_status = 'processing'
            
            db.session.commit()
            translation_id = translation.id
            
            # Update progress
            self.update_state(state='PROGRESS', meta={'current': 20, 'total': 100, 'status': 'Translating title'})
            
            # Translate using Gemini
            result = translation_service.translate_manual(
                title=manual.title,
                content=manual.content,
                source_lang=source_lang,
                target_lang=language_code,
                preserve_formatting=True
            )
            
            # Update progress
            self.update_state(state='PROGRESS', meta={'current': 90, 'total': 100, 'status': 'Saving translation'})
            
            # Save translation
            translation.translated_title = result['translated_title']
            translation.translated_content = result['translated_content']
            translation.translation_status = 'completed'
            
            db.session.commit()
            
            # Update progress to complete
            self.update_state(state='SUCCESS', meta={'current': 100, 'total': 100, 'status': 'Translation completed'})
            
            return {
                'translation_id': translation_id,
                'status': 'completed',
                'language_code': language_code
            }
            
    except Exception as e:
        logger.error(f"Translation task failed: {str(e)}")
        
        # Update translation record to failed
        try:
            from src.core.app import app
            with app.app_context():
                if 'translation_id' in locals():
                    translation = ManualTranslation.query.get(translation_id)
                    if translation:
                        translation.translation_status = 'failed'
                        db.session.commit()
        except:
            pass
        
        raise


@celery.task(bind=True, name='src.workers.translation_tasks.batch_translate_task')
def batch_translate_task(self, manual_id, language_codes, source_lang='ja'):
    """
    Translate manual to multiple languages
    
    Args:
        manual_id: ID of the manual to translate
        language_codes: List of target language codes
        source_lang: Source language code (default: ja)
        
    Returns:
        Dictionary with results for each language
    """
    try:
        # Update task state
        total_langs = len(language_codes)
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': total_langs, 'status': f'Starting batch translation to {total_langs} languages'}
        )
        
        results = []
        
        for i, lang_code in enumerate(language_codes):
            try:
                # Update progress
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': i,
                        'total': total_langs,
                        'status': f'Translating to {lang_code} ({i+1}/{total_langs})'
                    }
                )
                
                # Start translation task
                result = translate_manual_task.delay(manual_id, lang_code, source_lang)
                
                results.append({
                    'language_code': lang_code,
                    'task_id': result.id,
                    'status': 'pending'
                })
                
            except Exception as e:
                logger.error(f"Failed to start translation for {lang_code}: {str(e)}")
                results.append({
                    'language_code': lang_code,
                    'error': str(e),
                    'status': 'failed'
                })
        
        # Update progress to complete
        self.update_state(
            state='SUCCESS',
            meta={
                'current': total_langs,
                'total': total_langs,
                'status': f'Batch translation started for {total_langs} languages'
            }
        )
        
        return {
            'manual_id': manual_id,
            'total': len(results),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Batch translation task failed: {str(e)}")
        raise


@celery.task(name='src.workers.translation_tasks.cleanup_old_translations')
def cleanup_old_translations(days=90):
    """
    Clean up old failed translation records
    
    Args:
        days: Number of days to keep (default: 90)
        
    Returns:
        Number of records deleted
    """
    try:
        from src.core.app import app
        with app.app_context():
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            old_translations = ManualTranslation.query.filter(
                ManualTranslation.translation_status == 'failed',
                ManualTranslation.created_at < cutoff_date
            ).all()
            
            count = len(old_translations)
            
            for translation in old_translations:
                db.session.delete(translation)
            
            db.session.commit()
            
            logger.info(f"Cleaned up {count} old translation records")
            
            return {
                'deleted': count,
                'cutoff_date': cutoff_date.isoformat()
            }
            
    except Exception as e:
        logger.error(f"Translation cleanup failed: {str(e)}")
        raise
