.PHONY: test eval eval-gemini dev-backend dev-frontend

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
