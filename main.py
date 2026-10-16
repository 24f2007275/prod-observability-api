import json
import logging
import os
import math
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Deque, Dict, Any

from fastapi import FastAPI, Query, Request
from fastapi.responses import Response
from prometheus_client import Counter, CONTENT_TYPE_LATEST, generate_latest

STUDENT_EMAIL = os.getenv("STUDENT_EMAIL", "YOUR_IITM_LOGIN_EMAIL")

app = FastAPI(title="Production Observability API", version="1.0.0")

# Prometheus counter: the middleware increments this for every HTTP request,
# including requests to /metrics, /healthz, /logs/tail, and /work.
HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total number of HTTP requests received by this service",
)

_started_at = time.monotonic()
_log_entries: Deque[Dict[str, Any]] = deque(maxlen=2000)
_log_lock = threading.Lock()
_logger = logging.getLogger("observability")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_handler)
_logger.propagate = False


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    started = time.monotonic()
    HTTP_REQUESTS.inc()
    status_code = 500
    level = "INFO"
    try:
        response = await call_next(request)
        status_code = response.status_code
        if status_code >= 500:
            level = "ERROR"
        elif status_code >= 400:
            level = "WARNING"
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception:
        level = "ERROR"
        raise
    finally:
        entry = {
            "level": level,
            "ts": _utc_timestamp(),
            "path": request.url.path,
            "request_id": request_id,
            "method": request.method,
            "status_code": status_code,
            "duration_s": max(0.0, time.monotonic() - started),
        }
        with _log_lock:
            _log_entries.append(entry)
        _logger.info(json.dumps(entry, separators=(",", ":"), ensure_ascii=False))


@app.get("/")
async def root():
    return {"service": "production-observability-api", "status": "ok"}


@app.get("/work")
async def work(n: int = Query(default=1, ge=0, le=1_000_000)):
    # Perform K deterministic work units instead of returning a hard-coded K.
    # This bounded arithmetic loop gives the endpoint actual work to do.
    accumulator = 0
    for i in range(n):
        accumulator = (accumulator + i + 1) % 1_000_000_007
    return {"email": STUDENT_EMAIL, "done": n}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/healthz")
async def healthz():
    uptime_s = max(0.0, time.monotonic() - _started_at)
    # Keep the value finite even in unusual runtime conditions.
    if not math.isfinite(uptime_s):
        uptime_s = 0.0
    return {"status": "ok", "uptime_s": uptime_s}


@app.get("/logs/tail")
async def logs_tail(limit: int = Query(default=50, ge=0, le=2000)):
    with _log_lock:
        entries = list(_log_entries)
    if limit == 0:
        return []
    return entries[-limit:]
