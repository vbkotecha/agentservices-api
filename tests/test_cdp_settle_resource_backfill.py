"""CDP /settle paymentPayload.resource backfill for Bazaar indexing."""
import importlib
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))


def _load_main_helpers():
    for name in list(sys.modules):
        if name in ("main", "index", "x402_payment") or name.startswith(
            ("crypto_data", "agent_memory", "geo_data", "web_data")
        ):
            sys.modules.pop(name, None)

    env = {
        "VERCEL": "1",
        "CDP_API_KEY_ID": "",
        "CDP_API_KEY_SECRET": "",
    }
    with patch.dict(os.environ, env, clear=False):
        main = importlib.import_module("main")
    return main


def test_backfill_adds_resource_and_bazaar_when_buyer_omits_them():
    main = _load_main_helpers()
    payload = {
        "x402Version": 2,
        "payload": {"signature": "0xabc"},
        "accepted": {"scheme": "exact", "network": "eip155:8453"},
    }

    backfilled = main._backfill_settle_payment_payload(
        payload,
        "https://api.agentservices.to/v1/fx",
        "Real-time FX/forex rates for 30+ currencies",
    )

    assert backfilled["resource"]["url"] == "https://api.agentservices.to/v1/fx"
    assert backfilled["resource"]["serviceName"] == "AgentServices"
    assert "data" in backfilled["resource"]["tags"]
    assert backfilled["extensions"]["bazaar"]["name"] == "AgentServices"
    assert backfilled["extensions"]["bazaar"]["info"]["routeTemplate"] == "/v1/fx"


def test_backfill_preserves_existing_resource_url():
    main = _load_main_helpers()
    payload = {
        "resource": {"url": "https://api.agentservices.to/v1/fx?base=USD"},
        "extensions": {},
    }

    backfilled = main._backfill_settle_payment_payload(
        payload,
        "https://api.agentservices.to/v1/fx",
    )

    assert backfilled["resource"]["url"] == "https://api.agentservices.to/v1/fx?base=USD"
    assert backfilled["extensions"]["bazaar"]["info"]["routeTemplate"] == "/v1/fx"


def test_backfill_trims_long_resource_description():
    main = _load_main_helpers()
    payload = {"resource": {"url": "https://api.agentservices.to/v1/fx", "description": "x" * 600}}

    backfilled = main._backfill_settle_payment_payload(
        payload,
        "https://api.agentservices.to/v1/fx",
    )

    assert len(backfilled["resource"]["description"]) == main._CDP_RESOURCE_DESCRIPTION_MAX_LEN


def test_cdp_settle_client_keeps_resource_and_extensions():
    main = _load_main_helpers()
    client_cls = None
    for cell in main.__dict__.values():
        if getattr(cell, "__name__", None) == "CDPFixedFacilitatorClient":
            client_cls = cell
            break
    assert client_cls is not None

    captured = {}

    async def fake_super_settle(self, payment_payload, payment_requirements):
        captured["payload"] = (
            payment_payload.model_dump(by_alias=True, exclude_none=True)
            if hasattr(payment_payload, "model_dump")
            else dict(payment_payload)
        )
        return MagicMock()

    from x402.schemas import PaymentPayload, PaymentRequirements, ResourceInfo

    payload = PaymentPayload(
        x402_version=2,
        payload={"signature": "0xabc"},
        accepted=PaymentRequirements(
            scheme="exact",
            network="eip155:8453",
            asset="0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
            amount="3000",
            pay_to="0x1234567890123456789012345678901234567890",
            max_timeout_seconds=300,
        ),
        resource=ResourceInfo(url="https://api.agentservices.to/v1/fx"),
        extensions={"bazaar": {"name": "AgentServices"}},
    )

    client = client_cls(MagicMock())
    with patch.object(client_cls.__bases__[0], "settle", fake_super_settle):
        import asyncio

        asyncio.run(client.settle(payload, payload.accepted))

    assert captured["payload"]["resource"]["url"] == "https://api.agentservices.to/v1/fx"
    assert captured["payload"]["extensions"]["bazaar"]["name"] == "AgentServices"


def test_apply_settle_resource_backfill_uses_transport_url():
    main = _load_main_helpers()
    from x402.schemas import PaymentPayload, PaymentRequirements

    payload = PaymentPayload(
        x402_version=2,
        payload={"signature": "0xabc"},
        accepted=PaymentRequirements(
            scheme="exact",
            network="eip155:8453",
            asset="0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
            amount="3000",
            pay_to="0x1234567890123456789012345678901234567890",
            max_timeout_seconds=300,
        ),
    )

    adapter = MagicMock()
    adapter.get_url.return_value = "https://api.agentservices.to/v1/fx"
    request = MagicMock(adapter=adapter)
    transport = MagicMock(request=request)
    context = MagicMock(payment_payload=payload, transport_context=transport)

    main._apply_settle_resource_backfill(context)

    assert payload.resource is not None
    assert payload.resource.url == "https://api.agentservices.to/v1/fx"
    assert payload.extensions["bazaar"]["info"]["routeTemplate"] == "/v1/fx"
