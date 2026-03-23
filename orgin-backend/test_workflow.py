import requests
import io
from PIL import Image, ImageDraw
import json

# Create a simple test image
img = Image.new('RGB', (200, 200), color='blue')
draw = ImageDraw.Draw(img)
draw.text((50, 50), "TEST IMAGE", fill='white')
img_bytes = io.BytesIO()
img.save(img_bytes, format='PNG')
img_bytes.seek(0)

# Step 1: Embed watermark for user "rom"
print("=== Step 1: Embedding watermark ===")
files = {'file': ('test.png', img_bytes, 'image/png')}
data = {'user_handle': 'rom'}
response = requests.post('http://localhost:8000/api/watermark/embed', files=files, data=data)

if response.status_code == 200:
    watermarked_bytes = response.content
    with open('new_watermarked_test.png', 'wb') as f:
        f.write(watermarked_bytes)
    print("✓ Watermark embedded successfully")
else:
    print("✗ Embed failed:", response.status_code, response.text)
    exit()

# Step 2: Extract and verify the watermark
print("\n=== Step 2: Extracting watermark ===")
with open('new_watermarked_test.png', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/api/watermark/extract', files=files)

print("Status Code:", response.status_code)
result = response.json()
print("Response:", json.dumps(result, indent=2))

if result.get('found'):
    print("✓ Signature verification SUCCESS")
else:
    print("✗ Signature verification FAILED")
