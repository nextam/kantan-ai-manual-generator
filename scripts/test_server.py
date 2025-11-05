import requests

try:
    response = requests.get('http://localhost:5000/', timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Response Length: {len(response.text)} characters")
    print("\nFirst 500 characters:")
    print(response.text[:500])
except requests.exceptions.ConnectionError:
    print("ERROR: Cannot connect to server")
except requests.exceptions.Timeout:
    print("ERROR: Request timeout")
except Exception as e:
    print(f"ERROR: {e}")
