"""Check content field for video URLs"""
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.app import app
from src.models.models import Manual

with app.app_context():
    m = Manual.query.get(44)
    if m and m.content:
        urls = re.findall(r'gs://[^\s"\'<>]+', m.content)
        print(f"Found {len(urls)} GCS URLs in content")
        for i, url in enumerate(urls[:3], 1):
            print(f"{i}. {url}")
    else:
        print("No content found")
