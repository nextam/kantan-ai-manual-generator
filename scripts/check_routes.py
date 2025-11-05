"""
File: check_routes.py
Purpose: Check registered Flask routes
Main functionality: Display all registered URL rules
Dependencies: requests
"""

import requests

response = requests.get("http://localhost:5000/api/test/database-status")
print(f"Test endpoint works: {response.status_code == 200}")

# Try to access a simple page to see if Flask is running
response = requests.get("http://localhost:5000/")
print(f"Root endpoint status: {response.status_code}")

# Try admin endpoint
try:
    response = requests.get("http://localhost:5000/api/admin/companies")
    print(f"Admin endpoint status: {response.status_code}")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Admin endpoint error: {e}")
