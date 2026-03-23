import requests
import json

# Test the extract endpoint
with open('watermarked_test.png', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/api/watermark/extract', files=files)

print("Status Code:", response.status_code)
print("Response:", json.dumps(response.json(), indent=2))
