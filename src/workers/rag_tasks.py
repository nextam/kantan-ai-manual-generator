"""
File: rag_tasks.py
Purpose: Celery tasks for RAG processing
Main functionality: Async material processing, ElasticSearch indexing, job tracking
Dependencies: celery, SQLAlchemy models, RAG processor, ElasticSearch service
"""

from datetime import datetime
import traceback
import json

from src.workers.celery_app import celery
from src.models.models import db, ReferenceMaterial, ReferenceChunk, ProcessingJob
from src.services.rag_processor import rag_processor
from src.services.elasticsearch_service import elasticsearch_service


@celery.task(bind=True, name='src.workers.rag_tasks.process_material_task')
def process_material_task(self, material_id: int, job_id: int):
    """
    Process reference material asynchronously
    
    Steps:
    1. Update job status to 'processing'
    2. Download and extract text
    3. Generate metadata with Gemini
    4. Chunk text
    5. Generate embeddings
    6. Store chunks in database
    7. Index chunks in ElasticSearch
    8. Update material and job status
    
    Args:
        material_id: ReferenceMaterial.id
        job_id: ProcessingJob.id
    """
    
    # Import Flask app for context
    from app import app
    
    with app.app_context():
        try:
            # Step 1: Get material and job
            material = ReferenceMaterial.query.get(material_id)
            job = ProcessingJob.query.get(job_id)
            
            if not material or not job:
                raise Exception(f"Material {material_id} or Job {job_id} not found")
            
            # Update job status
            job.job_status = 'processing'
            job.started_at = datetime.utcnow()
            job.current_step = 'Initializing'
            db.session.commit()
            
            # Update material status
            material.processing_status = 'processing'
            material.processing_progress = 0
            db.session.commit()
            
            # Step 2: Process material with RAG pipeline
            job.current_step = 'Extracting text'
            job.progress = 10
            db.session.commit()
            
            result = rag_processor.process_material(
                material_id=material.id,
                company_id=material.company_id,
                file_path_s3=material.file_path,
                file_type=material.file_type,
                title=material.title
            )
            
            if not result['success']:
                raise Exception(result.get('error', 'Processing failed'))
            
            # Step 3: Store metadata
            job.current_step = 'Storing metadata'
            job.progress = 30
            material.processing_progress = 30
            db.session.commit()
            
            material.extracted_metadata = json.dumps({
                'extraction_metadata': result['extraction_metadata'],
                'gemini_metadata': result['gemini_metadata'],
                'text_length': result['extracted_text_length']
            }, ensure_ascii=False)
            db.session.commit()
            
            # Step 4: Store chunks in database
            job.current_step = 'Creating chunks'
            job.progress = 50
            material.processing_progress = 50
            db.session.commit()
            
            chunks = result['chunks']
            
            # Delete existing chunks (if reprocessing)
            ReferenceChunk.query.filter_by(material_id=material_id).delete()
            db.session.commit()
            
            # Create new chunks
            for chunk_data in chunks:
                chunk = ReferenceChunk(
                    material_id=material_id,
                    chunk_index=chunk_data['chunk_index'],
                    chunk_text=chunk_data['text'],
                    chunk_metadata=json.dumps(chunk_data['metadata'], ensure_ascii=False)
                )
                db.session.add(chunk)
            
            db.session.commit()
            
            # Step 5: Index in ElasticSearch
            job.current_step = 'Indexing in ElasticSearch'
            job.progress = 70
            material.processing_progress = 70
            db.session.commit()
            
            # Ensure ElasticSearch index exists
            elasticsearch_service.create_index()
            
            # Get chunks from database (to get IDs)
            db_chunks = ReferenceChunk.query.filter_by(
                material_id=material_id
            ).order_by(ReferenceChunk.chunk_index).all()
            
            # Index each chunk
            indexed_count = 0
            for db_chunk, chunk_data in zip(db_chunks, chunks):
                try:
                    elasticsearch_service.index_chunk(
                        chunk_id=db_chunk.id,
                        material_id=material.id,
                        company_id=material.company_id,
                        chunk_text=chunk_data['text'],
                        chunk_index=chunk_data['chunk_index'],
                        embedding=chunk_data['embedding'],
                        metadata=chunk_data['metadata']
                    )
                    
                    # Store ElasticSearch doc ID
                    db_chunk.elasticsearch_doc_id = f"chunk_{db_chunk.id}"
                    indexed_count += 1
                
                except Exception as e:
                    print(f"Failed to index chunk {db_chunk.id}: {e}")
            
            db.session.commit()
            
            # Step 6: Finalize
            job.current_step = 'Finalizing'
            job.progress = 95
            material.processing_progress = 95
            db.session.commit()
            
            # Update material
            material.processing_status = 'completed'
            material.processing_progress = 100
            material.elasticsearch_indexed = True
            material.elasticsearch_index_name = elasticsearch_service.index_name
            material.chunk_count = len(chunks)
            db.session.commit()
            
            # Update job
            job.job_status = 'completed'
            job.progress = 100
            job.completed_at = datetime.utcnow()
            job.current_step = 'Completed'
            job.result_data = json.dumps({
                'chunk_count': len(chunks),
                'indexed_count': indexed_count,
                'text_length': result['extracted_text_length']
            }, ensure_ascii=False)
            db.session.commit()
            
            return {
                'success': True,
                'material_id': material_id,
                'chunk_count': len(chunks),
                'indexed_count': indexed_count
            }
        
        except Exception as e:
            # Error handling
            error_msg = str(e)
            error_trace = traceback.format_exc()
            
            print(f"RAG processing failed for material {material_id}: {error_msg}")
            print(error_trace)
            
            try:
                # Update material
                material = ReferenceMaterial.query.get(material_id)
                if material:
                    material.processing_status = 'failed'
                    material.error_message = error_msg
                    db.session.commit()
                
                # Update job
                job = ProcessingJob.query.get(job_id)
                if job:
                    job.job_status = 'failed'
                    job.error_message = error_msg
                    job.completed_at = datetime.utcnow()
                    db.session.commit()
            
            except Exception as update_error:
                print(f"Failed to update error status: {update_error}")
            
            # Re-raise for Celery to handle
            raise


