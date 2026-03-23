import requests
import json
import base64
import io
from PIL import Image

def test_frontend_file_processing():
    """Test how the frontend processes files before sending"""
    
    print("=== DEBUGGING FRONTEND FILE PROCESSING ===\n")
    
    # Test with the existing watermarked image
    with open('watermarked_test.png', 'rb') as f:
        image_data = f.read()
    
    print(f"Original file size: {len(image_data)} bytes")
    
    # Method 1: Test exactly how the frontend sends FormData
    print("\n1. Testing FormData (like frontend)...")
    try:
        # Create FormData like the frontend does
        files = {'file': ('watermarked_test.png', image_data, 'image/png')}
        
        # Send to frontend proxy (like browser would)
        response = requests.post(
            "http://localhost:5173/api/watermark/extract",
            files=files,
            headers={'Accept': 'application/json'}
        )
        
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Found: {result.get('found')}")
        print(f"Message: {result.get('message')}")
        
    except Exception as e:
        print(f"FormData error: {e}")
    
    # Method 2: Test with different content types
    print("\n2. Testing different content types...")
    
    content_types = [
        'image/png',
        'image/jpeg', 
        'application/octet-stream',
        None  # Let requests determine
    ]
    
    for ct in content_types:
        try:
            files = {'file': ('test.png', image_data, ct)}
            response = requests.post("http://localhost:5173/api/watermark/extract", files=files)
            result = response.json()
            print(f"Content-Type {ct}: {result.get('found')} - {result.get('message', '')[:50]}")
        except Exception as e:
            print(f"Content-Type {ct}: Error - {e}")
    
    # Method 3: Test image normalization (like frontend does)
    print("\n3. Testing image normalization...")
    
    # The frontend has a _normalize_image function - let's simulate it
    try:
        img = Image.open(io.BytesIO(image_data)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        normalized_bytes = buf.getvalue()
        
        print(f"Normalized size: {len(normalized_bytes)} bytes")
        print(f"Size difference: {len(normalized_bytes) - len(image_data)} bytes")
        
        # Test with normalized image
        files = {'file': ('normalized.png', normalized_bytes, 'image/png')}
        response = requests.post("http://localhost:5173/api/watermark/extract", files=files)
        result = response.json()
        print(f"Normalized result: {result.get('found')} - {result.get('message', '')}")
        
    except Exception as e:
        print(f"Normalization error: {e}")

def test_specific_user_images():
    """Test with images that should definitely work"""
    
    print("\n=== TESTING WITH KNOWN GOOD IMAGES ===\n")
    
    # Get all watermarked media from database
    from database.db import get_db
    from database.models import WatermarkedMedia
    
    db = next(get_db())
    media_records = db.query(WatermarkedMedia).all()
    
    print(f"Found {len(media_records)} watermarked images in database")
    
    for i, record in enumerate(media_records[:3]):  # Test first 3
        print(f"\n{i+1}. Testing image for user: {record.user_handle}")
        print(f"   Seed prefix: {record.watermark_seed_prefix}")
        print(f"   Created: {record.created_at}")
        
        # We don't have the actual image files, but we can create a fresh one
        # and embed the watermark for this user
        
        # Create test image
        img = Image.new('RGB', (300, 300), color='blue')
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.text((100, 100), f"USER: {record.user_handle}", fill='white')
        
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        original_bytes = buf.getvalue()
        
        # Embed watermark for this user
        try:
            from services.watermark_service import embed_watermark
            from database.models import OriginRegistry
            
            user_record = db.query(OriginRegistry).filter(
                OriginRegistry.user_handle == record.user_handle
            ).first()
            
            if user_record:
                watermarked_bytes = embed_watermark(original_bytes, user_record.watermark_seed)
                
                # Test extraction
                files = {'file': (f'test_{record.user_handle}.png', watermarked_bytes, 'image/png')}
                response = requests.post("http://localhost:5173/api/watermark/extract", files=files)
                result = response.json()
                
                print(f"   Result: {result.get('found')} - {result.get('message', '')}")
                
                if result.get('found') and result.get('matched_user') == record.user_handle:
                    print(f"   ✅ SUCCESS for user {record.user_handle}")
                else:
                    print(f"   ❌ FAILED for user {record.user_handle}")
            else:
                print(f"   ❌ User {record.user_handle} not found in registry")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

def check_frontend_javascript_simulation():
    """Simulate what the frontend JavaScript actually does"""
    
    print("\n=== SIMULATING FRONTEND JAVASCRIPT ===\n")
    
    # This simulates the doExtract function from App.jsx
    print("Simulating doExtract() function...")
    
    try:
        with open('watermarked_test.png', 'rb') as f:
            # This is what happens when file is read in browser
            file_content = f.read()
        
        # Create FormData like the frontend does
        # fd = new FormData()
        # fd.append('file', extractFile)
        
        files = {'file': ('watermarked_test.png', file_content, 'image/png')}
        
        # This is the exact call the frontend makes
        # const res = await api.post('/api/watermark/extract', fd)
        response = requests.post('http://localhost:5173/api/watermark/extract', files=files)
        
        # This is what the frontend does with the response
        # setExtractResult(res.data)
        result = response.json()
        
        print(f"Frontend simulation result:")
        print(f"  found: {result.get('found')}")
        print(f"  matched_user: {result.get('matched_user')}")
        print(f"  verification_method: {result.get('verification_method')}")
        print(f"  message: {result.get('message')}")
        
        # This is the condition that shows "NO SIGNATURE DETECTED"
        if not result.get('found'):
            print("\n❌ This would show '◯ NO SIGNATURE DETECTED' in frontend")
        else:
            print("\n✅ This would show '✓ SIGNATURE VERIFIED SUCCESSFULLY' in frontend")
            
    except Exception as e:
        print(f"Frontend simulation error: {e}")

def main():
    print("=== FRONTEND UPLOAD ISSUE DEBUG ===\n")
    
    test_frontend_file_processing()
    test_specific_user_images()
    check_frontend_javascript_simulation()
    
    print(f"\n=== DEBUGGING COMPLETE ===")
    print("If all tests pass but frontend still shows 'NO SIGNATURE DETECTED':")
    print("1. Check browser console for JavaScript errors")
    print("2. Check Network tab for failed requests")
    print("3. Verify the frontend is actually calling the correct endpoint")
    print("4. Check if there are any frontend-side image processing issues")

if __name__ == "__main__":
    main()
