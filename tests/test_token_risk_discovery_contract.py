"""Keep Bazaar token-risk discovery aligned with the implemented outcome schema."""

import ast
from pathlib import Path


MAIN_PATH = Path(__file__).resolve().parents[1] / "src" / "main.py"


def _discovery_entry() -> dict:
    tree = ast.parse(MAIN_PATH.read_text())
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == "_BAZAAR_ENDPOINT_INFO" for target in node.targets):
            entries = ast.literal_eval(node.value)
            return entries["/v1/token-risk"]
    raise AssertionError("_BAZAAR_ENDPOINT_INFO was not found")


def test_token_risk_discovery_example_matches_the_outcome_contract():
    entry = _discovery_entry()
    example = entry["output_example"]

    assert entry["route"] == "/v1/token-risk/:token"
    assert entry["path_params"]["token"] == "bitcoin"
    assert set(example) == {
        "token", "risk_score", "risk_label", "dimensions", "market_data",
        "momentum", "recommendation", "timestamp",
    }
    assert set(example["dimensions"]) == {"volatility", "market_cap_risk", "liquidity_risk"}
    assert set(example["market_data"]) == {
        "price_usd", "change_24h_pct", "volume_24h_usd", "market_cap_usd",
    }
