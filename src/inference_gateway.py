"""
LLM Inference Gateway — x402-paid proxy for AI model inference.
400+ models via OpenRouter. Dynamic pricing: provider cost + 5%, floor $0.003.

Agents pay per inference call via x402. We proxy through OpenRouter for
universal model access (Claude, GPT, Gemini, DeepSeek, Grok, Llama, etc.)

OpenAI-compatible: POST /v1/chat/completions works with any OpenAI SDK.
"""
import urllib.request
import json
import os

from letta_keys import load_key

# Load OpenRouter key (primary multi-model gateway)
OPENROUTER_KEY = load_key("openrouter.key", "OPENROUTER_API_KEY")
OPENROUTER_BASE = "https://openrouter.ai/api/v1"

# Load CodexSale key (fallback for GPT models)
CODEXSALE_KEY = load_key("codex_sale.key", "CODEXSALE_API_KEY", "CODEX_SALE_API_KEY")
CODEXSALE_BASE_URL = "https://codex.sale/v1"

# Load Gemini key (free tier, highest margin)
GEMINI_KEY = load_key("gemini.key", "GEMINI_API_KEY")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Curated model catalog
CURATED_MODELS = [
    {"id": "openai/gpt-5.6-terra", "provider": "openai", "tier": "balanced", "context": "128K"},
    {"id": "openai/gpt-5.6-luna", "provider": "openai", "tier": "balanced", "context": "128K"},
    {"id": "openai/gpt-5.4", "provider": "openai", "tier": "balanced", "context": "128K"},
    {"id": "openai/gpt-5.4-mini", "provider": "openai", "tier": "standard", "context": "128K"},
    {"id": "anthropic/claude-opus-5", "provider": "anthropic", "tier": "premium", "context": "200K"},
    {"id": "anthropic/claude-sonnet-5", "provider": "anthropic", "tier": "balanced", "context": "200K"},
    {"id": "anthropic/claude-haiku-5", "provider": "anthropic", "tier": "balanced", "context": "200K"},
    {"id": "google/gemini-3.6-flash", "provider": "google", "tier": "standard", "context": "1M"},
    {"id": "google/gemini-3.5-flash-lite", "provider": "google", "tier": "standard", "context": "1M"},
    {"id": "x-ai/grok-4.5", "provider": "xai", "tier": "balanced", "context": "128K"},
    {"id": "x-ai/grok-4.3", "provider": "xai", "tier": "standard", "context": "128K"},
    {"id": "deepseek/deepseek-v4-flash", "provider": "deepseek", "tier": "standard", "context": "64K"},
    {"id": "deepseek/deepseek-v4-pro", "provider": "deepseek", "tier": "balanced", "context": "64K"},
    {"id": "meta-llama/llama-4-maverick", "provider": "meta", "tier": "standard", "context": "128K"},
    {"id": "meta-llama/llama-4-scout", "provider": "meta", "tier": "standard", "context": "128K"},
]

# Smart Router profiles
ROUTER_PROFILES = {
    "auto": {
        "reasoning": "deepseek/deepseek-v4-pro",
        "coding": "deepseek/deepseek-v4-flash",
        "creative": "anthropic/claude-sonnet-5",
        "analysis": "google/gemini-3.6-flash",
        "simple": "google/gemini-3.5-flash-lite",
        "trading": "x-ai/grok-4.3",
        "default": "deepseek/deepseek-v4-flash",
    },
    "eco": {
        "default": "google/gemini-3.5-flash-lite",
        "reasoning": "deepseek/deepseek-v4-flash",
    },
    "premium": {
        "default": "anthropic/claude-opus-5",
        "coding": "openai/gpt-5.6-terra",
    },
    "free": {
        "default": "meta-llama/llama-4-scout",
    },
}

TASK_KEYWORDS = {
    "coding": ["code", "function", "bug", "refactor", "api", "debug", "typescript", "python", "javascript", "react", "sql", "compile", "stack trace", "error", "fix", "implement", "deploy", "docker", "kubernetes"],
    "reasoning": ["prove", "explain why", "analyze", "deduce", "because", "therefore", "logic", "math", "theorem", "proof", "derive", "calculate"],
    "creative": ["write", "story", "poem", "marketing", "copy", "headline", "slogan", "brand", "creative", "content", "blog", "article"],
    "trading": ["btc", "eth", "price", "market", "trade", "buy", "sell", "signal", "portfolio", "crypto", "token", "defi", "yield", "liquidity"],
    "analysis": ["data", "chart", "graph", "trend", "statistics", "report", "summary", "compare", "benchmark", "metric"],
}


def _detect_category(messages: list) -> str:
    text = " ".join(m.get("content", "") for m in messages).lower()
    scores = {}
    for category, keywords in TASK_KEYWORDS.items():
        scores[category] = sum(1 for kw in keywords if kw in text)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "default"


def _route_model(model: str, messages: list, profile: str = "auto") -> str:
    if model and model != "auto":
        return model
    category = _detect_category(messages)
    profile_map = ROUTER_PROFILES.get(profile, ROUTER_PROFILES["auto"])
    return profile_map.get(category, profile_map.get("default", "deepseek/deepseek-v4-flash"))


