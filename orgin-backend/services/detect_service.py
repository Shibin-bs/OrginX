import io
import os
import json
import hashlib
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

FORENSICS_SYSTEM_PROMPT = """You are an expert digital forensics analyst working for OriginX — a data dignity and deepfake accountability platform.

Examine these markers:
ANATOMICAL: Eye reflection consistency, teeth boundary rendering, ear cartilage topology, hair boundary artifacts.
PHYSICS: Skin texture uniformity, chromatic aberration absence, subsurface scattering, shadow direction consistency.
GENERATION ARTIFACTS: Background-subject boundary blending, jewelry reflections, glasses lens physics.

Return ONLY valid JSON, no markdown:
{
  "verdict": "SYNTHETIC" | "AUTHENTIC" | "INCONCLUSIVE",
  "confidence": float 0.0-1.0,
  "probable_method": "GAN" | "DIFFUSION" | "FACE_SWAP" | "AUTHENTIC" | "UNKNOWN",
  "artifacts_found": [list of specific observations],
  "anatomical_flags": int,
  "physics_flags": int,
  "summary": "2 sentence plain English verdict"
}"""


def _ela_score(image_bytes: bytes) -> float:
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=75)
        compressed = Image.open(buf).convert("RGB")
        orig_arr = np.array(img, dtype=float)
        comp_arr = np.array(compressed, dtype=float)
        diff = np.abs(orig_arr - comp_arr)
        ela = np.mean(diff) / 255.0
        return float(min(ela * 10.0, 1.0))
    except Exception:
        return 0.3


def _noise_score(image_bytes: bytes) -> float:
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("L")
        arr = np.array(img, dtype=float)
        smoothed = gaussian_filter(arr, sigma=2)
        noise = arr - smoothed
        std = np.std(noise)
        if std < 8.0:
            score = 0.85
        elif std > 18.0:
            score = 0.15
        else:
            score = 0.85 - ((std - 8.0) / (18.0 - 8.0)) * 0.70
        return float(np.clip(score, 0.0, 1.0))
    except Exception:
        return 0.3


def _fft_score(image_bytes: bytes) -> float:
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("L")
        arr = np.array(img, dtype=float)
        fft = np.fft.fft2(arr)
        fft_mag = np.abs(np.fft.fftshift(fft))
        h, w = fft_mag.shape
        cy, cx = h // 2, w // 2
        radius = min(h, w) // 8
        ring = fft_mag[cy - radius:cy + radius, cx - radius:cx + radius]
        periodicity = float(np.max(ring) / (np.mean(ring) + 1e-8))
        score = min((periodicity - 1.0) / 15.0, 1.0)
        return float(np.clip(score, 0.0, 1.0))
    except Exception:
        return 0.3


def _image_hash(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()


def _gemini_analyze(image_bytes: bytes, auto_confidence: float) -> dict | None:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=FORENSICS_SYSTEM_PROMPT,
        )
        import PIL.Image
        pil_img = PIL.Image.open(io.BytesIO(image_bytes)).convert("RGB")
        response = model.generate_content([
            pil_img,
            f"Analyze this image. OriginX automated analysis scored it {auto_confidence:.0%} suspicious. Confirm or challenge.",
        ])
        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception:
        return None


def detect_deepfake(image_bytes: bytes) -> dict:
    ela = _ela_score(image_bytes)
    noise = _noise_score(image_bytes)
    freq = _fft_score(image_bytes)
    confidence = ela * 0.4 + noise * 0.3 + freq * 0.3
    is_deepfake = confidence > 0.55
    gemini_result = None
    if 0.35 < confidence < 0.75 and GEMINI_API_KEY:
        gemini_result = _gemini_analyze(image_bytes, confidence)
        if gemini_result:
            g_conf = gemini_result.get("confidence", confidence)
            confidence = confidence * 0.4 + g_conf * 0.6
            is_deepfake = confidence > 0.55
    return {
        "is_deepfake": bool(is_deepfake),
        "confidence": round(float(confidence), 3),
        "signals": {
            "ela_score": round(ela, 3),
            "noise_score": round(noise, 3),
            "freq_score": round(freq, 3),
        },
        "gemini_analysis": gemini_result,
        "image_hash": _image_hash(image_bytes),
    }