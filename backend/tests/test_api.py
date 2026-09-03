"""
End-to-end API tests. Run with:  ./venv/bin/pytest -v
Uses FastAPI's TestClient, which exercises the real ASGI app in-process
(same code path as uvicorn) without needing a live server.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_roles_and_login():
    r = client.get("/api/auth/roles")
    assert r.status_code == 200
    keys = [x["key"] for x in r.json()]
    assert set(keys) == {"ceo", "finance", "marketing", "regional"}

    r = client.post("/api/auth/login", json={"role": "regional"})
    assert r.status_code == 200
    assert r.json()["profile"]["region"] == "South India"

    r = client.post("/api/auth/login", json={"role": "not-a-role"})
    assert r.status_code == 400


def test_data_freshness():
    r = client.get("/api/data/freshness")
    assert r.status_code == 200
    sources = r.json()
    assert len(sources) == 7
    assert {"sales", "inventory", "marketing", "reviews", "competitor", "weather", "news"} == {s["id"] for s in sources}


def test_kpis_national_and_regional():
    r = client.get("/api/kpis")
    assert r.status_code == 200
    body = r.json()
    for metric in ["revenue", "profit", "orders", "invHealth", "csat"]:
        assert metric in body["series"]
        assert len(body["series"][metric]["values"]) == len(body["dates"])

    r = client.get("/api/kpis", params={"region": "South India"})
    assert r.status_code == 200
    # the injected shortage must be detected as material for South India
    south_band = r.json()["series"]["revenue"]["materialityBand"]
    assert south_band in ("high", "critical")


def test_events_detect_the_injected_shortage():
    r = client.get("/api/events")
    assert r.status_code == 200
    events = r.json()
    ids = {e["id"] for e in events}
    assert "evt_revenue_drop" in ids
    revenue_evt = next(e for e in events if e["id"] == "evt_revenue_drop")
    assert revenue_evt["severity"] in ("high", "critical")
    assert revenue_evt["region"] == "South India"
    # the sparse-history product must abstain rather than fabricate a cause
    np_evt = next(e for e in events if e["id"] == "evt_new_product")
    assert np_evt["abstain"] is True
    assert np_evt["confidence"]["band"] == "low"


def test_driver_tree_sums_reasonably_and_inventory_dominates():
    r = client.get("/api/driver-tree")
    assert r.status_code == 200
    nodes = {n["id"]: n for n in r.json()["nodes"]}
    children = [nodes[k]["pct"] for k in ("inventory", "competition", "campaign", "weather")]
    assert 95 <= sum(children) <= 101  # normalized shares should sum to ~100
    # inventory shortage should be the dominant driver, matching the injected scenario
    assert nodes["inventory"]["pct"] == max(children)


def test_evidence_graph_is_a_valid_dag_shape():
    r = client.get("/api/evidence/graph")
    assert r.status_code == 200
    body = r.json()
    assert len(body["nodes"]) > 0 and len(body["edges"]) > 0
    node_ids = {n["id"] for n in body["nodes"]}
    for e in body["edges"]:
        assert e["source"] in node_ids and e["target"] in node_ids


def test_recommendations_have_full_required_chain():
    r = client.get("/api/recommendations")
    assert r.status_code == 200
    recs = r.json()
    for rec in recs:
        for field in ["driver", "lever", "action", "impact", "owner", "confidence", "monitoring"]:
            assert rec.get(field), f"{rec['id']} missing required field {field}"

    # Regression guard: confidence must be genuinely computed per-recommendation,
    # not a hardcoded constant shared across recommendations backed by very
    # different amounts of evidence.
    scores = {rec["id"]: rec["confidence"]["score"] for rec in recs}
    assert len(set(scores.values())) == len(scores), f"recommendations should not share identical hardcoded confidence scores: {scores}"
    for rec in recs:
        assert "breakdown" in rec["confidence"], f"{rec['id']} confidence must include the computed breakdown, not a bare constant"


def test_feedback_roundtrip_persists():
    client.delete("/api/feedback")
    before = client.get("/api/feedback/rec_replenish_inventory").json()
    r = client.post("/api/feedback", json={"recId": "rec_replenish_inventory", "action": "accepted"})
    assert r.status_code == 200
    after = client.get("/api/feedback/rec_replenish_inventory").json()
    assert after["accepted"] == before["accepted"] + 1

    r = client.post("/api/feedback", json={"recId": "rec_replenish_inventory", "action": "not-a-real-action"})
    assert r.status_code == 400


def test_simulate_moves_numbers_in_expected_direction():
    r = client.post("/api/simulate", json={
        "priceChangePct": 0, "marketingSpendPct": 0, "inventoryInvestPct": 80, "supplierSwitch": True,
    })
    assert r.status_code == 200
    body = r.json()
    # heavy inventory investment should increase inventory health and revenue vs. baseline
    assert body["result"]["invHealth"] >= body["base"]["invHealth"]
    assert body["result"]["revenue"] >= body["base"]["revenue"]


def test_narrative_endpoints_never_crash_without_api_key():
    r = client.get("/api/summary", params={"persona": "ceo"})
    assert r.status_code == 200
    assert len(r.json()["text"]) > 20

    r = client.get("/api/boardroom")
    assert r.status_code == 200
    agents = r.json()
    assert len(agents) == 7
    assert any(a["role"] == "Decision Agent" for a in agents)

    r = client.post("/api/ask", json={"question": "why did South India underperform?"})
    assert r.status_code == 200
    assert len(r.json()["answer"]) > 10


def test_telemetry_reports_shape():
    r = client.get("/api/telemetry")
    assert r.status_code == 200
    body = r.json()
    for field in ["provider", "model", "configured", "calls", "cacheHits", "avgLatencyMs", "inputTokens", "outputTokens", "estimatedCostUsd"]:
        assert field in body