def list_models():
    from pricing_cache import pricing_summary as _ps
    return {
        "models": [{"id": m["id"], "context": m["context"]} for m in CURATED_MODELS],
        "pricing": "Dynamic: provider cost + 5%, floor $0.003. Calculated per request from model, input size, and max_tokens.",
        "pricing_details": _ps(),
        "default": "auto",
        "router_profiles": list(ROUTER_PROFILES.keys()),
        "total_curated": len(CURATED_MODELS),
        "total_available": "400+ via OpenRouter",
        "note": "Use model='auto' for smart routing. POST /v1/chat/completions is OpenAI-compatible. Price varies by model.",
    }


def list_all_openrouter_models():
    if not OPENROUTER_KEY:
        return {"models": [], "error": "OpenRouter not configured"}
    try:
        req = urllib.request.Request(
            f"{OPENROUTER_BASE}/models",
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        models = data.get("data", [])
        return {
            "total": len(models),
            "models": [{"id": m["id"], "pricing": m.get("pricing", {}), "context": m.get("context_length", "?")} for m in models[:100]],
            "note": f"Showing first 100 of {len(models)} models. Price per call = provider cost + 5%, floor $0.003.",
        }
    except Exception as e:
        return {"error": str(e)}


def inference(model, messages=None, temperature=0.7, max_tokens=1000, stream=False, profile="auto"):
    if messages is None:
        messages = []
    resolved_model = _route_model(model, messages, profile)

    if resolved_model.startswith(("openai/", "anthropic/", "google/", "x-ai/", "deepseek/", "meta-llama/", "~")):
        result = _call_openrouter(resolved_model, messages, temperature, max_tokens)
    elif resolved_model.startswith("gemini-"):
        result = _call_gemini(resolved_model, messages, temperature, max_tokens)
    elif resolved_model in ("gpt-5.4", "gpt-5.4-mini", "gpt-5.5"):
        result = _call_codexsale(resolved_model, messages, temperature, max_tokens, stream)
    else:
        result = _call_openrouter(resolved_model, messages, temperature, max_tokens)

    return result


def chat_completions(model, messages, temperature=0.7, max_tokens=1000, **kwargs):
    return inference(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)


def _call_openrouter(model, messages, temperature, max_tokens):
    if not OPENROUTER_KEY:
        return {"error": "Inference backend not configured", "status": "error"}
    payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    try:
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{OPENROUTER_BASE}/chat/completions",
            data=req_data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {OPENROUTER_KEY}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read().decode())
        result["provider"] = "AgentServices Inference Gateway"
        result["model_requested"] = model
        result["x402_paid"] = True
        return result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        return {"error": f"Backend error: {e.code} {e.reason}", "details": error_body[:500], "status": "backend_error", "model": model}
    except Exception as e:
        return {"error": str(e), "status": "error", "model": model}


def _call_gemini(model, messages, temperature, max_tokens):
    if not GEMINI_KEY:
        or_model = f"google/{model}" if not model.startswith("google/") else model
        return _call_openrouter(or_model, messages, temperature, max_tokens)
    contents = []
    system_instruction = None
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            system_instruction = {"parts": [{"text": content}]}
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": content}]})
        else:
            contents.append({"role": "user", "parts": [{"text": content}]})
    payload = {"contents": contents, "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}}
    if system_instruction:
        payload["systemInstruction"] = system_instruction
    try:
        req_data = json.dumps(payload).encode("utf-8")
        url = f"{GEMINI_BASE_URL}/models/{model}:generateContent?key={GEMINI_KEY}"
        req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
        candidates = result.get("candidates", [])
        text_parts = []
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text_parts = [p.get("text", "") for p in parts]
        return {
            "id": f"agentservices-gemini-{model}", "object": "chat.completion", "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "".join(text_parts)}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": result.get("usageMetadata", {}).get("promptTokenCount", 0), "completion_tokens": result.get("usageMetadata", {}).get("candidatesTokenCount", 0), "total_tokens": result.get("usageMetadata", {}).get("totalTokenCount", 0)},
            "provider": "AgentServices Inference Gateway (Google Gemini)", "model_requested": model, "x402_paid": True,
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}


def _call_codexsale(model, messages, temperature, max_tokens, stream):
    if not CODEXSALE_KEY:
        return _call_openrouter(f"openai/{model}", messages, temperature, max_tokens)
    payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens, "stream": False}
    try:
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(f"{CODEXSALE_BASE_URL}/chat/completions", data=req_data, headers={"Content-Type": "application/json", "Authorization": f"Bearer {CODEXSALE_KEY}"}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
        result["provider"] = "AgentServices Inference Gateway"
        result["model_requested"] = model
        result["x402_paid"] = True
        return result
    except Exception:
        return _call_openrouter(f"openai/{model}", messages, temperature, max_tokens)


def quick_complete(prompt, model="auto", max_tokens=500):
    return inference(model=model, messages=[{"role": "user", "content": prompt}], max_tokens=max_tokens)
