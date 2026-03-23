import requests
import io
from PIL import Image, ImageDraw
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test backend health"""
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"✓ Backend Health: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Backend Health Failed: {e}")
        return False

def test_registry():
    """Test consent registry"""
    try:
        response = requests.get(f"{BASE_URL}/api/consent/registry")
        print(f"✓ Registry: {response.status_code}")
        data = response.json()
        print(f"  Registered users: {data.get('total', 0)}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Registry Failed: {e}")
        return False

def create_test_image():
    """Create a test image"""
    img = Image.new('RGB', (300, 200), color='lightblue')
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), "ORIGINX TEST", fill='darkblue')
    draw.rectangle([20, 20, 280, 180], outline='darkblue', width=2)
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

def test_embed_workflow():
    """Test complete embed workflow"""
    print("\n=== Testing Embed Workflow ===")
    
    # Create test image
    img_bytes = create_test_image()
    
    # Embed watermark for existing user 'rom'
    files = {'file': ('test.png', img_bytes, 'image/png')}
    data = {'user_handle': 'rom'}
    
    try:
        response = requests.post(f"{BASE_URL}/api/watermark/embed", files=files, data=data)
        
        if response.status_code == 200:
            with open('workflow_test_watermarked.png', 'wb') as f:
                f.write(response.content)
            print("✓ Watermark embedded successfully")
            return True
        else:
            print(f"✗ Embed failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"✗ Embed exception: {e}")
        return False

def test_extract_workflow():
    """Test complete extract workflow"""
    print("\n=== Testing Extract Workflow ===")
    
    try:
        with open('workflow_test_watermarked.png', 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{BASE_URL}/api/watermark/extract", files=files)
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        print("Response:", json.dumps(result, indent=2))
        
        if result.get('found'):
            print("✓ Signature verification SUCCESS")
            print(f"  Matched user: @{result.get('matched_user')}")
            print(f"  Method: {result.get('verification_method')}")
            return True
        else:
            print("✗ Signature verification FAILED")
            return False
    except Exception as e:
        print(f"✗ Extract exception: {e}")
        return False

def main():
    print("=== ORIGINX COMPLETE WORKFLOW TEST ===\n")
    
    # Wait a moment for services to be ready
    time.sleep(2)
    
    # Test all components
    health_ok = test_health()
    registry_ok = test_registry()
    
    if not health_ok:
        print("\n❌ Backend not responding - aborting test")
        return
    
    embed_ok = test_embed_workflow()
    extract_ok = test_extract_workflow()
    
    print(f"\n=== TEST SUMMARY ===")
    print(f"Backend Health: {'✓' if health_ok else '✗'}")
    print(f"Registry: {'✓' if registry_ok else '✗'}")
    print(f"Embed Workflow: {'✓' if embed_ok else '✗'}")
    print(f"Extract Workflow: {'✓' if extract_ok else '✗'}")
    
    if all([health_ok, registry_ok, embed_ok, extract_ok]):
        print("\n🎉 ALL TESTS PASSED - System is ready!")
    else:
        print("\n⚠️  Some tests failed - check the logs above")

if __name__ == "__main__":
    main()
