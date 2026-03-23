import io
import hashlib
import numpy as np
from PIL import Image
from services.watermark_service import (
    embed_watermark, extract_watermark,
    compute_image_hash, compute_perceptual_hash,
    _try_dwtdct_extract, _lsb_extract
)
from database.db import get_db
from database.models import OriginRegistry, WatermarkedMedia

def debug_image_processing(image_path):
    """Debug the complete image processing pipeline"""
    print(f"=== DEBUGGING IMAGE: {image_path} ===\n")
    
    # Load and analyze original image
    with open(image_path, 'rb') as f:
        original_bytes = f.read()
    
    print(f"Original file size: {len(original_bytes)} bytes")
    
    try:
        img = Image.open(io.BytesIO(original_bytes))
        print(f"Image format: {img.format}")
        print(f"Image mode: {img.mode}")
        print(f"Image size: {img.size}")
        print(f"Image has transparency: {'transparency' in img.info}")
    except Exception as e:
        print(f"❌ Cannot read image: {e}")
        return
    
    # Compute hashes
    img_hash = compute_image_hash(original_bytes)
    p_hash = compute_perceptual_hash(original_bytes)
    print(f"\nImage hash: {img_hash[:16]}...")
    print(f"Perceptual hash: {p_hash}")
    
    # Check database for exact match
    db = next(get_db())
    exact_match = db.query(WatermarkedMedia).filter(
        WatermarkedMedia.image_hash == img_hash
    ).first()
    
    if exact_match:
        print(f"\n✅ EXACT HASH MATCH FOUND in database!")
        print(f"   User: {exact_match.user_handle}")
        print(f"   Seed prefix: {exact_match.watermark_seed_prefix}")
        print(f"   Created: {exact_match.created_at}")
        return True
    
    # Check for perceptual hash matches
    all_media = db.query(WatermarkedMedia).all()
    best_match = None
    best_dist = 26  # PHASH_THRESHOLD + 1
    
    for m in all_media:
        dist = hamming_distance(p_hash, m.perceptual_hash)
        if dist < best_dist:
            best_dist = dist
            best_match = m
    
    if best_match and best_dist <= 25:
        print(f"\n✅ PERCEPTUAL HASH MATCH FOUND!")
        print(f"   User: {best_match.user_handle}")
        print(f"   Distance: {best_dist} (threshold: 25)")
        return True
    
    # Try watermark extraction
    print(f"\n=== WATERMARK EXTRACTION ATTEMPTS ===")
    
    # Method 1: DwtDct extraction
    print("\n1. Trying DwtDct extraction...")
    dwtdct_result = _try_dwtdct_extract(original_bytes)
    if dwtdct_result:
        print(f"✅ DwtDct extracted: '{dwtdct_result}'")
        
        # Check against database
        records = db.query(OriginRegistry).all()
        for r in records:
            seed_prefix = r.watermark_seed[:8]
            if (seed_prefix in dwtdct_result or 
                dwtdct_result[:8] == seed_prefix):
                print(f"   ✅ MATCH with user @{r.user_handle}")
                return True
    else:
        print("❌ DwtDct extraction failed")
    
    # Method 2: LSB extraction
    print("\n2. Trying LSB extraction...")
    lsb_result = _lsb_extract(original_bytes)
    if lsb_result:
        print(f"✅ LSB extracted: '{lsb_result}'")
        
        # Check against database
        records = db.query(OriginRegistry).all()
        for r in records:
            seed_prefix = r.watermark_seed[:8]
            if (seed_prefix in lsb_result or 
                lsb_result[:8] == seed_prefix):
                print(f"   ✅ MATCH with user @{r.user_handle}")
                return True
    else:
        print("❌ LSB extraction failed")
    
    # Method 3: Combined extraction
    print("\n3. Trying combined extraction...")
    combined_result = extract_watermark(original_bytes)
    if combined_result:
        print(f"✅ Combined extracted: '{combined_result}'")
        
        # Check against database
        records = db.query(OriginRegistry).all()
        for r in records:
            seed_prefix = r.watermark_seed[:8]
            if (seed_prefix in combined_result or 
                combined_result[:8] == seed_prefix):
                print(f"   ✅ MATCH with user @{r.user_handle}")
                return True
    else:
        print("❌ Combined extraction failed")
    
    print(f"\n❌ NO SIGNATURE DETECTED - All methods failed")
    return False

def hamming_distance(hash1, hash2):
    """Calculate Hamming distance between two hash strings"""
    if len(hash1) != len(hash2):
        return max(len(hash1), len(hash2)) * 4
    dist = 0
    for c1, c2 in zip(hash1, hash2):
        diff = int(c1, 16) ^ int(c2, 16)
        dist += bin(diff).count('1')
    return dist

def test_fresh_watermark():
    """Create a fresh watermark and test immediately"""
    print("\n=== TESTING FRESH WATERMARK CREATION ===\n")
    
    # Create a simple test image
    img = Image.new('RGB', (200, 200), color='lightgreen')
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), "FRESH TEST", fill='darkgreen')
    
    # Save to bytes
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    original_bytes = buf.getvalue()
    
    print("Created fresh test image")
    
    # Get a user from database
    db = next(get_db())
    user = db.query(OriginRegistry).first()
    if not user:
        print("❌ No users in database")
        return False
    
    print(f"Using user: @{user.user_handle} (seed: {user.watermark_seed[:8]}...)")
    
    # Embed watermark
    try:
        watermarked_bytes = embed_watermark(original_bytes, user.watermark_seed)
        print("✅ Watermark embedded successfully")
        
        # Save for inspection
        with open('debug_fresh_watermarked.png', 'wb') as f:
            f.write(watermarked_bytes)
        print("Saved as: debug_fresh_watermarked.png")
        
        # Test extraction immediately
        print("\nTesting immediate extraction...")
        extracted = extract_watermark(watermarked_bytes)
        if extracted:
            print(f"✅ Extracted: '{extracted}'")
            if user.watermark_seed[:8] in extracted:
                print("✅ Fresh watermark test PASSED")
                return True
            else:
                print("❌ Extracted watermark doesn't match user seed")
        else:
            print("❌ Failed to extract fresh watermark")
            
    except Exception as e:
        print(f"❌ Embedding failed: {e}")
    
    return False

def main():
    print("=== ORIGINX SIGNATURE DEBUG MODULE ===\n")
    
    # Test 1: Debug existing watermarked image
    print("TEST 1: Debugging existing watermarked image")
    debug_result1 = debug_image_processing('watermarked_test.png')
    
    # Test 2: Debug fresh watermark
    print("\n" + "="*60)
    print("TEST 2: Testing fresh watermark creation")
    debug_result2 = test_fresh_watermark()
    
    # Test 3: Debug the fresh watermarked image
    if debug_result2:
        print("\n" + "="*60)
        print("TEST 3: Debugging fresh watermarked image")
        debug_result3 = debug_image_processing('debug_fresh_watermarked.png')
    
    print(f"\n=== DEBUG SUMMARY ===")
    print(f"Existing image: {'✅' if debug_result1 else '❌'}")
    print(f"Fresh watermark: {'✅' if debug_result2 else '❌'}")
    
    if not debug_result1 and not debug_result2:
        print("\n🚨 CRITICAL: Signature system is not working!")
        print("Possible causes:")
        print("1. Missing dependencies (cv2, imwatermark)")
        print("2. Image format incompatibility")
        print("3. Database connection issues")
        print("4. Watermark embedding/extraction logic errors")

if __name__ == "__main__":
    main()
