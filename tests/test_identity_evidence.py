import importlib


def module(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTSERVICES_IDENTITY_STORE", str(tmp_path))
    import src.agent_identity as identity
    return importlib.reload(identity)


def test_registration_retrieval_and_verification(tmp_path, monkeypatch):
    m = module(tmp_path, monkeypatch)
    agent = m.register_agent("0xabc", "Researcher", "https://example.test")
    assert agent["erc8004_compatible"] is True
    assert m.get_agent(agent["agent_id"])["name"] == "Researcher"
    verified = m.verify_agent(agent["agent_id"], "nonce-1")
    assert verified["verified"] is True
    assert verified["challenge"] == "nonce-1"
    assert verified["receipt"].startswith("sha256:")


def test_feedback_reputation_and_bounds(tmp_path, monkeypatch):
    m = module(tmp_path, monkeypatch)
    agent = m.register_agent("0xabc", "Worker")
    m.add_feedback(agent["agent_id"], 80, job_id="job-1")
    m.add_feedback(agent["agent_id"], 100, job_id="job-2")
    result = m.reputation(agent["agent_id"])
    assert result["reputation_score"] == 90
    assert result["completed_jobs"] == 2
    try:
        m.add_feedback(agent["agent_id"], 101)
        assert False
    except ValueError:
        pass


def test_evidence_round_trip_and_claims(tmp_path, monkeypatch):
    m = module(tmp_path, monkeypatch)
    evidence = m.snapshot("agent-x", "job outcome", {"status": "complete"}, "https://source")
    verified = m.verify_evidence(evidence["evidence_id"])
    assert verified["valid"] is True
    claims = m.check_claims([evidence["evidence_id"], "ev_missing"])
    assert claims["valid"] is False
    assert claims["claims"][0]["valid"] is True
    assert claims["claims"][1]["valid"] is False


def test_missing_records_raise(tmp_path, monkeypatch):
    m = module(tmp_path, monkeypatch)
    for fn, args in ((m.verify_agent, ("missing",)), (m.reputation, ("missing",)),
                     (m.verify_evidence, ("missing",))):
        try:
            fn(*args)
            assert False
        except KeyError:
            pass
