"""
Voice Gateway — Phone numbers and AI voice calls via Twilio.
Phone numbers: $5 per 30-day lease (80% margin, Twilio costs ~$1)
Voice calls: $0.54 per call (75% margin, Twilio costs ~$0.10/min)
"""
import urllib.request
import json
import base64

from letta_keys import load_twilio_config

TWILIO_CONFIG = load_twilio_config()

TWILIO_SID = TWILIO_CONFIG.get("account_sid", "")
TWILIO_TOKEN = TWILIO_CONFIG.get("auth_token", "")
TWILIO_PHONE = TWILIO_CONFIG.get("phone_number", "")
TWILIO_BASE = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}"


def _twilio_request(endpoint, method="GET", post_data=None):
    """Make an authenticated Twilio API request."""
    if not TWILIO_SID or not TWILIO_TOKEN:
        return {"error": "Twilio not configured", "status": "error"}

    auth = base64.b64encode(f"{TWILIO_SID}:{TWILIO_TOKEN}".encode()).decode()
    url = f"{TWILIO_BASE}/{endpoint}"

    headers = {
        "Authorization": f"Basic {auth}",
    }

    if method == "POST":
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urllib.parse.urlencode(post_data or {}).encode()
    else:
        data = None

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"Twilio error {e.code}", "details": e.read().decode()[:300], "status": "error"}
    except Exception as e:
        return {"error": str(e), "status": "error"}


def get_phone_number():
    """Get our current Twilio phone number info."""
    if not TWILIO_PHONE:
        return {"error": "No phone number configured", "status": "error"}
    return {
        "phone_number": TWILIO_PHONE,
        "account_sid": TWILIO_SID[:20] + "...",
        "provider": "AgentServices Voice Gateway",
        "lease_type": "30-day",
        "capabilities": ["voice", "sms"],
    }


def make_call(to_number: str, message: str = "", voice_url: str = ""):
    """
    Make an AI voice call to a phone number.
    Cost: $0.54 per call via x402 (Twilio costs ~$0.10/min).
    """
    if not TWILIO_PHONE:
        return {"error": "No outbound number configured", "status": "error"}

    # If message provided, use TwiML to speak it
    if message and not voice_url:
        # Use Twilio's TwiML Bin or a hosted URL
        import urllib.parse
        twiml = f'<Response><Say>{message}</Say></Response>'
        # For now, just initiate the call
        post_data = {
            "To": to_number,
            "From": TWILIO_PHONE,
            "Twiml": twiml,
        }
    elif voice_url:
        post_data = {
            "To": to_number,
            "From": TWILIO_PHONE,
            "Url": voice_url,
        }
    else:
        return {"error": "Either message or voice_url required", "status": "error"}

    result = _twilio_request("Calls.json", method="POST", post_data=post_data)

    if "error" not in result:
        return {
            "status": "call_initiated",
            "to": to_number,
            "from": TWILIO_PHONE,
            "call_sid": result.get("sid", ""),
            "provider": "AgentServices Voice Gateway",
        }
    return result


def lookup_number(phone_number: str):
    """
    Look up phone number information (carrier, type, fraud risk).
    Cost: $0.05 per lookup via x402.
    """
    # Use Twilio Lookup API
    auth = base64.b64encode(f"{TWILIO_SID}:{TWILIO_TOKEN}".encode()).decode()
    url = f"https://lookups.twilio.com/v1/PhoneNumbers/{phone_number}?Type=carrier&Type=caller-name"

    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return {
                "phone_number": data.get("phone_number", phone_number),
                "national_format": data.get("national_format", ""),
                "country_code": data.get("country_code", ""),
                "carrier": data.get("carrier", {}),
                "caller_name": data.get("caller_name", {}),
                "provider": "AgentServices Voice Gateway",
            }
    except urllib.error.HTTPError as e:
        return {"error": f"Lookup error {e.code}", "status": "error"}
    except Exception as e:
        return {"error": str(e), "status": "error"}


import urllib.parse  # needed for urlencode and quote
