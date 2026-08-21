"""Keep Bazaar market-pulse discovery aligned with its real result envelope."""

import ast
from pathlib import Path


MAIN_PATH = Path(__file__).resolve().parents[1] / "src" / "main.py"


def _discovery_entry() -> dict:
    tree = ast.parse(MAIN_PATH.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "_BAZAAR_ENDPOINT_INFO"
            for target in node.targets
        ):
            return ast.literal_eval(node.value)["/v1/market-pulse"]
    raise AssertionError("_BAZAAR_ENDPOINT_INFO was not found")


def test_market_pulse_discovery_example_matches_result_envelope():
    example = _discovery_entry()["output_example"]

    assert set(example) == {
        "research_type", "modules", "errors", "timestamp", "synthesis", "pricing_advantage",
    }
    assert set(example["modules"]["sentiment"]) == {
        "fear_greed_value", "fear_greed_label", "interpretation",
    }
    assert set(example["synthesis"]) == {
        "market_direction", "sentiment_score", "data_modules_active", "modules_available",
    }
