"""
OriginX Watermark Engine — Production-Grade
============================================
Binary payload design:
  DwtDct layer: b"OX" + SHA256(seed)[:6] = 8 bytes (64 bits)
  LSB layer:    "ORIGINX:<signature_hex>:END" in pixel LSBs

The 2-byte "OX" header acts as a magic number for corruption detection.
The 6-byte SHA256 digest is the canonical signature_hash stored in DB.
Both layers embed the same canonical signature for consistency.
"""

import io
import hashlib
import struct
import numpy as np
from PIL import Image


# ── SIGNATURE COMPUTATION ───────────────────────────────

PAYLOAD_HEADER = b"OX"           # 2-byte magic number
SIGNATURE_BYTES = 6              # 6 bytes of SHA256 digest
PAYLOAD_SIZE = 8                 # 2 (header) + 6 (signature) = 8 bytes
PAYLOAD_BITS = PAYLOAD_SIZE * 8  # 64 bits for DwtDct


def compute_signature(seed: str) -> str:
    """Compute the canonical 12-char hex signature from a watermark seed.
    This is the single source of truth for matching."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()[:SIGNATURE_BYTES]
    return digest.hex()  # 12-char hex string


def build_payload(seed: str) -> bytes:
    """Build the 8-byte binary payload for DwtDct embedding.
    Format: b'OX' + SHA256(seed)[:6] = 8 bytes exactly."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()[:SIGNATURE_BYTES]
    payload = PAYLOAD_HEADER + digest
    assert len(payload) == PAYLOAD_SIZE, f"Payload must be {PAYLOAD_SIZE} bytes, got {len(payload)}"
    return payload


def validate_payload(raw: bytes) -> str | None:
    """Validate extracted binary payload. Returns signature hex or None.
    Checks for OX magic header, returns the 6-byte digest as hex."""
    if len(raw) < PAYLOAD_SIZE:
        return None
    if raw[:2] != PAYLOAD_HEADER:
        return None
    sig_bytes = raw[2:PAYLOAD_SIZE]
    return sig_bytes.hex()


def match_signature_tolerant(extracted_hex: str, stored_hex: str, max_hamming: int = 2) -> bool:
    """Compare two signature hashes with hamming tolerance for bit-flip errors.
    max_hamming=2 allows up to 2 bit flips in the 48-bit signature."""
    if extracted_hex == stored_hex:
        return True
    if len(extracted_hex) != len(stored_hex):
        return False
    try:
        e_int = int(extracted_hex, 16)
        s_int = int(stored_hex, 16)
        diff = e_int ^ s_int
        return bin(diff).count('1') <= max_hamming
    except ValueError:
        return False


# ── HASHING ─────────────────────────────────────────────

