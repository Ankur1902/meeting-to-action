.PHONY: test eval eval-gemini dev-backend dev-frontend demo

test:
	cd backend && pytest -q

eval:  ## offline baseline + regression gate
	cd backend && python -m evals.run_eval --provider baseline --check

eval-gemini:  ## needs GEMINI_API_KEY; compares models
	cd backend && python -m evals.run_eval --provider gemini --models gemini-2.5-flash,gemini-2.5-pro --judge

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

demo:  ## offline demo API (no API key) on :8000 — pair with `make dev-frontend`
	cd backend && uvicorn demo_server:app --port 8000
