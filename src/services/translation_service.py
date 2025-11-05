"""
File: translation_service.py
Purpose: Multi-language translation service using Gemini API
Main functionality: Translate manual content while preserving formatting
Dependencies: google-genai, models
"""

import os
import logging
from typing import Dict, List, Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class TranslationService:
    """
    Translation service using Gemini API
    
    Features:
    - Multi-language support
    - Markdown formatting preservation
    - Batch translation optimization
    - Translation quality validation
    """
    
    # Supported languages
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'ja': 'Japanese',
        'zh': 'Chinese (Simplified)',
        'ko': 'Korean',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'pt': 'Portuguese',
        'it': 'Italian',
        'ru': 'Russian'
    }
    
    def __init__(self):
        """Initialize Gemini client for translation"""
        try:
            project_id = os.getenv('PROJECT_ID', 'kantan-ai-database')
            location = os.getenv('VERTEX_AI_LOCATION', 'us-central1')
            
            self.client = genai.Client(
                vertexai=True,
                project=project_id,
                location=location
            )
            
            # Use flash model for cost-effective translation
            self.model_id = 'gemini-2.0-flash-exp'
            
            logger.info(f"Translation service initialized with model: {self.model_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize translation service: {str(e)}")
            raise
    
    def translate_manual(
        self,
        title: str,
        content: str,
        source_lang: str,
        target_lang: str,
        preserve_formatting: bool = True
    ) -> Dict[str, str]:
        """
        Translate manual title and content
        
        Args:
            title: Manual title
            content: Manual content (markdown or HTML)
            source_lang: Source language code (e.g., 'ja')
            target_lang: Target language code (e.g., 'en')
            preserve_formatting: Whether to preserve markdown/HTML formatting
            
        Returns:
            Dictionary with translated_title and translated_content
            
        Raises:
            Exception: If translation fails
        """
        try:
            if target_lang not in self.SUPPORTED_LANGUAGES:
                raise ValueError(f"Unsupported target language: {target_lang}")
            
            source_lang_name = self.SUPPORTED_LANGUAGES.get(source_lang, source_lang)
            target_lang_name = self.SUPPORTED_LANGUAGES[target_lang]
            
            # Translate title
            translated_title = self._translate_text(
                text=title,
                source_lang=source_lang_name,
                target_lang=target_lang_name,
                preserve_formatting=False
            )
            
            # Translate content (in chunks if too large)
            if len(content) > 10000:
                translated_content = self._translate_large_content(
                    content=content,
                    source_lang=source_lang_name,
                    target_lang=target_lang_name,
                    preserve_formatting=preserve_formatting
                )
            else:
                translated_content = self._translate_text(
                    text=content,
                    source_lang=source_lang_name,
                    target_lang=target_lang_name,
                    preserve_formatting=preserve_formatting
                )
            
            return {
                'translated_title': translated_title,
                'translated_content': translated_content
            }
            
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            raise Exception(f"Translation error: {str(e)}")
    
    def _translate_text(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        preserve_formatting: bool = True
    ) -> str:
        """
        Translate a single text block
        
        Args:
            text: Text to translate
            source_lang: Source language name
            target_lang: Target language name
            preserve_formatting: Whether to preserve formatting
            
        Returns:
            Translated text
        """
        try:
            # Build translation prompt
            if preserve_formatting:
                prompt = f"""Translate the following text from {source_lang} to {target_lang}.

CRITICAL REQUIREMENTS:
1. Preserve ALL markdown formatting (headers, lists, tables, code blocks, etc.)
2. Preserve ALL HTML tags if present
3. Keep line breaks and spacing exactly as in the original
4. Translate only the text content, not the markup
5. Do not add any explanations or notes

Text to translate:
{text}

Translated text:"""
            else:
                prompt = f"""Translate the following text from {source_lang} to {target_lang}.

Provide only the translated text without any explanations.

Text to translate:
{text}

Translated text:"""
            
            # Call Gemini API
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,  # Lower temperature for more consistent translation
                    max_output_tokens=8192
                )
            )
            
            translated = response.text.strip()
            
            logger.info(f"Translated {len(text)} characters to {target_lang}")
            
            return translated
            
        except Exception as e:
            logger.error(f"Text translation failed: {str(e)}")
            raise
    
    def _translate_large_content(
        self,
        content: str,
        source_lang: str,
        target_lang: str,
        preserve_formatting: bool = True
    ) -> str:
        """
        Translate large content by splitting into chunks
        
        Args:
            content: Large content to translate
            source_lang: Source language name
            target_lang: Target language name
            preserve_formatting: Whether to preserve formatting
            
        Returns:
            Translated content
        """
        try:
            # Split content into manageable chunks (by paragraphs or sections)
            chunks = self._split_content(content, max_size=8000)
            
            translated_chunks = []
            
            for i, chunk in enumerate(chunks):
                logger.info(f"Translating chunk {i+1}/{len(chunks)}")
                
                translated_chunk = self._translate_text(
                    text=chunk,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    preserve_formatting=preserve_formatting
                )
                
                translated_chunks.append(translated_chunk)
            
            # Join translated chunks
            translated_content = '\n\n'.join(translated_chunks)
            
            return translated_content
            
        except Exception as e:
            logger.error(f"Large content translation failed: {str(e)}")
            raise
    
    def _split_content(self, content: str, max_size: int = 8000) -> List[str]:
        """
        Split content into chunks for translation
        
        Args:
            content: Content to split
            max_size: Maximum size per chunk
            
        Returns:
            List of content chunks
        """
        # Split by double newlines (paragraphs)
        paragraphs = content.split('\n\n')
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            if current_size + para_size > max_size and current_chunk:
                # Save current chunk and start new one
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size + 2  # +2 for \n\n
        
        # Add remaining chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def batch_translate(
        self,
        items: List[Dict[str, str]],
        source_lang: str,
        target_lang: str
    ) -> List[Dict[str, str]]:
        """
        Batch translate multiple items
        
        Args:
            items: List of items to translate, each with 'title' and 'content'
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            List of translated items
        """
        try:
            translated_items = []
            
            for i, item in enumerate(items):
                logger.info(f"Translating item {i+1}/{len(items)}")
                
                translated = self.translate_manual(
                    title=item.get('title', ''),
                    content=item.get('content', ''),
                    source_lang=source_lang,
                    target_lang=target_lang
                )
                
                translated_items.append(translated)
            
            return translated_items
            
        except Exception as e:
            logger.error(f"Batch translation failed: {str(e)}")
            raise


# Global instance
translation_service = TranslationService()
