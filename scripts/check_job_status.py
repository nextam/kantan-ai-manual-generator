"""
Check job and manual status
"""
from src.models.models import db, ProcessingJob, Manual
from src.core.app import app

app.app_context().push()

# Check latest jobs
jobs = ProcessingJob.query.order_by(ProcessingJob.id.desc()).limit(3).all()
print("===== Latest Processing Jobs =====")
for job in jobs:
    print(f"\nJob ID: {job.id}")
    print(f"  Resource ID: {job.resource_id}")
    print(f"  Status: {job.job_status}")
    print(f"  Progress: {job.progress}%")
    print(f"  Current Step: {job.current_step}")
    print(f"  Error: {job.error_message or 'None'}")
    print(f"  Started: {job.started_at}")
    print(f"  Completed: {job.completed_at}")

# Check latest manuals
manuals = Manual.query.order_by(Manual.id.desc()).limit(3).all()
print("\n\n===== Latest Manuals =====")
for manual in manuals:
    print(f"\nManual ID: {manual.id}")
    print(f"  Title: {manual.title}")
    print(f"  Status: {manual.generation_status}")
    print(f"  Progress: {manual.generation_progress}%")
    print(f"  Content Length: {len(manual.content) if manual.content else 0} chars")
    print(f"  Error: {manual.error_message or 'None'}")
    print(f"  Created: {manual.created_at}")
    print(f"  Completed: {manual.completed_at}")
