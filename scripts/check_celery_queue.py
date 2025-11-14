"""
File: check_celery_queue.py
Purpose: Check Celery queue and inspect jobs
"""
import redis
from celery import Celery

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=1)

# Check queue length
queue_length = r.llen('default')
print(f"📊 Default queue length: {queue_length}")

# Get pending tasks
if queue_length > 0:
    tasks = r.lrange('default', 0, -1)
    print(f"\n📋 Pending tasks:")
    for idx, task in enumerate(tasks, 1):
        print(f"  {idx}. {task[:100]}...")

# Check Celery inspect
celery_app = Celery('manual_generator', broker='redis://localhost:6379/1')
inspect = celery_app.control.inspect(timeout=3.0)

print(f"\n🔍 Active tasks:")
active = inspect.active()
if active:
    for worker, tasks in active.items():
        print(f"  {worker}: {len(tasks)} tasks")
        for task in tasks:
            print(f"    - {task['name']}: {task['id']}")
else:
    print("  (none)")

print(f"\n⏸️  Reserved tasks:")
reserved = inspect.reserved()
if reserved:
    for worker, tasks in reserved.items():
        print(f"  {worker}: {len(tasks)} tasks")
else:
    print("  (none)")

print(f"\n📝 Registered tasks:")
registered = inspect.registered()
if registered:
    for worker, tasks in registered.items():
        print(f"  {worker}:")
        for task in tasks:
            print(f"    - {task}")
else:
    print("  (none)")
