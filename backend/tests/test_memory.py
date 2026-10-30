from datetime import date

from app.memory.service import MemoryService, chunk_text
from app.memory.store import MemoryStore
from app.pipeline.runner import ExtractionPipeline
from tests.conftest import GOOD_RESPONSE, TRANSCRIPT, FakeLLM


def test_chunking_respects_size():
    text = " ".join(f"Sentence number {i} is here." for i in range(60))
    chunks = chunk_text(text, 200)
    assert len(chunks) > 3 and all(len(c) <= 230 for c in chunks)
    assert chunk_text("") == []


async def _ingest(mem, settings, response, title, day):
    r = (await ExtractionPipeline(FakeLLM([response]), settings).run(TRANSCRIPT, day))
    return await mem.ingest(title=title, meeting_date=day, transcript=r["transcript"], response=r["data"])


async def test_ingest_and_cited_qa(settings):
    store = MemoryStore()
    llm = FakeLLM(default="The checkout bug is Marcus's [1].")
    mem = MemoryService(store, llm)
    mid = await _ingest(mem, settings, GOOD_RESPONSE, "Sprint", "2026-03-02")
    out = await mem.ask("who is fixing the checkout bug?")
    assert out["answer"].endswith("[1].")
    assert out["sources"][0]["meetingId"] == mid
    assert "checkout" in out["sources"][0]["text"].lower()
    assert "Question: who is fixing" in llm.prompts[-1] and "[1]" in llm.prompts[-1]


async def test_ask_with_empty_memory(settings):
    mem = MemoryService(MemoryStore(), FakeLLM())
    out = await mem.ask("anything at all?")
    assert out["sources"] == [] and "couldn't find" in out["answer"]


async def test_insights_overdue_duplicates_conflicts(settings):
    store = MemoryStore()
    mem = MemoryService(store, FakeLLM())
    await _ingest(mem, settings, GOOD_RESPONSE, "Week 1", "2026-03-02")
    dup = {**GOOD_RESPONSE, "tasks": [GOOD_RESPONSE["tasks"][0]]}
    await _ingest(mem, settings, dup, "Week 2", "2026-03-09")
    conflict = {**GOOD_RESPONSE, "tasks": [{**GOOD_RESPONSE["tasks"][0], "owner": "Dana", "quote": "I'll update the release notes by Thursday."}]}
    await _ingest(mem, settings, conflict, "Week 3", "2026-03-16")

    ins = mem.insights(today=date(2026, 3, 20))
    assert len(ins["overdue"]) == 3 and ins["overdue"][0]["daysOverdue"] == 16
    assert len(ins["duplicates"]) == 1
    assert len(ins["conflicts"]) == 2  # Dana version conflicts with both Marcus versions

    # completing a task removes it from insights
    for t in store.list_tasks():
        store.update_task_status(t["id"], "done")
    assert mem.insights(today=date(2026, 3, 20)) == {"overdue": [], "duplicates": [], "conflicts": []}


async def test_dimension_mismatch_is_ignored(settings):
    store = MemoryStore()
    mem = MemoryService(store, FakeLLM())
    await _ingest(mem, settings, GOOD_RESPONSE, "Sprint", "2026-03-02")
    assert store.search([0.1, 0.2, 0.3], 3) == []


def test_delete_cascades():
    store = MemoryStore()
    mid = store.save_meeting(title="t", meeting_date="2026-01-01", summary={}, trace=[],
                             tasks=[{"id": "1", "status": "todo", "owner": "a", "task": "x"}],
                             chunks=["hello"], embeddings=[[1.0, 0.0]])
    assert store.delete_meeting(mid)
    assert store.list_tasks() == [] and store.search([1.0, 0.0]) == []