def compute_pixel_hash(image_bytes: bytes) -> str:
    """SHA-256 of raw pixel array (not PNG bytes).
    Stable across PNG re-encodes, different PNG filters, metadata changes."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    pixel_data = np.array(img).tobytes()
    return hashlib.sha256(pixel_data).hexdigest()


def compute_image_hash(image_bytes: bytes) -> str:
    """SHA-256 of raw bytes (for backward compat)."""
    return hashlib.sha256(image_bytes).hexdigest()


def compute_perceptual_hash(image_bytes: bytes, hash_size: int = 16) -> str:
    """DCT-based perceptual hash (pHash). Returns hex string.
    Robust to JPEG re-compression, screenshots, and minor edits."""
    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    img = img.resize((hash_size * 4, hash_size * 4), Image.LANCZOS)
    arr = np.array(img, dtype=float)
    from scipy.fft import dctn
    dct = dctn(arr, type=2, norm='ortho')
    dct_low = dct[:hash_size, :hash_size]
    median = np.median(dct_low)
    bits = (dct_low > median).flatten()
    hex_str = ''.join(format(int(''.join(str(int(b)) for b in bits[i:i+4]), 2), 'x')
                      for i in range(0, len(bits), 4))
    return hex_str


def hamming_distance(hash1: str, hash2: str) -> int:
    """Hamming distance between two hex hash strings."""
    if len(hash1) != len(hash2):
        return max(len(hash1), len(hash2)) * 4
    dist = 0
    for c1, c2 in zip(hash1, hash2):
        diff = int(c1, 16) ^ int(c2, 16)
        dist += bin(diff).count('1')
    return dist


# ── EMBED ───────────────────────────────────────────────

def embed_watermark(image_bytes: bytes, seed: str) -> bytes:
    """Embed watermark using DwtDct (primary) + LSB (secondary).
    Both layers embed the same canonical signature for consistency."""
    sig_hex = compute_signature(seed)
    payload = build_payload(seed)
    print(f"  [WM-EMBED] Signature: {sig_hex}")
    print(f"  [WM-EMBED] Payload ({len(payload)} bytes): {payload.hex()}")

    try:
        import cv2
        from imwatermark import WatermarkEncoder

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h = img.size
        new_w = (w // 8) * 8
        new_h = (h // 8) * 8
        if new_w != w or new_h != h:
            img = img.resize((new_w, new_h), Image.LANCZOS)
            print(f"  [WM-EMBED] Resized: {w}x{h} → {new_w}x{new_h}")

        img_rgb = np.array(img)
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

        encoder = WatermarkEncoder()
        encoder.set_watermark("bytes", payload)
        watermarked_bgr = encoder.encode(img_bgr, "dwtDct")

        watermarked_rgb = cv2.cvtColor(watermarked_bgr, cv2.COLOR_BGR2RGB)
        result = Image.fromarray(watermarked_rgb.astype(np.uint8))

        # Save DwtDct result, then embed LSB on top
        buf = io.BytesIO()
        result.save(buf, format="PNG")
        dwtdct_bytes = buf.getvalue()
        final_bytes = _lsb_embed(dwtdct_bytes, sig_hex)
        print(f"  [WM-EMBED] ✓ Dual-layer embed SUCCESS (DwtDct + LSB)")
        return final_bytes

    except Exception as e:
        print(f"  [WM-EMBED] ✗ DwtDct failed: {e} — using LSB only")
        return _lsb_embed(image_bytes, sig_hex)


# ── EXTRACT ─────────────────────────────────────────────

def extract_watermark(image_bytes: bytes) -> str | None:
    """Multi-strategy extraction. Returns 12-char signature hex or None.
    Strategy order: DwtDct → LSB (both return the same canonical signature)."""

    # Strategy 1: DwtDct extraction
    sig = _try_dwtdct_extract(image_bytes)
    if sig:
        return sig

    # Strategy 2: LSB extraction
    sig = _lsb_extract(image_bytes)
    if sig:
        return sig

    return None


def _try_dwtdct_extract(image_bytes: bytes) -> str | None:
    """Extract DwtDct payload. Returns signature hex if valid OX header found."""
    try:
        import cv2
        from imwatermark import WatermarkDecoder

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h = img.size
        
        # Ensure dimensions are multiples of 8 for DWT
        new_w = (w // 8) * 8
        new_h = (h // 8) * 8
        if new_w < 8 or new_h < 8:
            print(f"  [WM-DWT] ✗ Image too small: {w}x{h} → {new_w}x{new_h}")
            return None
            
        if new_w != w or new_h != h:
            print(f"  [WM-DWT] Resizing: {w}x{h} → {new_w}x{new_h}")
            img = img.resize((new_w, new_h), Image.LANCZOS)

        img_rgb = np.array(img, dtype=np.uint8)
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

        decoder = WatermarkDecoder("bytes", PAYLOAD_BITS)
        recovered = decoder.decode(img_bgr, "dwtDct")

        if recovered is None or len(recovered) == 0:
            print(f"  [WM-DWT] ✗ Decoder returned empty payload")
            return None

        print(f"  [WM-DWT] Raw payload: {recovered.hex()} ({len(recovered)} bytes)")
        print(f"  [WM-DWT] Raw repr: {repr(recovered)}")

        sig = validate_payload(recovered)
        if sig:
            print(f"  [WM-DWT] ✓ Valid OX header → signature: {sig}")
            return sig.lower()  # Normalize to lowercase
        else:
            # Try to find OX header at different positions (in case of bit errors)
            if len(recovered) >= 2:
                header_pos = recovered.find(PAYLOAD_HEADER)
                if header_pos >= 0 and header_pos + PAYLOAD_SIZE <= len(recovered):
                    alt_payload = recovered[header_pos:header_pos + PAYLOAD_SIZE]
                    alt_sig = validate_payload(alt_payload)
                    if alt_sig:
                        print(f"  [WM-DWT] ✓ Found OX header at offset {header_pos} → signature: {alt_sig}")
                        return alt_sig.lower()
            print(f"  [WM-DWT] ✗ No valid OX header (got: {recovered[:min(8, len(recovered))].hex()})")
            return None

    except ImportError as e:
        print(f"  [WM-DWT] ✗ Missing dependencies: {e}")
        return None
    except Exception as e:
        print(f"  [WM-DWT] ✗ DwtDct extract FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


# ── LSB LAYER ───────────────────────────────────────────

def _lsb_embed(image_bytes: bytes, sig_hex: str) -> bytes:
    """Embed signature via LSB steganography.
    Format: ORIGINX:<12-char-sig-hex>:END in pixel LSBs."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    pixels = list(img.getdata())
    message = f"ORIGINX:{sig_hex}:END"
    bits = "".join(format(ord(c), "08b") for c in message)
    print(f"  [WM-LSB] Embedding: '{message}' ({len(bits)} bits into {len(pixels)} pixels)")

    new_pixels = []
    bit_idx = 0
    for pixel in pixels:
        r, g, b = pixel
        if bit_idx < len(bits):
            r = (r & ~1) | int(bits[bit_idx])
            bit_idx += 1
        if bit_idx < len(bits):
            g = (g & ~1) | int(bits[bit_idx])
            bit_idx += 1
        if bit_idx < len(bits):
            b = (b & ~1) | int(bits[bit_idx])
            bit_idx += 1
        new_pixels.append((r, g, b))
    result = Image.new("RGB", img.size)
    result.putdata(new_pixels)
    buf = io.BytesIO()
    result.save(buf, format="PNG")
    return buf.getvalue()


