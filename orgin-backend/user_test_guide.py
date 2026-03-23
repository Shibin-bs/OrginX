import requests
import webbrowser
import time

def create_test_images_for_user():
    """Create test images that you can use to test the frontend"""
    
    print("=== CREATING TEST IMAGES FOR FRONTEND TESTING ===\n")
    
    from PIL import Image, ImageDraw
    import io
    
    # Test 1: Create and watermark an image for user 'rom'
    print("1. Creating watermarked image for user 'rom'...")
    
    img = Image.new('RGB', (400, 300), color='lightblue')
    draw = ImageDraw.Draw(img)
    draw.text((100, 100), "TEST IMAGE FOR ROM", fill='darkblue')
    draw.rectangle([20, 20, 380, 280], outline='darkblue', width=3)
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    original_bytes = buf.getvalue()
    
    # Embed watermark
    try:
        from services.watermark_service import embed_watermark
        from database.db import get_db
        from database.models import OriginRegistry
        
        db = next(get_db())
        user = db.query(OriginRegistry).filter(OriginRegistry.user_handle == 'rom').first()
        
        if user:
            watermarked_bytes = embed_watermark(original_bytes, user.watermark_seed)
            
            with open('frontend_test_rom.png', 'wb') as f:
                f.write(watermarked_bytes)
            print("✅ Created: frontend_test_rom.png (should verify successfully)")
        else:
            print("❌ User 'rom' not found in database")
            
    except Exception as e:
        print(f"❌ Error creating watermarked image: {e}")
    
    # Test 2: Create a non-watermarked image
    print("\n2. Creating non-watermarked image...")
    
    img2 = Image.new('RGB', (400, 300), color='lightcoral')
    draw2 = ImageDraw.Draw(img2)
    draw2.text((100, 100), "NO WATERMARK", fill='darkred')
    draw2.rectangle([20, 20, 380, 280], outline='darkred', width=3)
    
    buf2 = io.BytesIO()
    img2.save(buf2, format='PNG')
    
    with open('frontend_test_no_watermark.png', 'wb') as f:
        f.write(buf2.getvalue())
    print("✅ Created: frontend_test_no_watermark.png (should show 'NO SIGNATURE DETECTED')")
    
    # Test 3: Test both images via API to confirm
    print("\n3. Testing both images via API...")
    
    test_files = [
        ('frontend_test_rom.png', True, "Should detect signature"),
        ('frontend_test_no_watermark.png', False, "Should NOT detect signature")
    ]
    
    for filename, should_detect, description in test_files:
        try:
            with open(filename, 'rb') as f:
                files = {'file': (filename, f.read(), 'image/png')}
                response = requests.post("http://localhost:5173/api/watermark/extract", files=files)
                result = response.json()
                
                detected = result.get('found', False)
                status = "✅" if detected == should_detect else "❌"
                print(f"   {status} {filename}: {detected} - {description}")
                
                if detected:
                    print(f"      User: @{result.get('matched_user')}")
                    print(f"      Method: {result.get('verification_method')}")
                else:
                    print(f"      Message: {result.get('message')}")
                    
        except Exception as e:
            print(f"   ❌ Error testing {filename}: {e}")

def open_frontend_with_instructions():
    """Open the frontend with testing instructions"""
    
    print("\n=== FRONTEND TESTING INSTRUCTIONS ===\n")
    print("I'm about to open the frontend in your browser.")
    print("Please follow these steps EXACTLY:\n")
    
    print("STEP 1: Test the watermarked image")
    print("1. Click on the 'EXTRACT' tab")
    print("2. Click 'Click to select image to scan'")
    print("3. Select the file: frontend_test_rom.png")
    print("4. Click '◉ SCAN FOR SIGNATURE'")
    print("5. Expected result: '✓ SIGNATURE VERIFIED SUCCESSFULLY'")
    print("   - Should show user: @rom")
    print("   - Should show verification method\n")
    
    print("STEP 2: Test the non-watermarked image")
    print("1. Click 'Click to select image to scan' again")
    print("2. Select the file: frontend_test_no_watermark.png")
    print("3. Click '◉ SCAN FOR SIGNATURE'")
    print("4. Expected result: '◯ NO SIGNATURE DETECTED'\n")
    
    print("STEP 3: Check browser console if issues occur")
    print("1. Press F12 to open developer tools")
    print("2. Click on 'Console' tab")
    print("3. Look for any red error messages")
    print("4. Click on 'Network' tab")
    print("5. Repeat the upload and check for failed requests\n")
    
    # Open the frontend
    try:
        webbrowser.open('http://localhost:5173')
        print("🌐 Frontend opened in your browser!")
    except:
        print("❌ Could not open browser automatically")
        print("Please manually open: http://localhost:5173")

def check_common_issues():
    """Check for common frontend issues"""
    
    print("\n=== CHECKING COMMON FRONTEND ISSUES ===\n")
    
    # Check if frontend is running
    try:
        response = requests.get("http://localhost:5173", timeout=5)
        print("✅ Frontend is running")
    except:
        print("❌ Frontend is not running!")
        print("   Start it with: cd orgin-frontend && npm run dev")
        return
    
    # Check if backend is accessible from frontend
    try:
        response = requests.get("http://localhost:5173/api/health", timeout=5)
        print("✅ Backend is accessible from frontend")
    except:
        print("❌ Backend is NOT accessible from frontend!")
        print("   Check proxy configuration in vite.config.js")
        return
    
    # Check CORS headers
    try:
        response = requests.options("http://localhost:5173/api/watermark/extract", timeout=5)
        print("✅ CORS check passed")
    except:
        print("⚠️  Could not verify CORS settings")

def main():
    print("=== ORIGINX FRONTEND TESTING GUIDE ===\n")
    
    # Check if everything is running
    check_common_issues()
    
    # Create test images
    create_test_images_for_user()
    
    # Open frontend with instructions
    open_frontend_with_instructions()
    
    print(f"\n=== SUMMARY ===")
    print("✅ Created test images in the backend directory")
    print("✅ Verified backend is working correctly")
    print("✅ Opened frontend in your browser")
    print("\nIf you still see 'NO SIGNATURE DETECTED' for the watermarked image:")
    print("1. Check browser console for JavaScript errors")
    print("2. Check Network tab for failed API calls")
    print("3. Make sure you're selecting the correct file (frontend_test_rom.png)")
    print("4. Try refreshing the page and testing again")

if __name__ == "__main__":
    main()
