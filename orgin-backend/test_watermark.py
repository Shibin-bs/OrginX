"""
OriginX End-to-End Watermark Test
==================================
Tests: embed → extract (exact match) → re-encode → extract (pixel hash match)
"""
import requests
import json
import io
from PIL import Image, ImageDraw
import random

BASE = "http://localhost:8000"


def create_test_image():
    """Create a colorful test image with enough complexity for DwtDct."""
    random.seed(42)
    img = Image.new("RGB", (512, 512), (20, 30, 50))
    draw = ImageDraw.Draw(img)
    for _ in range(80):
        x, y = random.randint(0, 511), random.randint(0, 511)
        w, h = random.randint(10, 100), random.randint(10, 100)
        c = (random.randint(30, 255), random.randint(30, 255), random.randint(30, 255))
        draw.rectangle([x, y, x + w, y + h], fill=c)
    for _ in range(30):
        x, y = random.randint(0, 511), random.randint(0, 511)
        r = random.randint(5, 40)
        c = (random.randint(30, 255), random.randint(30, 255), random.randint(30, 255))
        draw.ellipse([x - r, y - r, x + r, y + r], fill=c)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_health():
    print("=" * 60)
    print("TEST: Backend Health Check")
    r = requests.get(f"{BASE}/api/health", timeout=5)
    assert r.status_code == 200, f"Health check failed: {r.status_code}"
    data = r.json()
    assert data["status"] == "ok"
    print(f"  ✓ Backend online, version={data['version']}")
    return True


def test_embed_extract(user_handle="mol"):
    print("\n" + "=" * 60)
    print(f"TEST: Embed → Extract (user=@{user_handle})")

    # Create test image
    img_bytes = create_test_image()
    print(f"  Created test image: {len(img_bytes)} bytes")

    # EMBED
    print("\n  --- EMBED ---")
    r = requests.post(
        f"{BASE}/api/watermark/embed",
        files={"file": ("test.png", img_bytes, "image/png")},
        data={"user_handle": user_handle},
        timeout=30,
    )
    assert r.status_code == 200, f"Embed failed: {r.status_code} {r.text[:200]}"
    assert "image" in r.headers.get("content-type", ""), f"Expected image, got {r.headers.get('content-type')}"
    watermarked = r.content
    print(f"  ✓ Embedded: {len(watermarked)} bytes")

    # EXTRACT (exact bytes — should match via pixel hash)
    print("\n  --- EXTRACT (exact bytes) ---")
    r2 = requests.post(
        f"{BASE}/api/watermark/extract",
        files={"file": ("watermarked.png", watermarked, "image/png")},
        timeout=30,
    )
    assert r2.status_code == 200, f"Extract failed: {r2.status_code}"
    result = r2.json()
    print(f"  found: {result['found']}")
    print(f"  matched_user: {result.get('matched_user')}")
    print(f"  method: {result.get('verification_method')}")
    print(f"  message: {result.get('message')}")
    assert result["found"] is True, f"FAILED: {result}"
    assert result["matched_user"] == user_handle, f"Wrong user: {result['matched_user']}"
    print(f"  ✓ PASSED — matched @{user_handle} via {result['verification_method']}")

    # EXTRACT (re-encoded — should still match via pixel hash or pHash)
    print("\n  --- EXTRACT (re-encoded PNG) ---")
    img = Image.open(io.BytesIO(watermarked)).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    reencoded = buf.getvalue()
    print(f"  Re-encoded: {len(reencoded)} bytes (was {len(watermarked)})")

    r3 = requests.post(
        f"{BASE}/api/watermark/extract",
        files={"file": ("reencoded.png", reencoded, "image/png")},
        timeout=30,
    )
    assert r3.status_code == 200
    result3 = r3.json()
    print(f"  found: {result3['found']}")
    print(f"  method: {result3.get('verification_method')}")
    print(f"  message: {result3.get('message')}")
    assert result3["found"] is True, f"FAILED on re-encode: {result3}"
    print(f"  ✓ PASSED — re-encoded image still matched via {result3['verification_method']}")

    return True


def test_analyze(user_handle="mol"):
    print("\n" + "=" * 60)
    print(f"TEST: Deepfake Analyze (user=@{user_handle})")

    img_bytes = create_test_image()

    # Embed first
    r = requests.post(
        f"{BASE}/api/watermark/embed",
        files={"file": ("test.png", img_bytes, "image/png")},
        data={"user_handle": user_handle},
        timeout=30,
    )
    watermarked = r.content

    # Analyze
    r2 = requests.post(
        f"{BASE}/api/detect/analyze",
        files={"file": ("watermarked.png", watermarked, "image/png")},
        timeout=30,
    )
    assert r2.status_code == 200
    result = r2.json()
    print(f"  is_deepfake: {result['is_deepfake']}")
    print(f"  confidence: {result['confidence']}")
    print(f"  provenance.watermark_found: {result['provenance']['watermark_found']}")
    print(f"  provenance.matched_user: {result['provenance']['matched_user']}")
    print(f"  provenance.detection_type: {result['provenance']['detection_type']}")
    print(f"  ✓ PASSED — analysis complete")
    return True


if __name__ == "__main__":
    print("OriginX End-to-End Watermark Verification")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_fn in [test_health, test_embed_extract, test_analyze]:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"\n  ✗ FAILED: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    if failed == 0:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
