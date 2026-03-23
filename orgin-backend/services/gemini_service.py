import os
import json


def generate_forensic_report(detection_result: dict) -> str:
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"You are a digital forensics expert writing a formal report for OriginX, a data dignity platform. "
            f"Given this detection result: {json.dumps(detection_result)}, write a 3-4 sentence plain English "
            f"forensic narrative explaining what was found, what signals triggered, and what it means for data rights."
        )
        return response.text
    except Exception:
        return "OriginX automated analysis complete. Review signal scores for details."


def parse_consent_policy(natural_language: str) -> dict:
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"Parse this consent statement into JSON flags for OriginX. "
            f"Statement: '{natural_language}'. Return ONLY a JSON object with these boolean keys: "
            f"commercial_use, ai_training, derivative_works, political_use, artistic_use, resharing, attribution_required."
        )
        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception:
        return {
            "commercial_use": False,
            "ai_training": False,
            "derivative_works": False,
            "political_use": False,
            "artistic_use": False,
            "resharing": False,
            "attribution_required": False,
        }


def analyze_image_forensics(image_bytes: bytes, auto_confidence: float) -> str:
    try:
        import google.generativeai as genai
        import PIL.Image
        import io
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
        model = genai.GenerativeModel("gemini-1.5-flash")
        pil_img = PIL.Image.open(io.BytesIO(image_bytes)).convert("RGB")
        response = model.generate_content([
            pil_img,
            f"As a forensic expert for OriginX, describe in 3-5 sentences what visual artifacts "
            f"you observe. Our system scored it {auto_confidence:.0%} suspicious."
        ])
        return response.text
    except Exception:
        return "OriginX visual analysis unavailable."


def generate_violation_notice(matched_user: str, platform: str) -> str:
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"Generate a formal data rights violation notice for OriginX. "
            f"The victim @{matched_user} had their consent signature detected in synthetic media on {platform}. "
            f"Include formal opening, violation description, removal demand, placeholder for date and signature. Under 200 words."
        )
        return response.text
    except Exception:
        return "OriginX notice generation unavailable. Please consult legal counsel."