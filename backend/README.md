# Backend — AI Meeting-to-Action Board

FastAPI service that turns meeting notes/transcripts into a summary and a
list of action items, using Google Gemini.

## Local development

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # then set GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```

Interactive API docs (Swagger UI) are then available at
`http://localhost:8000/docs`.

## Environment variables

See `.env.example` for the full list. Key ones:

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | — | Optional at startup; LLM routes return 503 without it |
| `GEMINI_MODEL` / `EMBEDDING_MODEL` | `gemini-2.5-flash` / `gemini-embedding-001` | Models used |
| `DATABASE_PATH` | `data/meetings.db` | SQLite memory file |
| `GROUNDING_THRESHOLD` | `0.8` | Min fuzzy score for a quote to count as verified |
| `ENABLE_LLM_VERIFIER` | `false` | Extra LLM entailment check per task |
| `REDACT_PII` | `true` | Redact emails/phones before LLM + storage |
| `API_KEY` / `RATE_LIMIT_PER_MINUTE` | empty / `60` | Auth + rate limiting for `/api/*` |
| `ACTIONS_GITHUB_TOKEN` / `ACTIONS_GITHUB_REPO` | empty | Enable real issue creation on approval |

## Endpoints

- `POST /api/extract`, `POST /api/extract/upload`, `POST /api/extract/stream` (SSE) — grounded extraction; responses include `evidence`, `supported`, `confidence`, `warnings`, `trace`, `meetingId`
- `GET /api/memory/meetings[/{id}]`, `DELETE /api/memory/meetings/{id}`, `GET|PATCH /api/memory/tasks`, `POST /api/memory/ask`, `GET /api/memory/insights`
- `POST /api/actions/propose/{meeting_id}`, `GET /api/actions`, `POST /api/actions/{id}/approve|reject`
- `GET /health`, `GET /api/metrics`

Interactive docs at `/docs`. Run tests with `pytest`, evals with `python -m evals.run_eval`.
