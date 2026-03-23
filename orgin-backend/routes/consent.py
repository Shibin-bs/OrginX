import hashlib
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import OriginRegistry
from services.merkle_service import merkle_tree
from services.watermark_service import compute_signature
from services import gemini_service

router = APIRouter()


class RegisterRequest(BaseModel):
    user_handle: str
    watermark_seed: str


class ConsentPolicyRequest(BaseModel):
    natural_language: str


@router.post("/register")
def register_consent(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(OriginRegistry).filter(
        OriginRegistry.user_handle == req.user_handle
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User handle already registered")
    key_hash = hashlib.sha256(req.watermark_seed.encode()).hexdigest()
    sig_hash = compute_signature(req.watermark_seed)
    merkle_tree.add_leaf(key_hash)
    record = OriginRegistry(
        id=str(uuid.uuid4()),
        user_handle=req.user_handle,
        public_key_hash=key_hash,
        watermark_seed=req.watermark_seed,
        signature_hash=sig_hash,
        registered_at=datetime.utcnow(),
        media_count=0,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {
        "id": record.id,
        "user_handle": record.user_handle,
        "public_key_hash": record.public_key_hash,
        "signature_hash": record.signature_hash,
        "merkle_root": merkle_tree.get_root(),
        "registered_at": record.registered_at.isoformat(),
    }


@router.get("/verify/{public_key_hash}")
def verify_consent(public_key_hash: str, db: Session = Depends(get_db)):
    record = db.query(OriginRegistry).filter(
        OriginRegistry.public_key_hash == public_key_hash
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Hash not found in registry")
    idx = next(
        (i for i, leaf in enumerate(merkle_tree.leaves)
         if leaf == hashlib.sha256(record.watermark_seed.encode()).hexdigest()),
        -1,
    )
    proof = merkle_tree.get_proof(idx) if idx >= 0 else []
    return {
        "id": record.id,
        "user_handle": record.user_handle,
        "public_key_hash": record.public_key_hash,
        "signature_hash": record.signature_hash,
        "registered_at": record.registered_at.isoformat(),
        "media_count": record.media_count,
        "merkle_root": merkle_tree.get_root(),
        "merkle_proof": proof,
    }


@router.get("/registry")
def get_registry(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    records = db.query(OriginRegistry).offset(skip).limit(limit).all()
    total = db.query(OriginRegistry).count()
    return {
        "total": total,
        "merkle_root": merkle_tree.get_root(),
        "records": [
            {
                "id": r.id,
                "user_handle": r.user_handle,
                "public_key_hash": r.public_key_hash[:16] + "...",
                "registered_at": r.registered_at.isoformat(),
                "media_count": r.media_count,
            }
            for r in records
        ],
    }


@router.post("/parse-consent")
def parse_consent(req: ConsentPolicyRequest):
    flags = gemini_service.parse_consent_policy(req.natural_language)
    return {"original_statement": req.natural_language, "parsed_flags": flags}