import requests
import json
import time

def test_frontend_backend_integration():
    """Test that frontend can communicate with backend"""
    
    # Test backend directly
    print("=== Testing Backend Directly ===")
    try:
        response = requests.get("http://localhost:8000/api/health")
        print(f"✓ Backend direct: {response.status_code}")
        print(f"  Response: {response.json()}")
    except Exception as e:
        print(f"✗ Backend direct failed: {e}")
        return False
    
    # Test frontend proxy to backend
    print("\n=== Testing Frontend Proxy ===")
    try:
        response = requests.get("http://localhost:5173/api/health")
        print(f"✓ Frontend proxy: {response.status_code}")
        print(f"  Response: {response.json()}")
    except Exception as e:
        print(f"✗ Frontend proxy failed: {e}")
        return False
    
    # Test registry through proxy
    print("\n=== Testing Registry Through Proxy ===")
    try:
        response = requests.get("http://localhost:5173/api/consent/registry")
        print(f"✓ Registry proxy: {response.status_code}")
        data = response.json()
        print(f"  Users registered: {data.get('total', 0)}")
    except Exception as e:
        print(f"✗ Registry proxy failed: {e}")
        return False
    
    return True

def test_signature_workflow_via_proxy():
    """Test signature workflow through frontend proxy"""
    
    print("\n=== Testing Signature Workflow via Proxy ===")
    
    # Test extract with existing watermarked image
    try:
        with open('watermarked_test.png', 'rb') as f:
            files = {'file': f}
            response = requests.post("http://localhost:5173/api/watermark/extract", files=files)
        
        print(f"Extract via proxy: {response.status_code}")
        result = response.json()
        
        if result.get('found'):
            print("✓ Signature verification via proxy SUCCESS")
            print(f"  User: @{result.get('matched_user')}")
            print(f"  Method: {result.get('verification_method')}")
            return True
        else:
            print("✗ Signature verification via proxy FAILED")
            return False
    except Exception as e:
        print(f"✗ Extract via proxy exception: {e}")
        return False

def main():
    print("=== ORIGINX FINAL INTEGRATION TEST ===\n")
    
    # Wait for services to be ready
    time.sleep(3)
    
    # Test integration
    proxy_ok = test_frontend_backend_integration()
    workflow_ok = test_signature_workflow_via_proxy()
    
    print(f"\n=== INTEGRATION TEST SUMMARY ===")
    print(f"Frontend-Backend Proxy: {'✓' if proxy_ok else '✗'}")
    print(f"Signature Workflow via Proxy: {'✓' if workflow_ok else '✗'}")
    
    if proxy_ok and workflow_ok:
        print("\n🎉 INTEGRATION TESTS PASSED!")
        print("📱 Frontend: http://localhost:5173")
        print("🔧 Backend: http://localhost:8000")
        print("✅ Signature authorization system is fully operational")
    else:
        print("\n⚠️  Integration tests failed - check configuration")

if __name__ == "__main__":
    main()
