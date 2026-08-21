"""
Government / public registry data — California business entity lookups.
$0.03 per call via x402.

Data: California Secretary of State BE Public Search API (subscription key required).
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from fastapi import HTTPException
from letta_keys import load_key

CA_SOS_API_KEY = load_key("ca_sos.key", "CA_SOS_API_KEY")
CA_SOS_BASE = "https://calico.sos.ca.gov/cbc/v1/api"
CA_SOS_SOURCE = "California Secretary of State Business Entity Public Search API"
DISCLAIMER = "This information is sourced from public records and is not legal or tax advice."
SKU = "ca.entity.status"


def _is_entity_number(query: str) -> bool:
    q = query.strip()
    if re.fullmatch(r"\d+", q):
        return True
    return bool(re.fullmatch(r"[CBcb]\d+", q))


def _normalize_entity_number(query: str) -> str:
    q = query.strip()
    if re.fullmatch(r"[CBcb]\d+", q):
        return q[1:]
    return q


def _service_unavailable() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "error": "service_unavailable",
            "message": "California SOS API key is not configured. Set CA_SOS_API_KEY.",
            "sku": SKU,
        },
    )


def _fetch_sos(path: str, params: dict) -> dict | list:
    if not CA_SOS_API_KEY:
        raise _service_unavailable()

    query = urllib.parse.urlencode(params)
    url = f"{CA_SOS_BASE}/{path}?{query}" if query else f"{CA_SOS_BASE}/{path}"
    headers = {
        "User-Agent": "AgentServices/1.0",
        "Ocp-Apim-Subscription-Key": CA_SOS_API_KEY,
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code in (400, 404):
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "entity_not_found",
                    "message": "No matching California business entity was found.",
                    "sku": SKU,
                },
            ) from e
        if e.code == 503:
            raise _service_unavailable() from e
        raise HTTPException(
            status_code=502,
            detail={
                "error": "upstream_error",
                "message": f"California SOS API returned HTTP {e.code}.",
                "sku": SKU,
            },
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "upstream_error",
                "message": str(e),
                "sku": SKU,
            },
        ) from e


def _parse_filing_date(raw: str | None) -> str | None:
    if not raw:
        return None
    value = raw.strip()
    if "T" in value:
        return value.split("T", 1)[0]
    if " " in value:
        return value.split(" ", 1)[0]
    return value[:10] if len(value) >= 10 else value


def _map_entity(record: dict) -> dict:
    agent_name = (record.get("AgentName") or "").strip() or None
    return {
        "sku": SKU,
        "name": record.get("EntityName"),
        "entity_number": record.get("EntityID"),
        "type": record.get("EntityType"),
        "status": record.get("StatusDescription"),
        "jurisdiction": record.get("Jurisdiction"),
        "registered_agent": {
            "name": agent_name,
            "city": record.get("AgentCity"),
            "state": record.get("AgentState"),
        },
        "initial_filing_date": _parse_filing_date(record.get("FilingDate")),
        "source": CA_SOS_SOURCE,
        "retrieved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "disclaimer": DISCLAIMER,
    }


def _lookup_by_entity_number(entity_number: str) -> dict:
    record = _fetch_sos("BusinessEntityDetails", {"entity-number": entity_number})
    if not isinstance(record, dict) or not record.get("EntityID"):
        raise HTTPException(
            status_code=404,
            detail={
                "error": "entity_not_found",
                "message": "No matching California business entity was found.",
                "sku": SKU,
            },
        )
    return _map_entity(record)


def _lookup_by_keyword(search_term: str) -> dict:
    payload = _fetch_sos("BusinessEntityKeywordSearch", {"search-term": search_term})
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=404,
            detail={
                "error": "entity_not_found",
                "message": "No matching California business entity was found.",
                "sku": SKU,
            },
        )

    entities = payload.get("EntityData") or []
    if not entities:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "entity_not_found",
                "message": "No matching California business entity was found.",
                "sku": SKU,
            },
        )

    normalized = search_term.strip().casefold()
    for record in entities:
        name = (record.get("EntityName") or "").strip().casefold()
        if name == normalized:
            return _map_entity(record)
    return _map_entity(entities[0])


def get_ca_entity_status(query: str) -> dict:
    """Look up a California business entity by name or entity number."""
    q = (query or "").strip()
    if not q:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_query",
                "message": "Query parameter q is required.",
                "sku": SKU,
            },
        )

    if _is_entity_number(q):
        return _lookup_by_entity_number(_normalize_entity_number(q))
    return _lookup_by_keyword(q)
