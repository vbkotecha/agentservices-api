"""Diagnostic app v2 - show actual import errors."""
import os
import sys
import traceback
import json

print("[DIAG] Starting diagnostic v2...", flush=True)
print(f"[DIAG] __file__: {__file__}", flush=True)
print(f"[DIAG] cwd: {os.getcwd()}", flush=True)

# Add src dir to path
src_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, src_dir)
print(f"[DIAG] src_dir added to path: {src_dir}", flush=True)
print(f"[DIAG] sys.path: {sys.path[:5]}", flush=True)

# Check if files exist
print(f"[DIAG] crypto_data.py exists: {os.path.exists(os.path.join(src_dir, 'crypto_data.py'))}", flush=True)

errors = {}

# Try importing crypto_data with full error output
try:
    from crypto_data import get_price
    print("[DIAG] crypto_data: OK", flush=True)
    errors['crypto_data'] = 'OK'
except Exception as e:
    err_msg = f"{type(e).__name__}: {e}"
    errors['crypto_data'] = err_msg
    print(f"[DIAG] crypto_data: FAILED - {err_msg}", flush=True)
    traceback.print_exc()

# Try importing synthesis_data
try:
    from synthesis_data import get_token_risk
    print("[DIAG] synthesis_data: OK", flush=True)
    errors['synthesis_data'] = 'OK'
except Exception as e:
    err_msg = f"{type(e).__name__}: {e}"
    errors['synthesis_data'] = err_msg
    print(f"[DIAG] synthesis_data: FAILED - {err_msg}", flush=True)
    traceback.print_exc()

# Try main
try:
    from main import app as main_app
    print("[DIAG] main: OK", flush=True)
    errors['main'] = 'OK'
except Exception as e:
    err_msg = f"{type(e).__name__}: {e}"
    errors['main'] = err_msg
    print(f"[DIAG] main: FAILED - {err_msg}", flush=True)
    traceback.print_exc()

print(f"[DIAG] All errors: {json.dumps(errors)}", flush=True)

from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "OK", "mode": "diagnostic_v2", "errors": errors}

@app.get("/")
async def root():
    return {"status": "OK", "mode": "diagnostic_v2", "errors": errors, "src_dir": src_dir}
