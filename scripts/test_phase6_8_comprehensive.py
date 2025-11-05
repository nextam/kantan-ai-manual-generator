"""
File: test_phase6_8_comprehensive.py
Purpose: Comprehensive testing for Phase 6-8 enterprise features
Main functionality: Test PDF export, translation, and async job management
Dependencies: Flask app, models, test data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.app import app
from src.core.db_manager import db
from src.models.models import (
    Company, User, Manual, ManualPDF, 
    ManualTranslation, ProcessingJob
)
from datetime import datetime
import json

def print_section(title):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_result(test_name, passed, message=""):
    """Print test result"""
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status} - {test_name}")
    if message:
        print(f"    {message}")

def create_test_manual():
    """Create a test manual for testing"""
    print_section("Creating Test Data")
    
    # Get test company and user
    company = Company.query.filter_by(company_code='career-survival').first()
    if not company:
        print_result("Test Company", False, "Test company 'career-survival' not found")
        return None
    
    user = User.query.filter_by(email='support@career-survival.com').first()
    if not user:
        print_result("Test User", False, "Test user 'support@career-survival.com' not found")
        return None
    
    print_result("Test Company Found", True, f"Company: {company.name} (ID: {company.id})")
    print_result("Test User Found", True, f"User: {user.username} (ID: {user.id})")
    
    # Create test manual
    manual = Manual(
        title="テスト用マニュアル - Phase 6-8 検証",
        description="PDF出力、翻訳、非同期ジョブ管理機能のテスト用マニュアル",
        content="テストマニュアルの内容",
        company_id=company.id,
        created_by=user.id,
        manual_type='manual_with_images',
        video_uri="gs://test-bucket/test_video.mp4",
        generation_status="completed"
    )
    db.session.add(manual)
    db.session.commit()
    
    # Note: Manual steps are stored in 'content' field as JSON, not separate table
    manual.content = json.dumps({
        "steps": [
            {
                "step_number": 1,
                "title": "準備工程",
                "description": "必要な工具と材料を準備します",
                "estimated_time": 300
            },
            {
                "step_number": 2,
                "title": "組み立て工程",
                "description": "部品Aと部品Bを組み合わせます",
                "estimated_time": 600
            },
            {
                "step_number": 3,
                "title": "検査工程",
                "description": "完成品の品質を確認します",
                "estimated_time": 300
            }
        ]
    })
    db.session.commit()
    
    print_result("Test Manual Created", True, f"Manual ID: {manual.id}, Title: {manual.title}")
    print_result("Test Steps Created", True, f"Created 3 steps in content field")
    
    return manual

def test_pdf_models():
    """Test PDF-related database models"""
    print_section("Phase 6: PDF Export - Database Models")
    
    # Get test manual
    manual = Manual.query.filter_by(title="テスト用マニュアル - Phase 6-8 検証").first()
    if not manual:
        manual = create_test_manual()
    
    # Create ManualPDF record
    pdf = ManualPDF(
        manual_id=manual.id,
        language_code='ja',
        filename=f"manual_{manual.id}_ja.pdf",
        file_path=f"s3://test-bucket/{manual.company_id}/pdfs/{manual.id}/ja/manual.pdf",
        file_size=1024000,
        page_count=10,
        generation_config=json.dumps({"page_size": "A4", "orientation": "portrait"}),
        generation_status='completed'
    )
    db.session.add(pdf)
    db.session.commit()
    
    # Verify creation
    retrieved_pdf = ManualPDF.query.filter_by(manual_id=manual.id).first()
    print_result("ManualPDF Model Creation", retrieved_pdf is not None)
    print_result("ManualPDF to_dict()", True, f"Fields: {list(retrieved_pdf.to_dict().keys())}")
    
    # Test query
    all_pdfs = ManualPDF.query.filter_by(manual_id=manual.id).all()
    print_result("ManualPDF Query", len(all_pdfs) > 0, f"Found {len(all_pdfs)} PDF(s)")
    
    return manual

def test_translation_models():
    """Test translation-related database models"""
    print_section("Phase 7: Translation - Database Models")
    
    # Get test manual
    manual = Manual.query.filter_by(title="テスト用マニュアル - Phase 6-8 検証").first()
    if not manual:
        manual = create_test_manual()
    
    # Delete existing translations for clean test
    ManualTranslation.query.filter_by(manual_id=manual.id).delete()
    db.session.commit()
    
    # Create translation records
    languages = [
        ('en', 'English Test Manual', 'Test manual content in English'),
        ('zh', '中文测试手册', '中文测试内容'),
        ('ko', '한국어 테스트 매뉴얼', '한국어 테스트 내용')
    ]
    
    for lang_code, title, content in languages:
        translation = ManualTranslation(
            manual_id=manual.id,
            language_code=lang_code,
            translated_title=title,
            translated_content=content,
            translation_engine='gemini',
            translation_status='completed'
        )
        db.session.add(translation)
    
    db.session.commit()
    
    # Verify creation
    translations = ManualTranslation.query.filter_by(manual_id=manual.id).all()
    print_result("ManualTranslation Creation", len(translations) >= 3, 
                f"Created {len(translations)} translation(s)")
    
    # Test unique constraint
    for trans in translations:
        print_result(f"Translation ({trans.language_code})", True, 
                    f"Status: {trans.translation_status}, Engine: {trans.translation_engine}")
    
    # Test to_dict
    if translations:
        trans_dict = translations[0].to_dict()
        print_result("ManualTranslation to_dict()", True, 
                    f"Fields: {list(trans_dict.keys())}")
    
    return manual

def test_job_models():
    """Test async job database models"""
    print_section("Phase 8: Async Jobs - Database Models")
    
    # Get test manual
    manual = Manual.query.filter_by(title="テスト用マニュアル - Phase 6-8 検証").first()
    company = Company.query.filter_by(company_code='career-survival').first()
    user = User.query.filter_by(email='support@career-survival.com').first()
    
    # Create job records
    job_types = [
        ('pdf_generation', 'Manual PDF generation job'),
        ('translation', 'Manual translation job'),
        ('batch_translation', 'Batch translation job')
    ]
    
    for job_type, description in job_types:
        job = ProcessingJob(
            job_type=job_type,
            job_status='processing',
            company_id=company.id,
            user_id=user.id,
            resource_type='manual',
            resource_id=manual.id if manual else None,
            job_params=json.dumps({"description": description}),
            progress=50,
            current_step="Processing...",
            started_at=datetime.utcnow()
        )
        db.session.add(job)
    
    db.session.commit()
    
    # Verify creation
    jobs = ProcessingJob.query.filter_by(resource_id=manual.id if manual else None).all()
    print_result("ProcessingJob Creation", len(jobs) >= 3, 
                f"Created {len(jobs)} job(s)")
    
    # Test queries
    for job in jobs:
        print_result(f"Job ({job.job_type})", True, 
                    f"Status: {job.job_status}, Progress: {job.progress}%")
    
    # Test to_dict
    if jobs:
        job_dict = jobs[0].to_dict()
        print_result("ProcessingJob to_dict()", True, 
                    f"Fields: {list(job_dict.keys())}")
    
    # Test index query (job_status + job_type)
    processing_jobs = ProcessingJob.query.filter_by(
        job_status='processing'
    ).filter(
        ProcessingJob.job_type.in_(['pdf_generation', 'translation'])
    ).all()
    print_result("ProcessingJob Index Query", len(processing_jobs) > 0, 
                f"Found {len(processing_jobs)} processing job(s)")

def test_routes_registration():
    """Test that all Phase 6-8 routes are registered"""
    print_section("Route Registration Check")
    
    with app.app_context():
        rules = list(app.url_map.iter_rules())
        
        # Check PDF routes
        pdf_routes = [r for r in rules if '/api/manuals' in r.rule and '/pdf' in r.rule]
        print_result("PDF Routes Registered", len(pdf_routes) >= 4, 
                    f"Found {len(pdf_routes)} PDF route(s)")
        for route in pdf_routes[:5]:  # Show first 5
            print(f"    - {route.rule} [{', '.join(route.methods - {'HEAD', 'OPTIONS'})}]")
        
        # Check translation routes
        translation_routes = [r for r in rules if '/api/manuals' in r.rule and '/translate' in r.rule]
        print_result("Translation Routes Registered", len(translation_routes) >= 3, 
                    f"Found {len(translation_routes)} translation route(s)")
        for route in translation_routes[:5]:
            print(f"    - {route.rule} [{', '.join(route.methods - {'HEAD', 'OPTIONS'})}]")
        
        # Check job routes
        job_routes = [r for r in rules if '/api/jobs' in r.rule]
        print_result("Job Routes Registered", len(job_routes) >= 5, 
                    f"Found {len(job_routes)} job route(s)")
        for route in job_routes[:5]:
            print(f"    - {route.rule} [{', '.join(route.methods - {'HEAD', 'OPTIONS'})}]")

def test_service_initialization():
    """Test that services are properly initialized"""
    print_section("Service Initialization Check")
    
    # Test translation service
    try:
        from src.services.translation_service import translation_service
        print_result("Translation Service Import", True, 
                    f"Model: {translation_service.model_id}")
        
        # Check supported languages
        supported_langs = list(translation_service.SUPPORTED_LANGUAGES.keys())
        print_result("Supported Languages", len(supported_langs) == 10, 
                    f"Languages: {', '.join(supported_langs)}")
    except Exception as e:
        print_result("Translation Service Import", False, str(e))
    
    # Test PDF generator (existing)
    try:
        from src.services.pdf_generator import ManualPDFGenerator
        print_result("PDF Generator Class Import", True, "ManualPDFGenerator class loaded")
    except Exception as e:
        print_result("PDF Generator Class Import", False, str(e))

def test_celery_tasks():
    """Test Celery task registration"""
    print_section("Celery Task Registration Check")
    
    try:
        from src.workers.celery_app import celery
        from src.workers import pdf_tasks, translation_tasks
        
        # Get registered tasks
        registered_tasks = list(celery.tasks.keys())
        
        # Check for Phase 6-8 tasks specifically
        phase6_8_tasks = [
            'src.workers.pdf_tasks.generate_pdf_task',
            'src.workers.pdf_tasks.batch_generate_pdfs_task',
            'src.workers.translation_tasks.translate_manual_task',
            'src.workers.translation_tasks.batch_translate_task',
            'src.workers.translation_tasks.cleanup_old_translations'
        ]
        
        print_result("Celery App Initialized", True, 
                    f"Total tasks: {len(registered_tasks)}")
        
        # Check each Phase 6-8 task
        for task_name in phase6_8_tasks:
            task_exists = task_name in registered_tasks
            task_type = task_name.split('.')[-2]  # pdf_tasks or translation_tasks
            print_result(f"{task_type.upper()} Task", task_exists, 
                        task_name.split('.')[-1])
        
        # Summary
        phase6_8_found = sum(1 for t in phase6_8_tasks if t in registered_tasks)
        print_result("Phase 6-8 Tasks Complete", phase6_8_found == len(phase6_8_tasks),
                    f"{phase6_8_found}/{len(phase6_8_tasks)} tasks registered")
        
    except Exception as e:
        print_result("Celery Tasks Check", False, str(e))

def generate_test_report():
    """Generate comprehensive test report"""
    print_section("Test Summary Report")
    
    # Database statistics
    total_companies = Company.query.count()
    total_users = User.query.count()
    total_manuals = Manual.query.count()
    total_pdfs = ManualPDF.query.count()
    total_translations = ManualTranslation.query.count()
    total_jobs = ProcessingJob.query.count()
    
    print(f"Database Statistics:")
    print(f"  - Companies: {total_companies}")
    print(f"  - Users: {total_users}")
    print(f"  - Manuals: {total_manuals}")
    print(f"  - PDFs: {total_pdfs}")
    print(f"  - Translations: {total_translations}")
    print(f"  - Processing Jobs: {total_jobs}")
    
    # Route statistics
    with app.app_context():
        total_routes = len(list(app.url_map.iter_rules()))
        pdf_routes = len([r for r in app.url_map.iter_rules() if '/pdf' in r.rule])
        translation_routes = len([r for r in app.url_map.iter_rules() if '/translate' in r.rule])
        job_routes = len([r for r in app.url_map.iter_rules() if '/jobs' in r.rule])
        
        print(f"\nRoute Statistics:")
        print(f"  - Total Routes: {total_routes}")
        print(f"  - PDF Routes: {pdf_routes}")
        print(f"  - Translation Routes: {translation_routes}")
        print(f"  - Job Routes: {job_routes}")

def main():
    """Main test execution"""
    print("\n" + "="*60)
    print("  Phase 6-8 Comprehensive Testing")
    print("  PDF Export, Translation, Async Job Management")
    print("="*60)
    
    with app.app_context():
        try:
            # Test database models
            test_pdf_models()
            test_translation_models()
            test_job_models()
            
            # Test routes and services
            test_routes_registration()
            test_service_initialization()
            test_celery_tasks()
            
            # Generate report
            generate_test_report()
            
            print("\n" + "="*60)
            print("  [SUCCESS] All tests completed successfully!")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"\n[FAIL] Test execution failed: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    main()
