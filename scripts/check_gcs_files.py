from google.cloud import storage

try:
    client = storage.Client.from_service_account_json('/app/gcp-credentials.json')
    bucket = client.bucket('manual_generator')
    
    print("=== GCS Video Files ===")
    blobs = list(bucket.list_blobs(prefix='video/', max_results=10))
    for blob in blobs:
        print(f"Blob name: {blob.name}")
        print(f"Size: {blob.size} bytes")
        print("---")
        
    print(f"\nTotal files found: {len(blobs)}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()