"""
Startup checker — tries to import the app, prints detailed errors,
then starts uvicorn if successful.
"""
import sys
import os
import traceback
import json

print("=" * 60, flush=True)
print("[STARTUP] Beginning startup check", flush=True)
print(f"[STARTUP] Python: {sys.version}", flush=True)
print(f"[STARTUP] CWD: {os.getcwd()}", flush=True)
print(f"[STARTUP] sys.path: {sys.path[:5]}", flush=True)
print(f"[STARTUP] Files in /app/src: {os.listdir('/app/src')[:10]}", flush=True)
print("=" * 60, flush=True)

# Check each module
modules_to_check = [
    ("crypto_data", "get_price"),
    ("geo_data", "get_ip_geo"),
    ("web_data", "get_url_metadata"),
    ("search_data", "web_search"),
    ("dex_data", "get_swap_quote"),
    ("prediction_data", "get_polymarket_markets"),
    ("news_data", "get_crypto_news"),
    ("marketing_data", "analyze_sentiment"),
    ("onchain_data", "get_whales"),
    ("synthesis_data", "get_token_risk"),
    ("inference_gateway", "inference"),
    ("tradfi_data", "get_stock_quote"),
    ("utility_data", "extract_web_content"),
    ("agent_memory", "store"),
    ("skill_packs", "available_skills"),
    ("media_gateway", "generate_image"),
    ("voice_gateway", "get_phone_number"),
    ("mcp_endpoint", "router"),
]

sys.path.insert(0, "/app/src")

_module_results = {}
all_ok = True
for mod_name, attr_name in modules_to_check:
    try:
        mod = __import__(mod_name)
        if hasattr(mod, attr_name):
            print(f"[CHECK] {mod_name}: OK", flush=True)
            _module_results[mod_name] = "OK"
        else:
            print(f"[CHECK] {mod_name}: IMPORTED but missing attr '{attr_name}'", flush=True)
            _module_results[mod_name] = f"IMPORTED but missing attr '{attr_name}'"
            all_ok = False
    except Exception as e:
        err_str = f"{type(e).__name__}: {e}"
        print(f"[CHECK] {mod_name}: FAILED — {err_str}", flush=True)
        traceback.print_exc()
        _module_results[mod_name] = err_str
        all_ok = False

# Try importing engine.policy_engine
try:
    from engine.policy_engine import evaluate_dispute, list_policies
    print("[CHECK] engine.policy_engine: OK", flush=True)
    _module_results["engine.policy_engine"] = "OK"
except Exception as e:
    err_str = f"{type(e).__name__}: {e}"
    print(f"[CHECK] engine.policy_engine: FAILED — {err_str}", flush=True)
    traceback.print_exc()
    _module_results["engine.policy_engine"] = err_str
    all_ok = False

# Now try importing main app
print("\n[STARTUP] Attempting to import main app...", flush=True)
_main_error = None
try:
    from main import app
    print("[STARTUP] main.app import: SUCCESS", flush=True)
except Exception as e:
    _main_error = f"{type(e).__name__}: {e}"
    print(f"[STARTUP] main.app import: FAILED — {_main_error}", flush=True)
    traceback.print_exc()
    all_ok = False

if not all_ok:
    print("\n[STARTUP] ERRORS DETECTED — starting diagnostic server", flush=True)
    from fastapi import FastAPI
    app = FastAPI(title="AgentServices (diagnostic)")

    @app.get("/health")
    async def health():
        return {"status": "DEGRADED", "message": "Some modules failed to import", "check": "/diagnostics for details"}

    @app.get("/")
    async def root():
        return {"status": "DEGRADED", "message": "Diagnostic mode — check /diagnostics", "modules_checked": len(_module_results), "ok": sum(1 for v in _module_results.values() if v == "OK")}

    @app.get("/diagnostics")
    async def diagnostics():
        return {
            "status": "DEGRADED",
            "modules": _module_results,
            "main_import_error": _main_error,
            "python": sys.version,
            "cwd": os.getcwd(),
            "files_in_src": os.listdir('/app/src'),
        }

# Start uvicorn
print(f"\n[STARTUP] Starting uvicorn on port {os.environ.get('PORT', '8000')}...", flush=True)
import uvicorn
port = int(os.environ.get("PORT", 8000))
uvicorn.run(app, host="0.0.0.0", port=port)
