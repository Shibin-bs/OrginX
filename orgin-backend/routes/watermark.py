import io
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import OriginRegistry, WatermarkedMedia
from services.watermark_service import (
    embed_watermark, extract_watermark, compute_signature,
    compute_pixel_hash, compute_perceptual_hash, hamming_distance,
    match_signature_tolerant,
)
from services.authenticity_service import authenticity_check

router = APIRouter()

# Perceptual hash hamming distance threshold
PHASH_THRESHOLD = 30


def _normalize_image(data: bytes) -> bytes:
    """Normalize image to RGB PNG. Handles edge cases gracefully."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        print(f"[WARN] _normalize_image failed: {e}, using raw bytes ({len(data)} bytes)")
        return data


def lookup_signature(image_bytes: bytes, db: Session) -> dict:
    """4-strategy signature lookup cascade:
    1. Pixel hash exact match (re-encode stable)
    2. Perceptual hash similarity (screenshot/compression stable)
    3. DwtDct embedded payload extraction
    4. LSB embedded payload extraction
    Returns match result dict."""
    print(f"\n{'='*60}")
    print(f"[LOOKUP] Starting 4-strategy signature lookup ({len(image_bytes)} bytes)")

    # Compute hashes for strategy 1 & 2
    pix_hash = compute_pixel_hash(image_bytes)
    print(f"[LOOKUP] Pixel hash: {pix_hash[:16]}...")

    # ── Strategy 1: Pixel hash exact match ──
    exact = db.query(WatermarkedMedia).filter(
        WatermarkedMedia.image_hash == pix_hash
    ).first()
    if exact:
        record = db.query(OriginRegistry).filter(
            OriginRegistry.user_handle == exact.user_handle
        ).first()
        print(f"[LOOKUP] ✓ STRATEGY 1 — PIXEL HASH MATCH → @{exact.user_handle}")
        return _success(exact.user_handle, record, "PIXEL_HASH_MATCH",
                        f"image pixel data matches registered watermark for @{exact.user_handle}")

    # ── Strategy 2: Perceptual hash similarity ──
    try:
        p_hash = compute_perceptual_hash(image_bytes)
        print(f"[LOOKUP] Perceptual hash: {p_hash[:16]}...")
        all_media = db.query(WatermarkedMedia).all()
        print(f"[LOOKUP] Comparing pHash against {len(all_media)} registered images")
        best_match = None
        best_dist = PHASH_THRESHOLD + 1
        for m in all_media:
            dist = hamming_distance(p_hash, m.perceptual_hash)
            if dist < best_dist:
                best_dist = dist
                best_match = m
        if best_match and best_dist <= PHASH_THRESHOLD:
            record = db.query(OriginRegistry).filter(
                OriginRegistry.user_handle == best_match.user_handle
            ).first()
            similarity = round(max(0, (1 - best_dist / 64) * 100), 1)
            print(f"[LOOKUP] ✓ STRATEGY 2 — PERCEPTUAL HASH MATCH → @{best_match.user_handle} (dist={best_dist})")
            result = _success(best_match.user_handle, record, "PERCEPTUAL_HASH_MATCH",
                              f"image is a near-match to registered watermark for @{best_match.user_handle}")
            result["similarity"] = similarity
            return result
        else:
            print(f"[LOOKUP] ✗ Strategy 2: best dist={best_dist}, threshold={PHASH_THRESHOLD}")
    except Exception as e:
        print(f"[LOOKUP] ✗ Strategy 2 error: {e}")

    # ── Strategy 3+4: Embedded watermark extraction ──
    print(f"[LOOKUP] Trying embedded watermark extraction (DwtDct → LSB)...")
    recovered_sig = extract_watermark(image_bytes)
    if recovered_sig:
        print(f"[LOOKUP] Recovered signature: '{recovered_sig}'")
        # Match against all registered users
        records = db.query(OriginRegistry).all()
        for r in records:
            stored_sig = r.signature_hash
            if not stored_sig:
                # Legacy: compute on the fly
                stored_sig = compute_signature(r.watermark_seed)
            if match_signature_tolerant(recovered_sig, stored_sig, max_hamming=2):
                hamming = bin(int(recovered_sig, 16) ^ int(stored_sig, 16)).count('1') if recovered_sig != stored_sig else 0
                print(f"[LOOKUP] ✓ STRATEGY 3/4 — EMBEDDED WATERMARK MATCH → @{r.user_handle} (hamming={hamming})")
                return _success(r.user_handle, r, "EMBEDDED_WATERMARK",
                                f"embedded watermark signature matches @{r.user_handle}")
        print(f"[LOOKUP] ✗ Signature '{recovered_sig}' didn't match any registered user")
        return {
            "found": False,
            "matched_user": None,
            "verification_method": "WATERMARK_NO_MATCH",
            "recovered_signature": recovered_sig,
            "message": "Watermark payload extracted but does not match any registered identity",
        }

    print(f"[LOOKUP] ✗ No watermark detected by any strategy")
    return {
        "found": False,
        "matched_user": None,
        "verification_method": "NO_SIGNATURE",
        "message": "No OriginX signature detected in this image",
    }


def _success(user_handle: str, record, method: str, detail: str) -> dict:
    """Build a successful match response."""
    return {
        "found": True,
        "matched_user": user_handle,
        "public_key_hash": record.public_key_hash if record else None,
        "registered_at": record.registered_at.isoformat() if record and hasattr(record, 'registered_at') else None,
        "verification_method": method,
        "message": f"✓ OriginX signature verified — {detail}",
    }

# ── Ownership Declaration Text ──
OWNERSHIP_DECLARATION = (
    "I hereby declare that this image is my original work, created by me, "
    "and I am the rightful owner of all rights to this content. "
    "I understand that OriginX will permanently record this declaration along with "
    "my identity and a cryptographic fingerprint of this image. "
    "If I am found to have falsely claimed ownership of this content, "
    "I acknowledge that I shall be liable to face legal consequences under "
    "applicable intellectual property and fraud laws. "
    "This declaration is binding and irrevocable."
)

# Duplicate detection: perceptual hash threshold for "same image"
DUPLICATE_PHASH_THRESHOLD = 12


def _check_duplicate(image_bytes: bytes, requesting_user: str, db: Session) -> dict | None:
    """
    Check if this image (or a near-duplicate) is already registered
    by a DIFFERENT user. Returns match info dict if found, None otherwise.
    This is the core anti-fraud mechanism — prevents scammers from
    claiming someone else's already-registered work.
    """
    try:
        pix_hash = compute_pixel_hash(image_bytes)
        p_hash = compute_perceptual_hash(image_bytes)
    except Exception:
        return None

    # Exact pixel match
    exact = db.query(WatermarkedMedia).filter(
        WatermarkedMedia.image_hash == pix_hash
    ).first()
    if exact and exact.user_handle != requesting_user:
        return {
            "already_registered_by": f"@{exact.user_handle}",
            "match_type": "EXACT_PIXEL_MATCH",
            "message": (
                f"This exact image is already registered by @{exact.user_handle}. "
                f"You cannot claim ownership of someone else's work."
            ),
        }

    # Perceptual similarity match
    all_media = db.query(WatermarkedMedia).all()
    for m in all_media:
        if m.user_handle == requesting_user:
            continue
        dist = hamming_distance(p_hash, m.perceptual_hash)
        if dist <= DUPLICATE_PHASH_THRESHOLD:
            similarity = round(max(0, (1 - dist / 64) * 100), 1)
            return {
                "already_registered_by": f"@{m.user_handle}",
                "match_type": "PERCEPTUAL_MATCH",
                "similarity": f"{similarity}%",
                "message": (
                    f"A visually identical image ({similarity}% match) is already registered "
                    f"by @{m.user_handle}. This appears to be someone else's work."
                ),
            }

    return None


@router.post("/verify")
async def verify_image(
    file: UploadFile | None = File(None),
    user_handle: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """
    Step 1 of the embed flow: Verify image authenticity and check for duplicates.
    Returns verification result + ownership declaration if the image passes.
    """
    if not file:
        raise HTTPException(status_code=400, detail={"message": "No image file provided."})
    if not user_handle:
        raise HTTPException(status_code=400, detail={"message": "User handle is required."})
    raw = await file.read()
    print(f"\n{'='*60}")
    print(f"[VERIFY] Received {len(raw)} bytes for @{user_handle}")
    normalized = _normalize_image(raw)

    # ── Check if user exists ──
    record = db.query(OriginRegistry).filter(
        OriginRegistry.user_handle == user_handle
    ).first()
    if not record:
        raise HTTPException(
            status_code=400,
            detail={"message": "User handle not found in OriginX registry."}
        )

    # ── Anti-fraud: Check if image is already registered by someone else ──
    duplicate = _check_duplicate(normalized, user_handle, db)
    if duplicate:
        print(f"[VERIFY] ✗ DUPLICATE DETECTED: {duplicate}")
        raise HTTPException(
            status_code=400,
            detail={
                "message": duplicate["message"],
                "duplicate_info": duplicate,
            }
        )

    # ── Forensic authenticity screening ──
    auth_result = authenticity_check(normalized)
    print(f"[VERIFY] Authenticity result: passed={auth_result['passed']}, "
          f"risk={auth_result['risk_score']}")

    if not auth_result["passed"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Image failed authenticity detection and cannot be registered.",
                "analysis": auth_result,
            }
        )

    # ── Image passed all checks ──
    return {
        "verified": True,
        "message": "✓ This image has been verified as authentic.",
        "risk_score": auth_result["risk_score"],
        "signals": auth_result["signals"],
        "ownership_declaration": OWNERSHIP_DECLARATION,
    }


@router.post("/embed")
async def embed(
    file: UploadFile | None = File(None),
    user_handle: str | None = Form(None),
    consent_accepted: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """
    Step 2: Embed watermark. Requires consent_accepted='true'.
    Re-runs authenticity + duplicate checks as a safety gate.
    """
    if not file:
        raise HTTPException(status_code=400, detail={"message": "No image file provided."})
    if not user_handle:
        raise HTTPException(status_code=400, detail={"message": "User handle is required."})

    # ── Validate consent declaration ──
    if consent_accepted is None or consent_accepted.lower() != "true":
        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "Ownership consent declaration is required. "
                    "You must accept the declaration before embedding."
                )
            }
        )

    raw = await file.read()
    print(f"\n{'='*60}")
    print(f"[EMBED] Received {len(raw)} bytes for @{user_handle} (consent=accepted)")
    normalized = _normalize_image(raw)

    record = db.query(OriginRegistry).filter(
        OriginRegistry.user_handle == user_handle
    ).first()
    if not record:
        raise HTTPException(
            status_code=400,
            detail={"message": "User handle not found in OriginX registry."}
        )

    # ── Safety gate: Re-check duplicate ──
    duplicate = _check_duplicate(normalized, user_handle, db)
    if duplicate:
        raise HTTPException(
            status_code=400,
            detail={
                "message": duplicate["message"],
                "duplicate_info": duplicate,
            }
        )

    # ── Safety gate: Re-check authenticity ──
    auth_result = authenticity_check(normalized)
    if not auth_result["passed"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Image failed authenticity detection and cannot be registered.",
                "analysis": auth_result,
            }
        )

    # Ensure signature_hash exists (backfill for legacy users)
    if not record.signature_hash:
        record.signature_hash = compute_signature(record.watermark_seed)
        db.commit()

    watermarked = embed_watermark(normalized, record.watermark_seed)
    print(f"[EMBED] Watermarked image: {len(watermarked)} bytes")

    # Compute pixel hash (stable across re-encodes) + perceptual hash
    pix_hash = compute_pixel_hash(watermarked)
    p_hash = compute_perceptual_hash(watermarked)
    print(f"[EMBED] Pixel hash: {pix_hash[:16]}...")
    print(f"[EMBED] pHash:      {p_hash[:16]}...")

    media_record = WatermarkedMedia(
        id=str(uuid.uuid4()),
        user_handle=user_handle,
        image_hash=pix_hash,
        perceptual_hash=p_hash,
        signature_hash=record.signature_hash,
        original_filename=file.filename or "",
        created_at=datetime.utcnow(),
    )
    db.add(media_record)
    record.media_count += 1
    db.commit()
    print(f"[EMBED] ✓ Stored in WatermarkedMedia (sig={record.signature_hash})")
    print(f"[EMBED] ✓ Ownership consent recorded for @{user_handle}")

    return Response(
        content=watermarked,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename=originx_{file.filename}"},
    )


@router.post("/extract")
async def extract(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw = await file.read()
    print(f"\n[EXTRACT] Received {len(raw)} bytes, type={file.content_type}, name={file.filename}")

    # Try with raw bytes first
    result = lookup_signature(raw, db)
    if result["found"]:
        return result

    # If raw didn't match, try with normalized bytes
    normalized = _normalize_image(raw)
    if normalized != raw:
        print(f"[EXTRACT] Raw didn't match, retrying with normalized ({len(normalized)} bytes)")
        result = lookup_signature(normalized, db)

    return result