"""Tests for California business entity status gov-as-API SKU."""
import base64
import importlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from x402.schemas.responses import SupportedKind, SupportedResponse

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

MOCK_ENTITY = {
    "EntityID": "202150010654",
    "EntityType": "Limited Liability Company - CA",
    "FilingDate": "2021-12-06T09:33:09.6",
    "StatusDescription": "Active",
    "EntityName": "Pure Moon LLC",
    "Jurisdiction": "CALIFORNIA",
    "AgentName": "Sierra Pearson",
    "AgentCity": "SACRAMENTO",
    "AgentState": "CA",
}


def _fresh_import(module_name: str):
    sys.path.insert(0, str(SRC))
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def _decode_payment_header(headers) -> dict:
    raw = headers.get("payment-required") or headers.get("Payment-Required")
    assert raw
    return json.loads(base64.b64decode(raw))


@pytest.fixture()
def client():
    for name in list(sys.modules):
        if name in ("main", "index", "gov_data", "x402_payment") or name.startswith("gov_data"):
            sys.modules.pop(name, None)

    auth_headers = {
        "verify": {"Authorization": "Bearer test"},
        "settle": {"Authorization": "Bearer test"},
        "supported": {"Authorization": "Bearer test"},
    }
    supported = SupportedResponse(
        kinds=[SupportedKind(x402_version=2, scheme="exact", network="eip155:8453")],
    )
    with patch("x402_payment.create_cdp_auth_headers", return_value=auth_headers), patch(
        "x402.http.facilitator_client.HTTPFacilitatorClient.get_supported",
        return_value=supported,
    ):
        from main import app

        yield TestClient(app)


def test_unpaid_get_returns_402(client):
    response = client.get("/v1/gov/us/ca/entity", params={"q": "1"})
    assert response.status_code == 402
    payload = _decode_payment_header(response.headers)
    assert payload.get("x402Version") == 2
    accepts = payload.get("accepts") or []
    base_option = next(item for item in accepts if item.get("network") == "eip155:8453")
    assert base_option.get("scheme") == "exact"
    assert base_option.get("amount") == "30000"


def test_handler_maps_mocked_sos_entity_details():
    gov_data = _fresh_import("gov_data")

    def fake_fetch(path, params):
        assert path == "BusinessEntityDetails"
        assert params["entity-number"] == "1"
        return MOCK_ENTITY

    with patch.object(gov_data, "CA_SOS_API_KEY", "test-key"), patch.object(gov_data, "_fetch_sos", side_effect=fake_fetch):
        result = gov_data.get_ca_entity_status("1")

    assert result["sku"] == "ca.entity.status"
    assert result["name"] == "Pure Moon LLC"
    assert result["entity_number"] == "202150010654"
    assert result["type"] == "Limited Liability Company - CA"
    assert result["status"] == "Active"
    assert result["jurisdiction"] == "CALIFORNIA"
    assert result["registered_agent"]["name"] == "Sierra Pearson"
    assert result["initial_filing_date"] == "2021-12-06"
    assert result["source"] == gov_data.CA_SOS_SOURCE
    assert "retrieved_at" in result
    assert "not legal or tax advice" in result["disclaimer"].lower()
    assert "Standing" not in json.dumps(result)
    assert "good standing" not in json.dumps(result).lower()


def test_handler_maps_mocked_sos_keyword_search():
    gov_data = _fresh_import("gov_data")

    def fake_fetch(path, params):
        assert path == "BusinessEntityKeywordSearch"
        assert params["search-term"] == "Pure Moon LLC"
        return {"RecordCount": 1, "EntityData": [MOCK_ENTITY]}

    with patch.object(gov_data, "CA_SOS_API_KEY", "test-key"), patch.object(gov_data, "_fetch_sos", side_effect=fake_fetch):
        result = gov_data.get_ca_entity_status("Pure Moon LLC")

    assert result["name"] == "Pure Moon LLC"
    assert result["entity_number"] == "202150010654"


def test_missing_api_key_returns_structured_503():
    gov_data = _fresh_import("gov_data")
    with patch.object(gov_data, "CA_SOS_API_KEY", ""):
        with pytest.raises(HTTPException) as exc:
            gov_data.get_ca_entity_status("1")
    assert exc.value.status_code == 503
    assert exc.value.detail["sku"] == "ca.entity.status"


def test_gov_data_import_survives_permission_error_on_root():
    original_exists = Path.exists

    def permission_exists(self):
        if self.as_posix().startswith("/root/.letta"):
            raise PermissionError(13, "Permission denied")
        return original_exists(self)

    for name in list(sys.modules):
        if name in ("main", "index", "gov_data", "letta_keys"):
            sys.modules.pop(name, None)

    env = {
        "VERCEL": "1",
        "CA_SOS_API_KEY": "",
    }
    with patch.dict(os.environ, env, clear=False), patch.object(Path, "exists", permission_exists):
        gov_data = _fresh_import("gov_data")
        assert gov_data.CA_SOS_API_KEY == ""
        index_module = importlib.import_module("index")
        response = TestClient(index_module.app).get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
