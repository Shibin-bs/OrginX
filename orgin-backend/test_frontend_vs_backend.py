import requests
import io
from PIL import Image

def test_upload_methods():
    """Test the difference between frontend proxy and direct backend calls"""
    
    print("=== COMPARING FRONTEND vs BACKEND UPLOADS ===\n")
    
    # Create a test image
    img = Image.new('RGB', (300, 300), color='orange')
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.text((100, 100), "UPLOAD TEST", fill='white')
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    img_bytes = buf.getvalue()
    
    # First, embed a watermark using direct backend call
    print("1. Embedding watermark via direct backend...")
    files = {'file': ('test.png', img_bytes, 'image/png')}
    data = {'user_handle': 'rom'}  # Use existing user
    
    try:
        response = requests.post("http://localhost:8000/api/watermark/embed", files=files, data=data)
        if response.status_code == 200:
            watermarked_bytes = response.content
            print("✅ Direct backend embed successful")
        else:
            print(f"❌ Direct backend embed failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Direct backend embed error: {e}")
        return
    
    # Save the watermarked image
    with open('upload_test_watermarked.png', 'wb') as f:
        f.write(watermarked_bytes)
    
    # Test 2: Extract via direct backend
    print("\n2. Extracting via direct backend...")
    try:
        with open('upload_test_watermarked.png', 'rb') as f:
            files = {'file': f}
            response = requests.post("http://localhost:8000/api/watermark/extract", files=files)
        
        result = response.json()
        print(f"Direct backend result: {result.get('found', False)}")
        if result.get('found'):
            print(f"✅ Direct backend: {result.get('message')}")
        else:
            print(f"❌ Direct backend: {result.get('message')}")
    except Exception as e:
        print(f"❌ Direct backend extract error: {e}")
    
    # Test 3: Extract via frontend proxy
    print("\n3. Extracting via frontend proxy...")
    try:
        with open('upload_test_watermarked.png', 'rb') as f:
            files = {'file': f}
            response = requests.post("http://localhost:5173/api/watermark/extract", files=files)
        
        result = response.json()
        print(f"Frontend proxy result: {result.get('found', False)}")
        if result.get('found'):
            print(f"✅ Frontend proxy: {result.get('message')}")
        else:
            print(f"❌ Frontend proxy: {result.get('message')}")
    except Exception as e:
        print(f"❌ Frontend proxy extract error: {e}")
    
    # Test 4: Simulate frontend file upload (like browser does)
    print("\n4. Simulating browser upload...")
    try:
        # This simulates how a browser sends the file
        files = {'file': ('test.png', watermarked_bytes, 'image/png')}
        response = requests.post("http://localhost:5173/api/watermark/extract", files=files)
        
        result = response.json()
        print(f"Browser simulation result: {result.get('found', False)}")
        if result.get('found'):
            print(f"✅ Browser simulation: {result.get('message')}")
        else:
            print(f"❌ Browser simulation: {result.get('message')}")
    except Exception as e:
        print(f"❌ Browser simulation error: {e}")

def test_image_processing_differences():
    """Test if image processing differs between methods"""
    print("\n=== TESTING IMAGE PROCESSING DIFFERENCES ===\n")
    
    # Load the existing watermarked image
    with open('watermarked_test.png', 'rb') as f:
        original_bytes = f.read()
    
    print(f"Original image size: {len(original_bytes)} bytes")
    
    # Test 1: Direct backend extraction
    print("\n1. Direct backend extraction...")
    try:
        files = {'file': ('watermarked_test.png', original_bytes, 'image/png')}
        response = requests.post("http://localhost:8000/api/watermark/extract", files=files)
        result = response.json()
        print(f"Result: {result.get('found', False)} - {result.get('message', '')}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Frontend proxy extraction
    print("\n2. Frontend proxy extraction...")
    try:
        files = {'file': ('watermarked_test.png', original_bytes, 'image/png')}
        response = requests.post("http://localhost:5173/api/watermark/extract", files=files)
        result = response.json()
        print(f"Result: {result.get('found', False)} - {result.get('message', '')}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Check if the image gets modified during upload
    print("\n3. Checking image modification...")
    
    # Save and reload to simulate browser processing
    img = Image.open(io.BytesIO(original_bytes))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    processed_bytes = buf.getvalue()
    
    print(f"Processed image size: {len(processed_bytes)} bytes")
    print(f"Size difference: {len(processed_bytes) - len(original_bytes)} bytes")
    
    # Test extraction on processed image
    try:
        files = {'file': ('processed.png', processed_bytes, 'image/png')}
        response = requests.post("http://localhost:8000/api/watermark/extract", files=files)
        result = response.json()
        print(f"Processed image result: {result.get('found', False)} - {result.get('message', '')}")
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("=== FRONTEND vs BACKEND SIGNATURE DETECTION DEBUG ===\n")
    
    test_upload_methods()
    test_image_processing_differences()
    
    print(f"\n=== RECOMMENDATIONS ===")
    print("1. If direct backend works but frontend doesn't:")
    print("   - Check CORS configuration")
    print("   - Verify proxy settings")
    print("   - Check file upload handling in frontend")
    print("\n2. If both fail:")
    print("   - Check image format/size requirements")
    print("   - Verify database contains watermarked images")
    print("   - Check watermark embedding was successful")

if __name__ == "__main__":
    main()
