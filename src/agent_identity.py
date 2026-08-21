"""Agent identity, reputation, and evidence receipt primitives.

The wire shapes intentionally follow ERC-8004 concepts (agent registration,
feedback, reputation and verification) without pretending to perform an
on-chain transaction. Each response carries a deterministic receipt hash so a
caller can anchor it to ERC-8004 or another registry later.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

STORE = Path(os.environ.get("AGENTSERVICES_IDENTITY_STORE", "/tmp/agentservices-identity"))


def _read(name: str, default: Any) -> Any:
    path = STORE / name
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def _write(name: str, value: Any) -> None:
    STORE.mkdir(parents=True, exist_ok=True)
    path = STORE / name
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")))
    tmp.replace(path)


def _receipt(kind: str, payload: Any) -> str:
    body = json.dumps({"kind": kind, "payload": payload}, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(body.encode()).hexdigest()


def register_agent(wallet: str, name: str, endpoint: str = "", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    if not wallet or not name:
        raise ValueError("wallet and name are required")
    agents = _read("agents.json", {})
    agent_id = "agent_" + uuid.uuid4().hex
    now = int(time.time())
    agent = {"agent_id": agent_id, "name": name, "wallet": wallet, "endpoint": endpoint,
             "metadata": metadata or {}, "created_at": now, "updated_at": now,
             "registry": "agentservices", "erc8004_compatible": True}
    agents[agent_id] = agent
    _write("agents.json", agents)
    return {**agent, "receipt": _receipt("agent.register", agent)}


def get_agent(agent_id: str) -> dict[str, Any] | None:
    return _read("agents.json", {}).get(agent_id)


def add_feedback(agent_id: str, score: int, comment: str = "", job_id: str = "", evaluator: str = "") -> dict[str, Any]:
    if not get_agent(agent_id):
        raise KeyError("agent not found")
    if not 0 <= score <= 100:
        raise ValueError("score must be between 0 and 100")
    feedback = _read("feedback.json", [])
    item = {"feedback_id": "fb_" + uuid.uuid4().hex, "agent_id": agent_id, "score": score,
            "comment": comment, "job_id": job_id, "evaluator": evaluator, "created_at": int(time.time())}
    item["signed_feedback"] = _receipt("feedback", item)
    feedback.append(item)
    _write("feedback.json", feedback)
    return item


def reputation(agent_id: str) -> dict[str, Any]:
    rows = [x for x in _read("feedback.json", []) if x.get("agent_id") == agent_id]
    if not get_agent(agent_id):
        raise KeyError("agent not found")
    scores = [x["score"] for x in rows]
    result = {"agent_id": agent_id, "feedback_count": len(rows),
              "reputation_score": round(sum(scores) / len(scores), 2) if scores else None,
              "completed_jobs": len({x["job_id"] for x in rows if x.get("job_id")}),
              "feedback": rows}
    return {**result, "receipt": _receipt("reputation", result)}


def verify_agent(agent_id: str, challenge: str = "") -> dict[str, Any]:
    agent = get_agent(agent_id)
    if not agent:
        raise KeyError("agent not found")
    payload = {"agent_id": agent_id, "wallet": agent["wallet"], "challenge": challenge,
               "verified_at": int(time.time())}
    return {"agent_id": agent_id, "verified": True, "method": "registry-record",
            "challenge": challenge, "wallet": agent["wallet"], "receipt": _receipt("agent.verify", payload)}


def snapshot(agent_id: str, subject: str, data: Any, source: str = "") -> dict[str, Any]:
    if not subject:
        raise ValueError("subject is required")
    payload = {"agent_id": agent_id, "subject": subject, "data": data, "source": source,
               "created_at": int(time.time())}
    result = {"evidence_id": "ev_" + uuid.uuid4().hex, **payload,
              "content_hash": _receipt("evidence.snapshot", payload)}
    receipts = _read("evidence.json", [])
    receipts.append(result)
    _write("evidence.json", receipts)
    return result


def verify_evidence(evidence_id: str) -> dict[str, Any]:
    row = next((x for x in _read("evidence.json", []) if x.get("evidence_id") == evidence_id), None)
    if not row:
        raise KeyError("evidence not found")
    payload = {k: row[k] for k in ("agent_id", "subject", "data", "source", "created_at")}
    valid = _receipt("evidence.snapshot", payload) == row.get("content_hash")
    return {"evidence_id": evidence_id, "valid": valid, "content_hash": row.get("content_hash"),
            "receipt": _receipt("evidence.verify", {"evidence_id": evidence_id, "valid": valid})}


def check_claims(evidence_ids: list[str]) -> dict[str, Any]:
    results = []
    for evidence_id in evidence_ids:
        try:
            results.append(verify_evidence(evidence_id))
        except KeyError:
            results.append({"evidence_id": evidence_id, "valid": False, "error": "evidence not found"})
    result = {"claims": results, "valid": bool(results) and all(x.get("valid") for x in results)}
    return {**result, "receipt": _receipt("evidence.claims", result)}
