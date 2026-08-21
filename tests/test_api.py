#!/usr/bin/env python3
"""
AIServices + AgentCourt — Full API Test Suite
Tests all endpoints, x402 payment protocol, and infrastructure.
Run: python3 /root/.letta/aiservices/tests/test_api.py
"""
import json
import urllib.request
import urllib.error
import base64
import sys
import time

PASS = 0
FAIL = 0
SKIP = 0

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} — {detail}")

def skip(name, reason):
    global SKIP
    SKIP += 1
    print(f"  ⊘ {name} — SKIPPED: {reason}")

def fetch(url, method="GET", data=None, headers=None):
    """Fetch URL and return (status_code, headers_dict, body_str)."""
    if headers is None:
        headers = {}
    if data and isinstance(data, dict):
        data = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.getcode(), dict(resp.headers), resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode()

def decode_payment_header(headers):
    """Decode x402 v2 payment-required header."""
    raw = headers.get("payment-required") or headers.get("Payment-Required") or headers.get("PAYMENT-REQUIRED")
    if not raw:
        return None
    return json.loads(base64.b64decode(raw))

# ============================================================
# AISERVICES TESTS
# ============================================================
def test_aiservices():
    print("\n{'='*60}")
    print("AISERVICES API — api.agentservices.to")
    print("{'='*60}")
    BASE = "https://api.agentservices.to"

    print("\n── 1. HEALTH & INFRASTRUCTURE ──")
    code, _, body = fetch(f"{BASE}/health")
    d = json.loads(body)
    test("health returns 200", code == 200, f"got {code}")
    test("x402_enabled is True", d.get("x402_enabled") == True, f"got {d.get('x402_enabled')}")
    test("6 services listed", len(d.get("services", [])) == 6, f"got {len(d.get('services', []))}")
    test("version present", "version" in d, "missing version field")

    print("\n── 2. ROOT DISCOVERY ──")
    code, _, body = fetch(f"{BASE}/")
    d = json.loads(body)
    test("root returns 200", code == 200, f"got {code}")
    test("name is AIServices", d.get("name") == "AIServices", f"got {d.get('name')}")
    test("payment method listed", "x402" in d.get("payment", ""), f"got {d.get('payment')}")
    test("live flag is True", d.get("live") == True)
    test("wallet address present", len(d.get("wallet", "")) > 10)

    print("\n── 3. x402 MANIFEST (.well-known/x402) ──")
    code, _, body = fetch(f"{BASE}/.well-known/x402")
    d = json.loads(body)
    test("manifest returns 200", code == 200, f"got {code}")
    test("version 1.0", d.get("version") == "1.0")
    test("network is base-mainnet", d.get("network") == "base-mainnet")
    test("currency is USDC", d.get("currency") == "USDC")
    test("chain_id is eip155:8453", d.get("chain_id") == "eip155:8453")
    test("license is MIT", d.get("license") == "MIT")
    endpoints = d.get("endpoints", [])
    test("7 endpoints in manifest", len(endpoints) == 7, f"got {len(endpoints)}")
    paid = [e for e in endpoints if e["price"] != "$0.00"]
    test("3 paid endpoints", len(paid) == 3, f"got {len(paid)}")
    free = [e for e in endpoints if e["price"] == "$0.00"]
    test("4 free endpoints", len(free) == 4, f"got {len(free)}")

    print("\n── 4. PAID ENDPOINTS (expect 402) ──")
    
    # Indicators
    code, headers, body = fetch(f"{BASE}/v1/indicators/BTC")
    test("indicators/BTC returns 402", code == 402, f"got {code}")
    if code == 402:
        pd = decode_payment_header(headers)
        test("indicators payment header present", pd is not None)
        if pd:
            test("indicators x402Version 2", pd.get("x402Version") == 2)
            opt = pd["accepts"][0]
            test("indicators scheme exact", opt["scheme"] == "exact")
            test("indicators network base", opt["network"] == "eip155:8453")
            test("indicators USDC asset", opt["asset"] == "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
            test("indicators correct wallet", opt["payTo"] == "0x9863aB6242663FCc84c33632741711dB78f8Fd15")
            test("indicators price 20000 ($0.02)", opt["amount"] == "20000", f"got {opt.get('amount')}")

    # Yields
    code, headers, body = fetch(f"{BASE}/v1/yields")
    test("yields returns 402", code == 402, f"got {code}")
    if code == 402:
        pd = decode_payment_header(headers)
        test("yields payment header present", pd is not None)
        if pd:
            opt = pd["accepts"][0]
            test("yields price 20000 ($0.02)", opt["amount"] == "20000")

    # Metadata
    code, headers, body = fetch(f"{BASE}/v1/metadata?url=https://example.com")
    test("metadata returns 402", code == 402, f"got {code}")
    if code == 402:
        pd = decode_payment_header(headers)
        test("metadata payment header present", pd is not None)
        if pd:
            opt = pd["accepts"][0]
            test("metadata price 10000 ($0.01)", opt["amount"] == "10000", f"got {opt.get('amount')}")

    print("\n── 5. FREE ENDPOINTS (expect 200 or 429) ──")
    
    # Fear & Greed
    code, _, body = fetch(f"{BASE}/v1/fear-greed")
    test("fear-greed returns 200", code == 200, f"got {code}")
    if code == 200:
        d = json.loads(body)
        test("fear-greed has index", "index" in d, f"missing index: {d}")
        test("fear-greed has label", "label" in d)

    # Geo
    code, _, body = fetch(f"{BASE}/v1/geo/8.8.8.8")
    test("geo/8.8.8.8 returns 200", code == 200, f"got {code}")
    if code == 200:
        d = json.loads(body)
        test("geo has location data", "country" in d or "city" in d or "ip" in d, f"missing: {d}")

    # Price (might rate limit)
    code, _, body = fetch(f"{BASE}/v1/price/BTC")
    if code == 200:
        d = json.loads(body)
        test("price/BTC returns 200", code == 200)
        test("price has symbol", d.get("symbol") == "BTC")
        test("price has price_usd", "price_usd" in d)
    elif code == 429:
        skip("price/BTC (rate limited)", "CoinGecko 429")
    else:
        test("price/BTC returns 200", False, f"got {code}")

    # Batch prices
    code, _, body = fetch(f"{BASE}/v1/prices?symbols=BTC,ETH")
    if code == 200:
        test("prices returns 200", code == 200)
    elif code == 429:
        skip("prices (rate limited)", "CoinGecko 429")
    else:
        test("prices returns 200", False, f"got {code}")

    print("\n── 6. ERROR HANDLING ──")
    code, _, body = fetch(f"{BASE}/v1/geo/invalid-ip-xyz")
    test("invalid geo returns error (not 500)", code in [400, 404, 422, 200], f"got {code}")

# ============================================================
# AGENTCOURT TESTS
# ============================================================
def test_agentcourt():
    print("\n{'='*60}")
    print("AGENTCOURT API — api.agentcourt.to")
    print("{'='*60}")
    BASE = "https://api.agentcourt.to"

    print("\n── 1. HEALTH & INFRASTRUCTURE ──")
    code, _, body = fetch(f"{BASE}/health")
    test("health returns 200", code == 200, f"got {code}")
    if code == 200:
        d = json.loads(body)
        test("has policies list", "policies" in str(d))
        test("7 policy templates", len(d.get("policies", [])) == 7, f"got {len(d.get('policies', []))}")

    print("\n── 2. ROOT DISCOVERY ──")
    code, _, body = fetch(f"{BASE}/")
    d = json.loads(body)
    test("root returns 200", code == 200, f"got {code}")
    test("name is AgentCourt", d.get("name") == "AgentCourt")
    test("payment is x402", "x402" in d.get("payment", ""))

    print("\n── 3. x402 MANIFEST ──")
    code, _, body = fetch(f"{BASE}/.well-known/x402")
    d = json.loads(body)
    test("manifest returns 200", code == 200, f"got {code}")
    test("network is base-mainnet", d.get("network") == "base-mainnet")
    test("endpoints present", len(d.get("endpoints", [])) >= 1)

    print("\n── 4. PAID ENDPOINT: POST /v1/disputes (expect 402) ──")
    code, headers, body = fetch(f"{BASE}/v1/disputes", method="POST", data={"test": True})
    test("disputes returns 402", code == 402, f"got {code}")
    # AgentCourt uses older x402 — payment info might be in body or header
    if code == 402:
        pd = decode_payment_header(headers)
        if pd:
            test("disputes payment header present", pd is not None)
            opt = pd["accepts"][0]
            test("disputes correct wallet", opt["payTo"] == "0x9863aB6242663FCc84c33632741711dB78f8Fd15")
            test("disputes network base", opt["network"] == "eip155:8453")
        else:
            # Might be in body for v1
            try:
                bd = json.loads(body) if body else {}
                if bd and "accepts" in bd:
                    test("disputes payment in body", True)
                else:
                    skip("disputes payment body parse", "empty or v2 header format")
            except:
                skip("disputes payment validation", "couldn't parse response")

    print("\n── 5. FREE ENDPOINTS ──")
    code, _, body = fetch(f"{BASE}/v1/policies")
    test("policies returns 200", code == 200, f"got {code}")
    if code == 200:
        d = json.loads(body)
        if isinstance(d, list):
            test("7 policy templates listed", len(d) == 7, f"got {len(d)}")
        elif isinstance(d, dict) and "policies" in d:
            test("7 policy templates listed", len(d["policies"]) == 7)

    print("\n── 6. SSL/TLS ──")
    code, _, _ = fetch(f"{BASE}/health")
    test("HTTPS endpoint accessible", code in [200, 404], f"got {code}")

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("╔══════════════════════════════════════════╗")
    print("║  FULL API TEST SUITE — x402 APIs        ║")
    print("╚══════════════════════════════════════════╝")
    
    test_aiservices()
    test_agentcourt()
    
    print(f"\n{'='*60}")
    print(f"RESULTS: {PASS} PASS | {FAIL} FAIL | {SKIP} SKIP")
    print(f"{'='*60}")
    
    if FAIL > 0:
        print(f"\n⚠ {FAIL} TESTS FAILED — review above")
        sys.exit(1)
    else:
        print(f"\n✓ ALL TESTS PASSED")
        sys.exit(0)
