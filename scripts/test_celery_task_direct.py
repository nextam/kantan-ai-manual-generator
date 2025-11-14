"""
File: test_celery_task_direct.py
Purpose: Test if Celery task can be triggered manually
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.workers.manual_tasks import process_manual_generation_task

# Try to trigger task for Job ID 29
print("🔄 Triggering task for Job ID 29...")
try:
    result = process_manual_generation_task.delay(29)
    print(f"✅ Task triggered: {result.id}")
    print(f"📊 Task state: {result.state}")
    
    import time
    print(f"\n⏳ Waiting for task to complete...")
    for i in range(30):
        time.sleep(2)
        print(f"  [{i+1}/30] State: {result.state}")
        if result.state in ['SUCCESS', 'FAILURE']:
            break
    
    if result.state == 'SUCCESS':
        print(f"✅ Task completed successfully")
    elif result.state == 'FAILURE':
        print(f"❌ Task failed: {result.result}")
    else:
        print(f"⏸️  Task still {result.state}")
except Exception as e:
    print(f"❌ Task trigger failed: {e}")
    import traceback
    traceback.print_exc()
