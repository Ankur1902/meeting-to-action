import json

import pytest
from fastapi.testclient import TestClient

from app import deps
from app.core.config import Settings, get_settings
from app.main import app
from app.memory.store import MemoryStore
from tests.conftest import GOOD_RESPONSE, TRANSCRIPT, FakeLLM


@pytest.fixture
def client(settings):
    store, llm = MemoryStore(), FakeLLM(default=lambda p: GOOD_RESPONSE if "<transcript>" in p else "Answer [1].")
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[deps.get_store] = lambda: store
    app.dependency_overrides[deps.get_llm] = lambda: llm
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health_and_request_id(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.headers["x-request-id"]


def test_extract_end_to_end_persists(client):
    r = client.post("/api/extract", json={"text": TRANSCRIPT, "title": "Sprint", "meetingDate": "2026-03-02"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["meetingId"] and len(body["tasks"]) == 2
    assert body["tasks"][0]["evidence"]["verified"] is True
    assert body["summary"]["keyDecisions"] == ["Freeze the feature list"]
    assert [s["step"] for s in body["trace"]][0] == "clean"

    meetings = client.get("/api/memory/meetings").json()
    assert meetings[0]["title"] == "Sprint" and meetings[0]["task_count"] == 2
    assert client.get(f"/api/memory/meetings/{body['meetingId']}").json()["tasks"][0]["owner"] == "Marcus"


def test_extract_persist_false(client):
    r = client.post("/api/extract", json={"text": TRANSCRIPT, "persist": False})
    assert r.json()["meetingId"] is None and client.get("/api/memory/meetings").json() == []


def test_extract_validation(client):
    assert client.post("/api/extract", json={"text": ""}).status_code == 422
    assert client.post("/api/extract", json={"text": "   "}).status_code == 400


def test_extract_upload_txt(client):
    r = client.post("/api/extract/upload", files={"file": ("m.txt", TRANSCRIPT.encode(), "text/plain")})
    assert r.status_code == 200 and len(r.json()["tasks"]) == 2
    assert client.post("/api/extract/upload", files={"file": ("m.exe", b"x")}).status_code in (400, 415)


def test_extract_stream_sse(client):
    r = client.post("/api/extract/stream", json={"text": TRANSCRIPT})
    events = [l.split(": ", 1)[1] for l in r.text.splitlines() if l.startswith("event:")]
    assert events == ["step"] * 5 + ["result"]
    last = [l for l in r.text.splitlines() if l.startswith("data:")][-1]
    assert len(json.loads(last[6:])["tasks"]) == 2


def test_llm_not_configured_returns_503(settings):
    from app.llm.factory import NoLLMClient

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[deps.get_store] = lambda: MemoryStore()
    app.dependency_overrides[deps.get_llm] = lambda: NoLLMClient()
    try:
        r = TestClient(app).post("/api/extract", json={"text": TRANSCRIPT})
        assert r.status_code == 503 and "not configured" in r.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_memory_ask_tasks_insights(client):
    client.post("/api/extract", json={"text": TRANSCRIPT, "meetingDate": "2026-03-02"})
    ans = client.post("/api/memory/ask", json={"question": "who fixes the checkout bug?"}).json()
    assert ans["answer"] == "Answer [1]." and ans["sources"]
    assert client.post("/api/memory/ask", json={"question": "x"}).status_code == 422

    tasks = client.get("/api/memory/tasks").json()
    tid = tasks[0]["id"]
    assert client.patch(f"/api/memory/tasks/{tid}", json={"status": "done"}).status_code == 200
    assert client.patch(f"/api/memory/tasks/{tid}", json={"status": "bogus"}).status_code == 422
    assert client.patch("/api/memory/tasks/missing", json={"status": "done"}).status_code == 404
    assert len(client.get("/api/memory/tasks", params={"status": "done"}).json()) == 1

    ins = client.get("/api/memory/insights", params={"today": "2026-04-01"}).json()
    assert len(ins["overdue"]) == 0 or all(t["status"] != "done" for t in ins["overdue"])


def test_actions_flow(client):
    mid = client.post("/api/extract", json={"text": TRANSCRIPT, "meetingDate": "2026-03-02"}).json()["meetingId"]
    props = client.post(f"/api/actions/propose/{mid}").json()
    assert {p["kind"] for p in props} == {"email_draft", "github_issue"}
    pending = client.get("/api/actions", params={"status": "pending"}).json()
    assert len(pending) == 2
    issue = next(p for p in props if p["kind"] == "github_issue")
    assert client.post(f"/api/actions/{issue['id']}/approve").json()["status"] == "executed"
    assert client.post(f"/api/actions/{issue['id']}/approve").status_code == 409
    assert client.post("/api/actions/none/reject").status_code == 404
    assert client.post("/api/actions/propose/none").status_code == 404


def test_api_key_and_rate_limit(client, settings):
    settings.api_key = "secret"
    assert client.get("/api/memory/meetings").status_code == 401
    assert client.get("/api/memory/meetings", headers={"X-API-Key": "secret"}).status_code == 200
    assert client.get("/health").status_code == 200  # health is not protected
    settings.api_key = ""

    from app.core.security import RateLimiter
    rl = RateLimiter(2)
    assert rl.allow("ip", 0) and rl.allow("ip", 1) and not rl.allow("ip", 2) and rl.allow("ip", 61.5)


def test_metrics(client):
    client.get("/health")
    snap = client.get("/api/metrics").json()
    assert "/health|200" in snap["requests"]
