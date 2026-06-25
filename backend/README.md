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

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | Yes | — | API key from [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Gemini model used for summarization/extraction |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000` | Comma-separated list of origins allowed by CORS |
| `MAX_UPLOAD_SIZE_BYTES` | No | `10485760` (10MB) | Max size for uploaded transcript files |

## API reference

### `GET /health`
Liveness check. Returns `{"status": "ok"}`.

### `POST /api/extract`
Summarize and extract tasks from pasted text.

**Request**
```json
{ "text": "John will prepare the Q3 sales report by Friday." }
```

**Response** `200 OK`
```json
{
  "summary": {
    "executiveSummary": "string",
    "keyDecisions": ["string"]
  },
  "tasks": [
    {
      "id": "uuid",
      "task": "string",
      "owner": "string",
      "deadline": "string",
      "priority": "High | Medium | Low",
      "status": "todo"
    }
  ]
}
```

### `POST /api/extract/upload`
Same response shape as above, but accepts a `multipart/form-data` body with
a single `file` field (`.txt` or `.pdf`).

**Error responses** (`400`, `502`, `500`) follow:
```json
{ "detail": "Human-readable explanation of what went wrong" }
```

## Running with Docker

```bash
docker build -t meeting-board-backend .
docker run -p 8000:8000 --env-file .env meeting-board-backend
```

## Project layout

```
app/
├── main.py              # FastAPI app, CORS, global error handler
├── routes/extract.py     # /api/extract, /api/extract/upload
├── services/
│   ├── gemini_service.py # Gemini calls + response parsing
│   └── file_service.py   # TXT/PDF text extraction
├── schemas/               # Pydantic request/response models
└── core/
    ├── config.py          # Env-driven settings
    └── prompts.py          # Gemini prompt templates
```
