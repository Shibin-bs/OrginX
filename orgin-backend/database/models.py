import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class OriginRegistry(Base):
    __tablename__ = "origin_registry"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_handle = Column(String, nullable=False, unique=True)
    public_key_hash = Column(String, nullable=False, unique=True)
    watermark_seed = Column(String, nullable=False)
    # Canonical signature: hex(SHA256(seed)[:6]) — 12-char hex, the matching key
    signature_hash = Column(String, nullable=True, index=True)
    registered_at = Column(DateTime, default=datetime.utcnow)
    media_count = Column(Integer, default=0)


class ProvenanceLog(Base):
    __tablename__ = "provenance_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submitted_image_hash = Column(String, nullable=False)
    matched_user_handles = Column(Text, default="[]")
    is_deepfake = Column(Boolean, default=False)
    confidence_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class WatermarkedMedia(Base):
    __tablename__ = "watermarked_media"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_handle = Column(String, nullable=False)
    image_hash = Column(String, nullable=False, index=True)       # pixel-level SHA-256
    perceptual_hash = Column(String, nullable=False, index=True)  # DCT pHash
    signature_hash = Column(String, nullable=False, index=True)   # same as OriginRegistry.signature_hash
    original_filename = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)