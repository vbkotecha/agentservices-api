"""Regression checks for the public research-brief buyer contract."""
from pathlib import Path

CONTRACT = (Path(__file__).resolve().parents[1] / "docs" / "research-brief-outcome-contract.md").read_text()


def test_contract_names_live_endpoint_and_inputs():
    assert "https://api.agentservices.to/v1/research?q=<research-question>&sources=3" in CONTRACT
    assert "`sources`" in CONTRACT
    assert "caps it at `5`" in CONTRACT


def test_contract_discloses_partial_and_no_result_behavior():
    assert "`extraction_status`" in CONTRACT
    assert '"status": "no_results"' in CONTRACT
    assert "not a market prediction" in CONTRACT


def test_contract_distinguishes_fulfillment_from_settlement():
    assert "not proof of settlement" in CONTRACT
    assert "Buyer-retained payment evidence" in CONTRACT
