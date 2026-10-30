import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import ai, search

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_health_and_index(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    assert "LaunchMate" in client.get("/").text

def test_status_demo_without_keys(client):
    s = client.get("/api/status").json()
    assert s["demo"] and not s["live_ai"] and not s["ai_configured"]

def test_key_validation_error_is_clear(client):
    r = client.post("/api/status/check").json()
    assert "NEBIUS_API_KEY" in r["ai"] and "TAVILY_API_KEY" in r["search"]

def test_demo_research_labels_data(client):
    r = client.post("/api/research", json={"keywords": "python ai"}).json()
    assert r["ok"] and r["demo"] and r["new"] == 3
    opps = client.get("/api/opportunities").json()
    assert all(o["is_demo"] and not o["verified"] and o["deadline_status"] == "unconfirmed" for o in opps)
    assert client.post("/api/research", json={"keywords": "python"}).json()["new"] == 0  # dedupe

def test_task_crud(client):
    t = client.post("/api/tasks", json={"title": "Do it", "due": "2000-01-01"}).json()
    assert t["overdue"]
    client.put(f"/api/tasks/{t['id']}", json={"title": "Do it", "status": "done", "due": "2000-01-01"})
    assert [x for x in client.get("/api/tasks").json() if x["id"] == t["id"]][0]["status"] == "done"
    assert client.delete(f"/api/tasks/{t['id']}").status_code == 200
    assert client.post("/api/tasks", json={"title": "x", "due": "bad"}).status_code == 422

def test_kit_demo_and_exports(client):
    oid = client.get("/api/opportunities").json()[0]["id"]
    k = client.post(f"/api/opportunities/{oid}/kit").json()
    assert k["mode"] == "demo"
    doc = client.get("/api/documents").json()[0]
    assert "Nothing has been submitted" in doc["content"]
    assert "attachment" in client.get(f"/api/documents/{doc['id']}/download?fmt=txt").headers["content-disposition"]
    assert client.get("/api/export/opportunities.csv").text.startswith("id,title")
    assert "Preparation pack" in client.get(f"/api/export/pack/{oid}.md").text
    assert client.get("/api/export/nope.csv").status_code == 404

def test_workflow_with_mocked_services(client, monkeypatch):
    monkeypatch.setattr(search, "configured", lambda: True)
    monkeypatch.setattr(search, "search", lambda q, n=8: [{"title": "Real-ish Hack", "url": "https://mock.test/h?utm_x=1", "snippet": "python agents", "published": ""}])
    monkeypatch.setattr(ai, "configured", lambda: True)
    monkeypatch.setattr(ai, "chat_json", lambda s, u: {"items": [{"url": "https://mock.test/h", "relevance": "good", "uncertainties": "deadline unknown"}]})
    r = client.post("/api/research", json={"keywords": "python"}).json()
    assert r["ok"] and not r["demo"] and r["new"] == 1
    o = [x for x in client.get("/api/opportunities").json() if "Real-ish" in x["title"]][0]
    assert "good" in o["analysis"] and not o["is_demo"]

def test_stage_failure_reported_and_data_kept(client, monkeypatch):
    before = len(client.get("/api/opportunities").json())
    monkeypatch.setattr(search, "configured", lambda: True)
    def boom(q, n=8): raise search.SearchUnavailable("timeout")
    monkeypatch.setattr(search, "search", boom)
    r = client.post("/api/research", json={}).json()
    assert not r["ok"] and r["stages"][0]["status"] == "failed"
    assert len(client.get("/api/opportunities").json()) == before

def test_ai_timeout_is_wrapped(monkeypatch):
    from app.config import settings
    monkeypatch.setenv("NEBIUS_API_KEY", "secret-key-123")
    class Boom:
        def __getattr__(self, n): raise TimeoutError("timed out secret-key-123")
    monkeypatch.setattr(ai, "_client", lambda: Boom())
    with pytest.raises(ai.AIUnavailable) as e:
        ai.chat("s", "u")
    assert "secret-key-123" not in str(e.value) and "NEBIUS_MODEL" in str(e.value)

def test_clear_requires_confirmation(client):
    assert client.post("/api/clear", json={"confirm": "no"}).status_code == 400
    assert client.post("/api/clear", json={"confirm": "DELETE"}).status_code == 200
    assert client.get("/api/opportunities").json() == []
