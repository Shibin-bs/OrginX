"""
OriginX — Authenticity Service Test
Tests the forensic screening module against synthetic and natural-looking images.
"""
import io
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, ".")
from services.authenticity_service import authenticity_check


def make_solid_image():
    """Solid color — should be flagged as suspicious."""
    img = Image.new("RGB", (256, 256), (100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), "Solid color"


def make_gradient_image():
    """Smooth gradient — synthetic-looking, should be flagged."""
    arr = np.zeros((256, 256, 3), dtype=np.uint8)
    for i in range(256):
        arr[i, :, 0] = i
        arr[i, :, 1] = 255 - i
        arr[i, :, 2] = 128
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), "Gradient"


def make_natural_photo():
    """Simulate a natural-looking photographic image with varied textures,
    noise, and multiple objects — should PASS authenticity check."""
    np.random.seed(42)
    # Start with a random base resembling camera sensor output
    arr = np.random.randint(40, 220, (512, 512, 3), dtype=np.uint8)

    img = Image.fromarray(arr)
    # Apply slight blur to simulate lens optics (not too much)
    img = img.filter(ImageFilter.GaussianBlur(radius=1.2))

    # Draw diverse objects (varying textures like a real scene)
    draw = ImageDraw.Draw(img)
    # Sky-like gradient at top
    for y in range(100):
        c = int(180 + y * 0.3)
        draw.line([(0, y), (511, y)], fill=(100, 140, c))
    # Ground-like area with texture
    for y in range(350, 512):
        c = int(80 + (y - 350) * 0.5)
        draw.line([(0, y), (511, y)], fill=(c, int(c * 0.8), int(c * 0.5)))
    # Objects with sharp edges (buildings, trees)
    draw.rectangle([50, 100, 150, 350], fill=(80, 70, 65))
    draw.rectangle([55, 110, 145, 340], fill=(120, 110, 100))
    draw.rectangle([200, 150, 350, 350], fill=(90, 85, 75))
    draw.rectangle([210, 160, 340, 340], fill=(140, 130, 115))
    draw.ellipse([380, 80, 500, 200], fill=(50, 120, 50))
    draw.ellipse([390, 90, 490, 190], fill=(60, 140, 55))

    # Add sensor-like noise
    arr2 = np.array(img).astype(np.float64)
    noise = np.random.normal(0, 8, arr2.shape)
    arr2 = np.clip(arr2 + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr2)

    # Save as JPEG (realistic camera output) then reload
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue(), "Natural photo simulation"


def make_tiny_image():
    """Very small image — should be rejected."""
    img = Image.new("RGB", (16, 16), (200, 100, 50))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), "Tiny (16x16)"


def main():
    print("=" * 60)
    print("ORIGINX AUTHENTICITY SERVICE TEST")
    print("=" * 60)

    tests = [
        make_natural_photo(),
        make_solid_image(),
        make_gradient_image(),
        make_tiny_image(),
    ]

    results = []
    for image_bytes, label in tests:
        print(f"\n{'─'*50}")
        print(f"Testing: {label} ({len(image_bytes)} bytes)")
        result = authenticity_check(image_bytes)
        passed = result["passed"]
        risk = result["risk_score"]
        reason = result["failure_reason"]
        print(f"  Passed:     {passed}")
        print(f"  Risk Score: {risk}")
        print(f"  Signals:    {result['signals']}")
        if reason:
            print(f"  Reason:     {reason}")
        results.append((label, passed, risk))

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    all_ok = True
    for label, passed, risk in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {label:30s} → {status} (risk={risk:.4f})")
        # Natural photo should pass, everything else should fail
        if label == "Natural photo simulation" and not passed:
            print("    ⚠ ERROR: Natural photo should have passed!")
            all_ok = False
        if label in ("Solid color", "Gradient") and passed:
            print("    ⚠ ERROR: Synthetic image should have been rejected!")
            all_ok = False

    print()
    if all_ok:
        print("🎉 ALL TESTS BEHAVED AS EXPECTED")
    else:
        print("⚠ SOME TESTS DID NOT MATCH EXPECTATIONS — review thresholds")

    return all_ok


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
