# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# System deps kept minimal — pypdf and google-generativeai are pure-Python.
RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Cloud platforms (Render, Railway, Fly) inject PORT at runtime; default
# to 8000 for local `docker run`.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
