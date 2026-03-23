import io
import json
import uuid
import os
from datetime import datetime
from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import ProvenanceLog
from services.detect_service import detect_deepfake
from services import gemini_service
from routes.watermark import lookup_signature, _normalize_image

router = APIRouter()


class ReportRequest(BaseModel):
    detection_result: dict


@router.post("/analyze")
async def analyze(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw = await file.read()
    
    # Try with raw bytes first (preserves original watermark)
    sig_result = lookup_signature(raw, db)
    if not sig_result["found"]:
        # If raw didn't match, try with normalized bytes
        normalized = _normalize_image(raw)
        if normalized != raw:
            print(f"[ANALYZE] Raw didn't match, retrying with normalized ({len(normalized)} bytes)")
            sig_result = lookup_signature(normalized, db)
        else:
            normalized = raw
    else:
        # Still normalize for deepfake detection
        normalized = _normalize_image(raw)
    
    watermark_found = sig_result["found"]
    matched_user = sig_result.get("matched_user")

    detection = detect_deepfake(normalized)
    consent_violated = watermark_found and detection["is_deepfake"]

    if consent_violated:
        detection_type = "DIRECT_VIOLATION"
    elif detection["is_deepfake"] and not watermark_found:
        detection_type = "SYNTHETIC_NO_MATCH"
    elif watermark_found and not detection["is_deepfake"]:
        detection_type = "WATERMARK_AUTHENTIC"
    else:
        detection_type = "CLEAN"

    forensic_report = None
    violation_notice = None
    if consent_violated and os.environ.get("GEMINI_API_KEY", ""):
        forensic_report = gemini_service.generate_forensic_report(detection)
        violation_notice = gemini_service.generate_violation_notice(matched_user, "Unknown Platform")

    log = ProvenanceLog(
        id=str(uuid.uuid4()),
        submitted_image_hash=detection["image_hash"],
        matched_user_handles=json.dumps([matched_user] if matched_user else []),
        is_deepfake=detection["is_deepfake"],
        confidence_score=detection["confidence"],
        created_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()

    return {
        "is_deepfake": detection["is_deepfake"],
        "confidence": detection["confidence"],
        "signals": detection["signals"],
        "gemini_analysis": detection.get("gemini_analysis"),
        "forensic_report": forensic_report,
        "violation_notice": violation_notice,
        "provenance": {
            "watermark_found": watermark_found,
            "matched_user": matched_user,
            "consent_violated": consent_violated,
            "detection_type": detection_type,
            "verification_method": sig_result.get("verification_method"),
        },
        "image_hash": detection["image_hash"],
    }


@router.post("/report")
def report(req: ReportRequest):
    report_text = gemini_service.generate_forensic_report(req.detection_result)
    return {"report": report_text}