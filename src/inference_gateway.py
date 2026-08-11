"""
LLM Inference Gateway — x402-paid proxy for AI model inference.
402+ models via OpenRouter. Provider cost + 5% margin.

Agents pay per inference call via x402. We proxy through OpenRouter for
universal model access (Claude, GPT, Gemini, DeepSeek, Grok, Llama, etc.)

OpenAI-compatible: POST /v1/chat/completions works with any OpenAI SDK.
"""
import urllib.request
import json
import os
import time
from pathlib import Path

# Load OpenRouter key (primary multi-model gateway)
OPENROUTER_KEY = Path("/root/.letta/keys/openrouter.key").read_text().strip() if Path("/root/.letta/keys/openrouter.key").exists() else ""
OPENROUTER_BASE = "https://openrouter.ai/api/v1"

# Load CodexSale key (fallback for GPT models)
CODEXSALE_KEY = Path("/root/.letta/keys/codex_sale.key").read_text().strip() if Path("/root/.letta/keys/codex_sale.key").exists() else ""
CODEXSALE_BASE_URL = "https://codex.sale/v1"

# Load Gemini key (free tier, highest margin)
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
_gemini_key_file = Path("/root/.letta/keys/gemini.key")
if not GEMINI_KEY and _gemini_key_file.exists():
    GEMINI_KEY = _gemini_key_file.read_text().strip()
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Curated model catalog (the full 400+ list is dynamic; this is what we advertise)
CURATED_MODELS = [
    # OpenAI
    {"id": "openai/gpt-5.6-terra", "provider": "openai", "category": "reasoning", "context": "128K"},
    {"id": "openai/gpt-5.6-luna", "provider": "openai", "category": "fast", "context": "128K"},
    {"id": "openai/gpt-5.4", "provider": "openai", "category": "balanced", "context": "128K"},
    {"id": "openai/gpt-5.4-mini", "provider": "openai", "category": "economy", "context": "128K"},
    # Anthropic
    {"id": "anthropic/claude-opus-5", "provider": "anthropic", "category": "reasoning", "context": "200K"},
    {"id": "anthropic/claude-sonnet-5", "provider": "anthropic", "category": "balanced", "context": "200K"},
    {"id": "anthropic/claude-haiku-5", "provider": "anthropic", "category": "fast", "context": "200K"},
    # Google
    {"id": "google/gemini-3.6-flash", "provider": "google", "category": "fast", "context": "1M"},
    {"id": "google/gemini-3.5-flash-lite", "provider": "google", "category": "economy", "context": "1M"},
    # xAI
    {"id": "x-ai/grok-4.5", "provider": "xai", "category": "reasoning", "context": "128K"},
    {"id": "x-ai/grok-4.3", "provider": "xai", "category": "balanced", "context": "128K"},
    # DeepSeek
    {"id": "deepseek/deepseek-v4-flash", "provider": "deepseek", "category": "economy", "context": "64K"},
    {"id": "deepseek/deepseek-v4-pro", "provider": "deepseek", "category": "reasoning", "context": "64K"},
    # Meta
    {"id": "meta-llama/llama-4-maverick", "provider": "meta", "category": "balanced", "context": "128K"},
    {"id": "meta-llama/llama-4-scout", "provider": "meta", "category": "fast", "context": "128K"},
    # Legacy aliases (backward compat with existing callers)
    {"id": "gpt-5.4", "provider": "codexsale", "category": "balanced", "context": "128K", "_alias": True},
    {"id": "gpt-5.4-mini", "provider": "codexsale", "category": "economy", "context": "128K", "_alias": True},
    {"id": "gpt-5.5", "provider": "codexsale", "category": "reasoning", "context": "128K", "_alias": True},
    {"id": "gemini-2.0-flash", "provider": "gemini", "category": "economy", "context": "1M", "_alias": True},
    {"id": "gemini-2.5-flash", "provider": "gemini", "category": "fast", "context": "1M", "_alias": True},
    {"id": "gemini-2.5-pro", "provider": "gemini", "category": "reasoning", "context": "1M", "_alias": True},
]

# Smart Router: map task categories to best-value models
# Category is detected from the prompt content
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

# Keywords for task classification
TASK_KEYWORDS = {
    "coding": ["code", "function", "bug", "refactor", "api", "debug", "typescript", "python", "javascript", "react", "sql", "compile", "stack trace", "error", "fix", "implement", "deploy", "docker", "kubernetes"],
    "reasoning": ["prove", "explain why", "analyze", "deduce", "because", "therefore", "logic", "math", "theorem", "proof", "derive", "calculate"],
    "creative": ["write", "story", "poem", "marketing", "copy", "headline", "slogan", "brand", "creative", "content", "blog", "article"],
    "trading": ["btc", "eth", "price", "market", "trade", "buy", "sell", "signal", "portfolio", "crypto", "token", "defi", "yield", "liquidity"],
    "analysis": ["data", "chart", "graph", "trend", "statistics", "report", "summary", "compare", "benchmark", "metric"],
}


def _detect_category(messages: list) -> str:
    """Classify the task from message content."""
    text = " ".join(m.get("content", "") for m in messages).lower()
    scores = {}
    for category, keywords in TASK_KEYWORDS.items():
        scores[category] = sum(1 for kw in keywords if kw in text)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "default"