def _lsb_extract(image_bytes: bytes) -> str | None:
    """Extract signature from LSB layer. Returns 12-char signature hex or None.
    Tries multiple bit offsets to handle alignment issues."""
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        pixels = list(img.getdata())
        
        # Extract more bits to handle potential offsets and larger messages
        # ORIGINX:<12 hex chars>:END = 27 chars × 8 bits = 216 bits
        # Try up to 1000 bits to handle offsets and ensure we capture the watermark
        max_bits = min(1000, len(pixels) * 3)
        bits = ""
        for pixel in pixels:
            for channel in pixel:
                bits += str(channel & 1)
                if len(bits) >= max_bits:
                    break
            if len(bits) >= max_bits:
                break
        
        # Try multiple bit offsets (0, 1, 2, 3) to handle alignment issues
        for offset in range(4):
            if offset >= len(bits):
                continue
                
            offset_bits = bits[offset:]
            # Convert bits to characters, filtering out invalid ASCII
            chars = []
            for i in range(0, len(offset_bits) - 7, 8):
                try:
                    byte_val = int(offset_bits[i:i+8], 2)
                    # Only accept printable ASCII characters (32-126) and common control chars
                    if 32 <= byte_val <= 126 or byte_val in [9, 10, 13]:  # printable + tab, LF, CR
                        chars.append(chr(byte_val))
                    else:
                        # If we hit invalid char, try to find marker in what we have so far
                        break
                except (ValueError, OverflowError):
                    break
            
            message = "".join(chars)
            
            # Current format: ORIGINX:<sig>:END
            if "ORIGINX:" in message and ":END" in message:
                start = message.index("ORIGINX:") + 8
                end = message.index(":END", start)
                sig_hex = message[start:end].strip()
                # Validate signature is hex and reasonable length (12 chars for 6 bytes)
                if len(sig_hex) == 12 and all(c in '0123456789abcdefABCDEF' for c in sig_hex):
                    print(f"  [WM-LSB] ✓ Extracted (offset={offset}): '{sig_hex}'")
                    return sig_hex.lower()  # Normalize to lowercase
            
            # Legacy format: <seed>||ORIGINX|| (backward compat)
            if "||ORIGINX||" in message:
                raw_seed = message.split("||ORIGINX||")[0].strip()
                sig_hex = compute_signature(raw_seed)
                print(f"  [WM-LSB] ✓ Legacy format (offset={offset}) → computed sig: {sig_hex}")
                return sig_hex
            
            # Also try searching for partial matches in case of corruption
            if "ORIGINX:" in message:
                start = message.index("ORIGINX:") + 8
                # Try to extract hex even if :END is missing
                remaining = message[start:]
                # Extract up to 12 hex characters
                sig_candidate = ""
                for c in remaining:
                    if c in '0123456789abcdefABCDEF':
                        sig_candidate += c
                        if len(sig_candidate) >= 12:
                            break
                    elif sig_candidate:  # Stop if we hit non-hex after starting
                        break
                if len(sig_candidate) == 12:
                    print(f"  [WM-LSB] ✓ Extracted partial (offset={offset}, no :END): '{sig_candidate}'")
                    return sig_candidate.lower()

        print(f"  [WM-LSB] ✗ No marker found in {max_bits} bits (tried offsets 0-3)")
        return None
    except Exception as e:
        print(f"  [WM-LSB] ✗ LSB extract FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None