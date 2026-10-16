# Production Observability API

FastAPI service for the observability lab. It provides:

- `GET /work?n=K`: performs K bounded arithmetic work units and returns `{"email": "24f2007275@ds.study.iitm.ac.in", "done": K}`.
- `GET /metrics`: live Prometheus exposition with `http_requests_total`, incremented by middleware on every HTTP request.
- `GET /healthz`: returns `{"status":"ok","uptime_s":...}`.
- `GET /logs/tail?limit=N`: returns the last N structured JSON request-log entries. Each entry includes `level`, `ts`, `path`, and `request_id` (plus method/status/duration).

## Run locally

```bash
python -m pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Deploy on Render

Create a new Web Service from this repository and add an environment variable `STUDENT_EMAIL` whose value is the exact email used to log into the assignment:

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

Submit the service base URL (do not append an endpoint path).