def _route_model(model: str, messages: list, profile: str = "auto") -> str:
    """
    Smart Router: if model is 'auto', classify the task and pick the best model.
    Returns the resolved model ID.
    """
    if model and model != "auto":
        return model

    category = _detect_category(messages)
    profile_map = ROUTER_PROFILES.get(profile, ROUTER_PROFILES["auto"])
    return profile_map.get(category, profile_map.get("default", "deepseek/deepseek-v4-flash"))


def list_models():
    """List available models for inference."""
    return {
        "models": [{"id": m["id"], "category": m["category"], "context": m["context"]} for m in CURATED_MODELS if not m.get("_alias")],
        "aliases": [m["id"] for m in CURATED_MODELS if m.get("_alias")],
        "default": "auto",
        "router_profiles": list(ROUTER_PROFILES.keys()),
        "total_curated": len([m for m in CURATED_MODELS if not m.get("_alias")]),
        "total_available": "400+ via OpenRouter",
        "pricing": "Provider cost + 5%. $0.03-$0.05 per call via x402 (USDC on Base).",
        "note": "Use model='auto' for smart routing. POST /v1/chat/completions is OpenAI-compatible.",
    }


def list_all_openrouter_models():
    """Fetch the full live model list from OpenRouter."""
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
            "models": [{"id": m["id"], "context": m.get("context_length", "?")} for m in models[:50]],
            "note": f"Showing first 50 of {len(models)} models. Full list at /v1/models.",
        }
    except Exception as e:
        return {"error": str(e)}


def inference(
    model: str = "auto",
    messages: list = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    stream: bool = False,
    profile: str = "auto",
):
    """
    Proxy a chat completion request. Routes to the best model.

    Args:
        model: Model ID or 'auto' for smart routing
        messages: List of {role, content} messages (OpenAI format)
        temperature: 0.0-2.0
        max_tokens: Max output tokens
        profile: Router profile (auto/eco/premium/free)
    """
    if messages is None:
        messages = []

    # Smart routing
    resolved_model = _route_model(model, messages, profile)

    # Route based on provider
    if resolved_model.startswith(("openai/", "anthropic/", "google/", "x-ai/", "deepseek/", "meta-llama/", "~")):
        return _call_openrouter(resolved_model, messages, temperature, max_tokens)

    if resolved_model.startswith("gemini-"):
        return _call_gemini(resolved_model, messages, temperature, max_tokens)

    # Legacy GPT aliases → CodexSale
    if resolved_model in ("gpt-5.4", "gpt-5.4-mini", "gpt-5.5"):
        return _call_codexsale(resolved_model, messages, temperature, max_tokens, stream)

    # Unknown model — try OpenRouter as catch-all
    return _call_openrouter(resolved_model, messages, temperature, max_tokens)


def chat_completions(model: str, messages: list, temperature: float = 0.7, max_tokens: int = 1000, **kwargs):
    """
    OpenAI-compatible chat completions endpoint.
    Drop-in replacement for OpenAI API — same request/response shape.
    """
    return inference(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)


def _call_openrouter(model, messages, temperature, max_tokens):
    """Call OpenRouter for any model (400+ available)."""
    if not OPENROUTER_KEY:
        return {"error": "Inference backend not configured", "status": "error"}

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{OPENROUTER_BASE}/chat/completions",
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENROUTER_KEY}",
            },
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
        return {
            "error": f"Backend error: {e.code} {e.reason}",
            "details": error_body[:500],
            "status": "backend_error",
            "model": model,
        }
    except Exception as e:
        return {"error": str(e), "status": "error", "model": model}


def _call_gemini(model, messages, temperature, max_tokens):
    """Call Google Gemini API with OpenAI-format message conversion."""
    if not GEMINI_KEY:
        # Fallback to OpenRouter Gemini
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

    payload = {
        "contents": contents,
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
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
            "id": f"agentservices-gemini-{model}",
            "object": "chat.completion",
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "".join(text_parts)}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": result.get("usageMetadata", {}).get("promptTokenCount", 0),
                "completion_tokens": result.get("usageMetadata", {}).get("candidatesTokenCount", 0),
                "total_tokens": result.get("usageMetadata", {}).get("totalTokenCount", 0),
            },
            "provider": "AgentServices Inference Gateway (Google Gemini)",
            "model_requested": model,
            "x402_paid": True,
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}


def _call_codexsale(model, messages, temperature, max_tokens, stream):
    """Proxy to CodexSale (OpenAI-compatible) for legacy GPT model aliases."""
    if not CODEXSALE_KEY:
        # Fallback to OpenRouter
        return _call_openrouter(f"openai/{model}", messages, temperature, max_tokens)

    payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens, "stream": False}

    try:
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{CODEXSALE_BASE_URL}/chat/completions",
            data=req_data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {CODEXSALE_KEY}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
        result["provider"] = "AgentServices Inference Gateway"
        result["model_requested"] = model
        result["x402_paid"] = True
        return result
    except Exception as e:
        # Fallback to OpenRouter
        return _call_openrouter(f"openai/{model}", messages, temperature, max_tokens)


def quick_complete(prompt: str, model: str = "auto", max_tokens: int = 500):
    """Simple text completion — agent sends a prompt string, gets a response."""
    messages = [{"role": "user", "content": prompt}]
    return inference(model=model, messages=messages, max_tokens=max_tokens)
