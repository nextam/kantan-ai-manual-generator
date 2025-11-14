"""
Get latest manual ID
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.models import Manual
from src.core.app import app

with app.app_context():
    latest = Manual.query.order_by(Manual.id.desc()).first()
    if latest:
        print(latest.id)
    else:
        print("No manuals found")
