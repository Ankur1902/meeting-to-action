import httpx
import pytest

from app.actions.service import ActionService
from app.memory.service import MemoryService
from app.memory.store import MemoryStore
from app.pipeline.errors import PipelineError
from app.pipeline.runner import ExtractionPipeline
from tests.conftest import GOOD_RESPONSE, TRANSCRIPT, FakeLLM


async def _meeting(settings, store):
    r = await ExtractionPipeline(FakeLLM([GOOD_RESPONSE]), settings).run(TRANSCRIPT, "2026-03-02")
    return await MemoryService(store, FakeLLM()).ingest(
        title="Sprint", meeting_date="2026-03-02", transcript=r["transcript"], response=r["data"])


async def test_propose_creates_pending_only(settings):
    store = MemoryStore()
    mid = await _meeting(settings, store)
    svc = ActionService(store, FakeLLM([{"subject": "Recap", "body": "Hello"}]), settings)
    proposals = await svc.propose(mid)
    kinds = sorted(p["kind"] for p in proposals)
    assert kinds == ["email_draft", "github_issue"]  # only the one High-priority task
    assert all(p["status"] == "pending" for p in proposals)
    assert [p for p in proposals if p["kind"] == "email_draft"][0]["payload"]["subject"] == "Recap"


async def test_email_falls_back_to_template(settings):
    store = MemoryStore()
    mid = await _meeting(settings, store)
    email = (await ActionService(store, FakeLLM(["garbage"]), settings).propose(mid))[0]
    assert email["payload"]["subject"] == "Follow-up: Sprint" and "Fix the checkout bug" in email["payload"]["body"]


async def test_approve_dry_run_without_token(settings):
    store = MemoryStore()
    mid = await _meeting(settings, store)
    svc = ActionService(store, FakeLLM(["x"]), settings)
    issue = [p for p in await svc.propose(mid) if p["kind"] == "github_issue"][0]
    done = await svc.approve(issue["id"])
    assert done["status"] == "executed" and done["result"]["dryRun"] is True
    with pytest.raises(PipelineError) as e:  # cannot approve twice
        await svc.approve(issue["id"])
    assert e.value.status_code == 409


async def test_approve_creates_github_issue(settings):
    settings.github_token, settings.github_repo = "tok", "acme/board"
    seen = {}

    def handler(request: httpx.Request):
        seen["url"], seen["auth"], seen["body"] = str(request.url), request.headers["authorization"], request.read()
        return httpx.Response(201, json={"html_url": "https://github.com/acme/board/issues/7", "number": 7})

    store = MemoryStore()
    mid = await _meeting(settings, store)
    svc = ActionService(store, FakeLLM(["x"]), settings, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    issue = [p for p in await svc.propose(mid) if p["kind"] == "github_issue"][0]
    done = await svc.approve(issue["id"])
    assert seen["url"] == "https://api.github.com/repos/acme/board/issues" and seen["auth"] == "Bearer tok"
    assert done["result"] == {"dryRun": False, "url": "https://github.com/acme/board/issues/7", "number": 7}


async def test_failed_execution_is_recorded(settings):
    settings.github_token, settings.github_repo = "tok", "acme/board"
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(403, json={})))
    store = MemoryStore()
    mid = await _meeting(settings, store)
    svc = ActionService(store, FakeLLM(["x"]), settings, http_client=client)
    issue = [p for p in await svc.propose(mid) if p["kind"] == "github_issue"][0]
    with pytest.raises(PipelineError):
        await svc.approve(issue["id"])
    assert store.get_action(issue["id"])["status"] == "failed"


async def test_reject_and_email_never_sent(settings):
    store = MemoryStore()
    mid = await _meeting(settings, store)
    svc = ActionService(store, FakeLLM(["x"]), settings)
    email, issue = None, None
    for p in await svc.propose(mid):
        email, issue = (p, issue) if p["kind"] == "email_draft" else (email, p)
    assert svc.reject(issue["id"])["status"] == "rejected"
    sent = await svc.approve(email["id"])
    assert sent["result"]["sent"] is False
    with pytest.raises(PipelineError):
        svc.reject(email["id"])


async def test_propose_unknown_meeting(settings):
    with pytest.raises(PipelineError) as e:
        await ActionService(MemoryStore(), FakeLLM(), settings).propose("nope")
    assert e.value.status_code == 404