@celery.task(bind=True, name='src.workers.rag_tasks.reindex_material_task')
def reindex_material_task(self, material_id: int):
    """
    Reindex material in ElasticSearch
    
    This task only reindexes existing chunks, does not reprocess the file.
    Useful when ElasticSearch index settings change.
    
    Args:
        material_id: ReferenceMaterial.id
    """
    
    from app import app
    
    with app.app_context():
        try:
            material = ReferenceMaterial.query.get(material_id)
            if not material:
                raise Exception(f"Material {material_id} not found")
            
            # Get existing chunks
            chunks = ReferenceChunk.query.filter_by(
                material_id=material_id
            ).order_by(ReferenceChunk.chunk_index).all()
            
            if not chunks:
                raise Exception("No chunks found for this material")
            
            # Delete existing ElasticSearch documents
            elasticsearch_service.delete_material_chunks(material_id, material.company_id)
            
            # Ensure index exists
            elasticsearch_service.create_index()
            
            # Reindex chunks
            # Note: This requires embeddings to be stored somewhere
            # For now, this is a placeholder - embeddings need to be regenerated
            raise Exception("Reindexing requires re-running full RAG processing")
        
        except Exception as e:
            print(f"Reindexing failed for material {material_id}: {e}")
            raise


@celery.task(bind=True, name='src.workers.rag_tasks.cleanup_failed_jobs')
def cleanup_failed_jobs():
    """
    Cleanup failed jobs older than 7 days
    
    Periodic task (should be scheduled with celery beat)
    """
    
    from app import app
    
    with app.app_context():
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            # Find failed jobs older than cutoff
            failed_jobs = ProcessingJob.query.filter(
                ProcessingJob.job_status == 'failed',
                ProcessingJob.created_at < cutoff_date
            ).all()
            
            deleted_count = 0
            for job in failed_jobs:
                db.session.delete(job)
                deleted_count += 1
            
            db.session.commit()
            
            print(f"Cleaned up {deleted_count} failed jobs")
            return {'deleted_count': deleted_count}
        
        except Exception as e:
            print(f"Job cleanup failed: {e}")
            raise
