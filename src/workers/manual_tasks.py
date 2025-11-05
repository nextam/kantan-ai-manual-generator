"""
File: manual_tasks.py
Purpose: Celery tasks for async manual generation with RAG enhancement
Main functionality: Background processing for manual generation
Dependencies: Celery, GeminiService, RAGProcessor, ElasticSearch
"""

from src.workers.celery_app import celery_app
from src.models.models import db, Manual, ProcessingJob, ManualTemplate
from src.services.gemini_service import GeminiService
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name='manual_tasks.process_manual_generation')
def process_manual_generation_task(self, job_id):
    """
    Process manual generation with RAG enhancement
    
    Args:
        job_id: ProcessingJob ID
    """
    try:
        # Get job from database
        job = ProcessingJob.query.get(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return {'error': 'Job not found'}
        
        # Update job status
        job.job_status = 'processing'
        job.started_at = datetime.utcnow()
        job.progress = 0
        job.current_step = 'Initializing manual generation'
        db.session.commit()
        
        # Get manual record
        manual_id = job.resource_id
        manual = Manual.query.get(manual_id)
        
        if not manual:
            job.job_status = 'failed'
            job.error_message = 'Manual record not found'
            db.session.commit()
            return {'error': 'Manual not found'}
        
        # Update manual status
        manual.generation_status = 'processing'
        db.session.commit()
        
        # Parse job parameters
        params = json.loads(job.job_params) if job.job_params else {}
        video_uri = params.get('video_uri')
        template_content = params.get('template_content', {})
        rag_context = params.get('rag_context')
        use_rag = params.get('use_rag', False)
        
        # Step 1: Extract video content with Gemini
        job.current_step = 'Analyzing video content'
        job.progress = 20
        db.session.commit()
        
        try:
            from src.services.gemini_service import GeminiService
            gemini_service = GeminiService()
            
            # Build comprehensive prompt with RAG context
            base_prompt = build_manual_generation_prompt(
                video_uri=video_uri,
                template_content=template_content,
                rag_context=rag_context if use_rag else None
            )
            
            logger.info(f"Generating manual content for manual {manual_id}")
            logger.info(f"Video URI: {video_uri}")
            logger.info(f"RAG enabled: {use_rag}")
            
            # Call Gemini API to generate comprehensive manual
            # The generate_comprehensive_manual method expects video_uris (list) and other parameters
            manual_content_result = gemini_service.generate_comprehensive_manual(
                video_uris=[video_uri],
                custom_prompt=base_prompt,
                include_images=template_content.get('include_images', False)
            )
            
            # Extract content from result
            if isinstance(manual_content_result, dict):
                manual_content = manual_content_result.get('content', '')
                if not manual_content:
                    # Try alternative keys
                    manual_content = (
                        manual_content_result.get('html_content') or
                        manual_content_result.get('manual_content') or
                        str(manual_content_result)
                    )
            else:
                manual_content = str(manual_content_result)
            
            job.current_step = 'Processing generated content'
            job.progress = 70
            db.session.commit()
            
        except Exception as gemini_error:
            logger.error(f"Gemini generation failed: {str(gemini_error)}")
            job.job_status = 'failed'
            job.error_message = f'Gemini API error: {str(gemini_error)}'
            manual.generation_status = 'failed'
            manual.error_message = str(gemini_error)
            db.session.commit()
            return {'error': str(gemini_error)}
        
        # Step 2: Format and save manual content
        job.current_step = 'Saving manual content'
        job.progress = 90
        db.session.commit()
        
        try:
            # Save manual content
            manual.content = manual_content
            manual.generation_status = 'completed'
            
            # Store RAG sources if used
            if use_rag and rag_context:
                manual.rag_sources = json.dumps({
                    'sources_count': rag_context.get('total_results', 0),
                    'materials': [
                        {
                            'material_id': src.get('material_id'),
                            'title': src.get('material_title'),
                            'relevance': src.get('relevance_score')
                        }
                        for src in rag_context.get('reference_materials', [])
                    ]
                })
            
            manual.completed_at = datetime.utcnow()
            
        except Exception as save_error:
            logger.error(f"Failed to save manual content: {str(save_error)}")
            job.job_status = 'failed'
            job.error_message = f'Save error: {str(save_error)}'
            manual.generation_status = 'failed'
            db.session.commit()
            return {'error': str(save_error)}
        
        # Complete job
        job.job_status = 'completed'
        job.progress = 100
        job.current_step = 'Manual generation completed'
        job.completed_at = datetime.utcnow()
        job.result_data = json.dumps({
            'manual_id': manual.id,
            'content_length': len(manual_content) if manual_content else 0,
            'rag_used': use_rag,
            'rag_sources_count': rag_context.get('total_results', 0) if rag_context else 0
        })
        
        db.session.commit()
        
        logger.info(f"Manual generation completed for manual {manual_id}")
        
        return {
            'status': 'success',
            'manual_id': manual.id,
            'job_id': job.id
        }
        
    except Exception as e:
        logger.error(f"Manual generation task failed: {str(e)}")
        
        # Update job status
        try:
            job = ProcessingJob.query.get(job_id)
            if job:
                job.job_status = 'failed'
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                
                # Update manual status
                if job.resource_id:
                    manual = Manual.query.get(job.resource_id)
                    if manual:
                        manual.generation_status = 'failed'
                        manual.error_message = str(e)
                
                db.session.commit()
        except:
            pass
        
        return {'error': str(e)}


def build_manual_generation_prompt(video_uri, template_content, rag_context=None):
    """
    Build comprehensive prompt for manual generation
    
    Args:
        video_uri: URI of the video to analyze
        template_content: Template structure
        rag_context: RAG search results (optional)
    
    Returns:
        Formatted prompt string
    """
    prompt_parts = []
    
    # Base instruction
    prompt_parts.append("""
You are an expert technical writer creating a manufacturing process manual.
Analyze the provided video and create a detailed, step-by-step manual following the template structure.
""")
    
    # Add RAG context if available
    if rag_context and rag_context.get('reference_materials'):
        prompt_parts.append("\n## Reference Materials\n")
        prompt_parts.append(
            "Use the following reference materials to enhance accuracy and include relevant details:\n"
        )
        
        for idx, material in enumerate(rag_context['reference_materials'], 1):
            prompt_parts.append(f"\n### Reference {idx}: {material.get('material_title', 'Unknown')}\n")
            prompt_parts.append(f"Relevance Score: {material.get('relevance_score', 0):.2f}\n")
            prompt_parts.append(f"Content:\n{material.get('chunk_text', '')}\n")
            
            if material.get('metadata'):
                prompt_parts.append(f"Metadata: {json.dumps(material['metadata'])}\n")
        
        prompt_parts.append("""
\nIMPORTANT: Incorporate relevant information from these reference materials into your manual.
Cite sources where appropriate (e.g., "As per safety guidelines in Reference 1...").
""")
    
    # Add template structure
    if template_content:
        prompt_parts.append("\n## Template Structure\n")
        prompt_parts.append("Follow this structure for the manual:\n")
        prompt_parts.append(json.dumps(template_content, indent=2))
    
    # Add video analysis instruction
    prompt_parts.append("""
\n## Video Analysis Instructions

1. Watch the entire video carefully
2. Identify all distinct steps in the process
3. Note safety considerations and precautions
4. Identify required tools and materials
5. Capture timing information for each step
6. Document quality checkpoints

## Output Format

Provide the manual in structured JSON format following the template structure.
Include:
- Clear step-by-step instructions
- Timestamps for each step
- Safety warnings where applicable
- Quality check points
- Required tools and materials

Ensure the manual is:
- Clear and concise
- Technically accurate
- Easy to follow
- Complete and comprehensive
""")
    
    return '\n'.join(prompt_parts)
