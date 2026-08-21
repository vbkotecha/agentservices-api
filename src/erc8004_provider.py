"""ERC-8004 read adapter backed by the QuantuLabs indexer."""
from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


class _HTTP:
    @staticmethod
    def get(url: str, params=None, headers=None, timeout=15):
        if params:
            url += "?" + urlencode(params)
        request = Request(url, headers=headers or {}, method="GET")
        try:
            response = urlopen(request, timeout=timeout)
            status, body = response.status, response.read().decode()
        except HTTPError as error:
            status, body = error.code, error.read().decode()

        class Response:
            status_code = status
            text = body
            def json(self):
                return json.loads(self.text)
        return Response()

    @staticmethod
    def post(url: str, payload: dict[str, Any], headers=None, timeout=15):
        request = Request(url, data=json.dumps(payload).encode(),
                          headers={"content-type": "application/json", **(headers or {})}, method="POST")
        try:
            response = urlopen(request, timeout=timeout)
            status, body = response.status, response.read().decode()
        except HTTPError as error:
            status, body = error.code, error.read().decode()

        class Response:
            status_code = status
            text = body
            def json(self):
                return json.loads(self.text)
        return Response()


requests = _HTTP()
# QuantuLabs' public ERC-8004 GraphQL indexer. QuickNode is blocked from Railway
# by Cloudflare Error 1010, so it must only be selected explicitly.
BASE_URL = os.environ.get("ERC8004_PROVIDER_BASE_URL", "https://8004-indexer-main.qnt.sh/v2/graphql")
TIMEOUT = float(os.environ.get("ERC8004_PROVIDER_TIMEOUT", "15"))


def _error(status: int, detail: Any) -> RuntimeError:
    error = RuntimeError(f"ERC-8004 provider returned HTTP {status}")
    setattr(error, "status_code", status)
    setattr(error, "detail", detail)
    return error


def _graphql(query: str, variables: dict[str, Any] | None = None) -> Any:
    response = requests.post(BASE_URL, {"query": query, "variables": variables or {}}, timeout=TIMEOUT)
    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text[:1000]
        raise _error(response.status_code, detail)
    payload = response.json()
    if payload.get("errors"):
        raise _error(502, {"errors": payload["errors"]})
    return payload.get("data", {})


def _agent_filter(agent_id: str) -> str:
    # Numeric IDs are the ERC-8004 agentId. Entity IDs are accepted too.
    if agent_id.isdigit():
        return f'agentId: "{agent_id}"'
    escaped = agent_id.replace('"', '\\"')
    return f'id: "{escaped}"'


def agents(limit: int = 25, offset: int = 0, chain_id: int | None = None, payment: str = "") -> Any:
    # The deployed schema does not expose chainId in AgentFilter. Fetch the
    # requested window and apply the chain constraint without inventing a filter.
    rows = _graphql(f'''{{ agents(first: {limit}, skip: {offset}) {{
        id chainId agentId agentURI owner agentWallet totalFeedback
    }} }}''').get("agents", [])
    if chain_id is not None:
        rows = [row for row in rows if row.get("chainId") == chain_id]
    return {"agents": rows, "limit": limit, "offset": offset, "provider": "qnt"}


def agent(agent_id: str, payment: str = "") -> Any:
    where = _agent_filter(agent_id)
    rows = _graphql(f'''{{ agents(first: 1, where: {{{where}}}) {{
        id chainId agentId agentURI owner agentWallet totalFeedback
        registrationFile {{ name description image active x402Support mcpEndpoint mcpTools a2aEndpoint a2aSkills oasfSkills oasfDomains hasOASF supportedTrusts }}
        stats {{ id totalFeedback averageFeedbackValue lastActivity }}
    }} }}''').get("agents", [])
    if not rows:
        return {"agent": None}
    return rows[0]


def _resolve_agent(agent_id: str) -> dict[str, Any] | None:
    result = agent(agent_id)
    return result if result.get("id") else None


def reputation(agent_id: str, payment: str = "") -> Any:
    resolved = _resolve_agent(agent_id)
    if not resolved:
        return {"reputation": None}
    entity_id = resolved["id"]
    result = _graphql(f'''{{ agentReputation(asset: "{entity_id}") {{
        asset owner collection nftName agentUri feedbackCount avgScore positiveCount negativeCount validationCount
    }} }}''').get("agentReputation")
    return {"reputation": result, "agent": resolved}


def feedback(agent_id: str, limit: int = 25, offset: int = 0, payment: str = "") -> Any:
    resolved = _resolve_agent(agent_id)
    if not resolved:
        return {"feedback": [], "limit": limit, "offset": offset}
    entity_id = resolved["id"]
    rows = _graphql(f'''{{ feedbacks(first: {limit}, skip: {offset}, where: {{agent: "{entity_id}"}}) {{
        id agent {{ id chainId agentId }} clientAddress feedbackIndex value tag1 tag2 endpoint feedbackURI isRevoked createdAt
        responses {{ id responder responseUri createdAt }}
    }} }}''').get("feedbacks", [])
    return {"feedback": rows, "limit": limit, "offset": offset}


def validations(agent_id: str, limit: int = 25, offset: int = 0, payment: str = "") -> Any:
    # QuantuLabs exposes validationCount in AgentReputation but no validation
    # collection. Return the indexed count rather than pretending feedback is validation.
    reputation_data = reputation(agent_id, payment).get("reputation")
    return {"validations": [], "validationCount": (reputation_data or {}).get("validationCount", 0),
            "limit": limit, "offset": offset}


def provider_info() -> dict[str, str]:
    return {"provider": "quantalabs-erc8004-indexer", "base_url": BASE_URL,
            "source": "QuantuLabs ERC-8004 GraphQL registry/indexer",
            "payment": "provider x402 passthrough"}
