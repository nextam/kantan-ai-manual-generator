"""
File: translation_routes.py
Purpose: API endpoints for manual translation
Main functionality: Translate manuals, check status, retrieve translations
Dependencies: Flask, models, translation_service
"""

from flask import Blueprint, request, jsonify, session
from src.models.models import db, Manual, ManualTranslation, ProcessingJob
from src.services.translation_service import translation_service
from src.middleware.auth import require_authentication
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

translation_bp = Blueprint('translation', __name__, url_prefix='/api/manuals')


@translation_bp.route('/<int:manual_id>/translate', methods=['POST'])
@require_authentication
def translate_manual(manual_id):
    """
    Translate manual to one or more languages
    
    POST /api/manuals/{manual_id}/translate
    Body: {
        "language_codes": ["en", "zh", "ko"]  # Multiple languages
    }
    
    Response: {
        "translations": [
            {
                "id": 1,
                "manual_id": 123,
                "language_code": "en",
                "translation_status": "pending"
            }
        ],
        "message": "Translation started for 3 languages"
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
        language_codes = data.get('language_codes', [])
        
        if not language_codes:
            return {'error': 'No language codes provided'}, 400
        
        # Validate language codes
        supported_langs = translation_service.SUPPORTED_LANGUAGES.keys()
        invalid_langs = [lang for lang in language_codes if lang not in supported_langs]
        
        if invalid_langs:
            return {
                'error': f'Unsupported languages: {", ".join(invalid_langs)}',
                'supported_languages': list(supported_langs)
            }, 400
        
        # Determine source language (default to Japanese)
        source_lang = 'ja'
        
        # Create translation records
        translations = []
        
        for lang_code in language_codes:
            # Check if translation already exists
            existing = ManualTranslation.query.filter_by(
                manual_id=manual_id,
                language_code=lang_code
            ).first()
            
            if existing and existing.translation_status == 'completed':
                translations.append(existing)
                continue
            
            # Create new translation record or update existing
            if existing:
                translation = existing
                translation.translation_status = 'pending'
            else:
                translation = ManualTranslation(
                    manual_id=manual_id,
                    language_code=lang_code,
                    translated_title='',
                    translated_content='',
                    translation_engine='gemini',
                    translation_status='pending'
                )
                db.session.add(translation)
            
            translations.append(translation)
        
        db.session.commit()
        
        # Perform translations synchronously for now (async in Phase 8)
        completed_count = 0
        failed_count = 0
        
        for translation in translations:
            if translation.translation_status == 'completed':
                completed_count += 1
                continue
            
            try:
                translation.translation_status = 'processing'
                db.session.commit()
                
                # Translate using Gemini
                result = translation_service.translate_manual(
                    title=manual.title,
                    content=manual.content,
                    source_lang=source_lang,
                    target_lang=translation.language_code,
                    preserve_formatting=True
                )
                
                # Save translation
                translation.translated_title = result['translated_title']
                translation.translated_content = result['translated_content']
                translation.translation_status = 'completed'
                
                db.session.commit()
                
                completed_count += 1
                logger.info(f"Translation completed for manual {manual_id} to {translation.language_code}")
                
            except Exception as e:
                logger.error(f"Translation failed for {translation.language_code}: {str(e)}")
                translation.translation_status = 'failed'
                db.session.commit()
                failed_count += 1
        
        return {
            'translations': [t.to_dict() for t in translations],
            'message': f'Translation completed: {completed_count} succeeded, {failed_count} failed',
            'total': len(translations),
            'completed': completed_count,
            'failed': failed_count
        }, 201
        
    except Exception as e:
        logger.error(f"Error in translate_manual: {str(e)}")
        return {'error': str(e)}, 500


@translation_bp.route('/<int:manual_id>/translations/<int:translation_id>/status', methods=['GET'])
@require_authentication
def get_translation_status(manual_id, translation_id):
    """
    Get translation status
    
    GET /api/manuals/{manual_id}/translations/{translation_id}/status
    
    Response: {
        "id": 1,
        "translation_status": "completed",
        "language_code": "en"
    }
    """
    try:
        company_id = session.get('company_id')
        if not company_id:
            return {'error': 'Not authenticated'}, 401
        
        # Get translation
        translation = ManualTranslation.query.filter_by(
            id=translation_id,
            manual_id=manual_id
        ).first()
        
        if not translation:
            return {'error': 'Translation not found'}, 404
        
        # Verify manual belongs to company
        manual = Manual.query.filter_by(id=manual_id, company_id=company_id).first()
        if not manual:
            return {'error': 'Manual not found'}, 404
        
        return translation.to_dict(), 200
        
    except Exception as e:
        logger.error(f"Error in get_translation_status: {str(e)}")
        return {'error': str(e)}, 500


@translation_bp.route('/<int:manual_id>/translations/<language_code>', methods=['GET'])
@require_authentication
def get_translated_manual(manual_id, language_code):
    """
    Get translated manual content
    
    GET /api/manuals/{manual_id}/translations/{language_code}
    
    Response: {
        "id": 1,
        "manual_id": 123,
        "language_code": "en",
        "translated_title": "Work Manual",
        "translated_content": "...",
        "translation_status": "completed"
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
        
        # Get translation
        translation = ManualTranslation.query.filter_by(
            manual_id=manual_id,
            language_code=language_code
        ).first()
        
        if not translation:
            return {'error': f'Translation not found for language: {language_code}'}, 404
        
        if translation.translation_status != 'completed':
            return {
                'error': f'Translation not completed. Status: {translation.translation_status}',
                'translation': translation.to_dict()
            }, 400
        
        # Return full translation data
        result = translation.to_dict()
        result['translated_content'] = translation.translated_content
        
        return result, 200
        
    except Exception as e:
        logger.error(f"Error in get_translated_manual: {str(e)}")
        return {'error': str(e)}, 500


@translation_bp.route('/<int:manual_id>/translations', methods=['GET'])
@require_authentication
def list_translations(manual_id):
    """
    List all translations for a manual
    
    GET /api/manuals/{manual_id}/translations
    
    Response: {
        "translations": [
            {
                "id": 1,
                "language_code": "en",
                "translated_title": "Work Manual",
                "translation_status": "completed"
            }
        ],
        "total": 1
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
        
        # Get all translations
        translations = ManualTranslation.query.filter_by(
            manual_id=manual_id
        ).order_by(ManualTranslation.created_at.desc()).all()
        
        return {
            'translations': [t.to_dict() for t in translations],
            'total': len(translations)
        }, 200
        
    except Exception as e:
        logger.error(f"Error in list_translations: {str(e)}")
        return {'error': str(e)}, 500


@translation_bp.route('/languages', methods=['GET'])
def get_supported_languages():
    """
    Get list of supported languages
    
    GET /api/manuals/languages
    
    Response: {
        "languages": {
            "en": "English",
            "ja": "Japanese",
            "zh": "Chinese (Simplified)",
            ...
        }
    }
    """
    try:
        return {
            'languages': translation_service.SUPPORTED_LANGUAGES
        }, 200
    except Exception as e:
        logger.error(f"Error in get_supported_languages: {str(e)}")
        return {'error': str(e)}, 500
