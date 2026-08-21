#!/usr/bin/env python3
"""
AgentServices activation funnel probe.

Checks each stage of the activation funnel against the live API:
  1. Discovery: API health check
  2. Free use: GET /v1/prices returns 200
  3. Payment challenge: GET /v1/indicators/BTC returns 402
  4. Activation: (manual) — requires an external wallet to pay

Usage:
  python3 examples/check_activation_funnel.py

Exit code 0 if stages 1-3 pass; exit code 1 if any fail.
This script does NOT spend funds. Stage 4 is informational only.
"""

import sys
import urllib.request
import urllib.error
import json

BASE = "https://api.agentservices.to"

def check(name, url, expected_status):
    """Check a URL and report whether it returned the expected status."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
    except Exception as e:
        print(f"  FAIL  {name}: {e}")
        return False

    if status == expected_status:
        print(f"  OK    {name}: HTTP {status}")
        return True
    else:
        print(f"  FAIL  {name}: expected HTTP {expected_status}, got {status}")
        return False

def main():
    print("=== AgentServices Activation Funnel Probe ===\n")

    all_pass = True

    print("Stage 1 — Discovery (health check)")
    all_pass &= check("GET /health", f"{BASE}/health", 200)
    print()

    print("Stage 2 — Free use (price endpoint)")
    all_pass &= check("GET /v1/prices?symbols=BTC", f"{BASE}/v1/prices?symbols=BTC", 200)
    print()

    print("Stage 3 — Payment challenge (paid endpoint returns 402)")
    all_pass &= check("GET /v1/indicators/BTC", f"{BASE}/v1/indicators/BTC", 402)
    print()

    print("Stage 4 — Activation (external paid settlement)")
    print("  SKIP  Requires an external x402-compatible wallet to pay and retry.")
    print("  Measure: unique payer wallet addresses from facilitator settlement logs.")
    print()

    print("Stage 5 — Retention (repeat paid call within 7 days)")
    print("  SKIP  Requires multiple paid settlements from the same wallet.")
    print()

    if all_pass:
        print("Stages 1-3 pass. The funnel is open but no external activation is recorded.")
        sys.exit(0)
    else:
        print("One or more stages failed. The funnel is blocked.")
        sys.exit(1)

if __name__ == "__main__":
    main()
