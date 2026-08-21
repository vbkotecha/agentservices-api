import importlib


def test_provider_adapter_queries_graphql(monkeypatch):
    import src.erc8004_provider as p
    calls = []
    def fake_post(url, payload, headers=None, timeout=None):
        calls.append((url, payload, headers, timeout))
        class Response:
            status_code = 200
            def json(self):
                return {"data": {"agents": [{"agentId": "7", "chainId": 8453}]}}
        return Response()
    monkeypatch.setattr(p.requests, "post", fake_post)
    assert p.agents(limit=2, chain_id=8453, payment="signed")["agents"] == [{"agentId": "7", "chainId": 8453}]
    assert calls[0][0].endswith("/v2/graphql")
    assert "first: 2" in calls[0][1]["query"]


def test_provider_errors_preserve_status_and_detail(monkeypatch):
    import src.erc8004_provider as p
    def fake_post(*args, **kwargs):
        class Response:
            status_code = 402
            text = "payment required"
            def json(self): return {"accepts": [{"maxAmountRequired": "1000"}]}
        return Response()
    monkeypatch.setattr(p.requests, "post", fake_post)
    try:
        p.agents()
        assert False
    except RuntimeError as exc:
        assert exc.status_code == 402
        assert exc.detail["accepts"][0]["maxAmountRequired"] == "1000"
