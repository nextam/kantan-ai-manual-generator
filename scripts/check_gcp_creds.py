import json

with open('gcp-credentials.json', 'r') as f:
    creds = json.load(f)
    print(f"Project ID: {creds.get('project_id', 'NOT FOUND')}")
    print(f"Client Email: {creds.get('client_email', 'NOT FOUND')}")
