"""
Media Gateway — Image generation, TTS, and multi-model inference routing.
Uses CodexSale for images, OpenRouter for TTS and multi-model routing.
"""
import urllib.request
import json
import os

from letta_keys import load_key

# Load API keys
CODEXSALE_KEY = load_key("codex_sale.key", "CODEXSALE_API_KEY", "CODEX_SALE_API_KEY")
OPENROUTER_KEY = load_key("openrouter.key", "OPENROUTER_API_KEY")

CODEXSALE_BASE = "https://codex.sale/v1"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def _post_json(url, payload, api_key, timeout=60):
    """POST JSON to an API endpoint."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


# ============================================================
# IMAGE GENERATION — via CodexSale (gpt-image-2)
# $0.05 per image via x402
# ============================================================
def generate_image(prompt: str, size: str = "1024x1024", model: str = "gpt-image-2"):
    """Generate an image from a text prompt."""
    if not CODEXSALE_KEY:
        return {"error": "Image generation not configured", "status": "error"}

    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
        }
        result = _post_json(f"{CODEXSALE_BASE}/images/generations", payload, CODEXSALE_KEY, timeout=120)

        # Return the image data
        images = result.get("data", [])
        if images:
            return {
                "prompt": prompt,
                "model": model,
                "size": size,
                "image_url": images[0].get("url", ""),
                "revised_prompt": images[0].get("revised_prompt", prompt),
                "provider": "AgentServices Media Gateway",
            }
        return {"error": "No image in response", "raw": str(result)[:500]}
    except Exception as e:
        return {"error": str(e), "status": "error"}


# ============================================================
# TEXT-TO-SPEECH — via OpenRouter (gpt-audio, gpt-audio-mini)
# $0.05 per call via x402
# ============================================================
def text_to_speech(text: str, model: str = "openai/gpt-audio-mini", voice: str = "alloy"):
    """Convert text to speech audio."""
    if not OPENROUTER_KEY:
        return {"error": "TTS not configured", "status": "error"}

    try:
        # Use OpenRouter's audio API
        payload = {
            "model": model,
            "input": text,
            "voice": voice,
        }
        result = _post_json(f"{OPENROUTER_BASE}/audio/speech", payload, OPENROUTER_KEY, timeout=60)

        return {
            "text": text[:200],
            "model": model,
            "voice": voice,
            "audio_url": result.get("url", ""),
            "provider": "AgentServices Media Gateway",
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}


# ============================================================
# MULTI-MODEL INFERENCE ROUTING — via OpenRouter
# $0.03 per call via x402
# ============================================================
def multi_model_inference(model: str, messages: list, temperature: float = 0.7, max_tokens: int = 1000):
    """Route inference to ANY model via OpenRouter. 344+ models available."""
    if not OPENROUTER_KEY:
        return {"error": "Multi-model routing not configured", "status": "error"}

    try:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        result = _post_json(f"{OPENROUTER_BASE}/chat/completions", payload, OPENROUTER_KEY, timeout=60)

        result["provider"] = "AgentServices Multi-Model Gateway"
        result["model_requested"] = model
        result["x402_paid"] = True
        return result
    except Exception as e:
        return {"error": str(e), "status": "error"}


def list_all_models():
    """List all available models across CodexSale and OpenRouter."""
    models = {"codexsale": [], "openrouter": [], "total": 0}

    # CodexSale models
    try:
        req = urllib.request.Request(
            f"{CODEXSALE_BASE}/models",
            headers={"Authorization": f"Bearer {CODEXSALE_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            for m in data.get("data", []):
                mid = m.get("id", "")
                if "image" in mid:
                    models["codexsale"].append({"id": mid, "type": "image"})
                else:
                    models["codexsale"].append({"id": mid, "type": "llm"})
    except: pass

    # OpenRouter models
    try:
        req = urllib.request.Request(
            f"{OPENROUTER_BASE}/models",
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            for m in data.get("data", []):
                mid = m.get("id", "")
                mid_lower = mid.lower()
                if "audio" in mid_lower or "tts" in mid_lower:
                    models["openrouter"].append({"id": mid, "type": "tts"})
                elif "image" in mid_lower:
                    models["openrouter"].append({"id": mid, "type": "image"})
                else:
                    models["openrouter"].append({"id": mid, "type": "llm"})
    except: pass

    models["total"] = len(models["codexsale"]) + len(models["openrouter"])
    return models
