"""
A small Flask "Tasks" API, built to be deployment-friendly.

Deliberate choices you'll care about as a DevOps engineer:
  - Config comes from environment variables (12-factor), not hardcoded.
  - There's a /health endpoint for container/orchestrator probes.
  - Logging goes to stdout so `docker logs` and log collectors just work.
  - No dev-server assumptions: gunicorn runs `app` in production (see Dockerfile).
"""

import logging
import os
import sys
from datetime import datetime, timezone

from flask import Flask, jsonify, request

# ---------------------------------------------------------------------------
# Configuration (read once, from the environment)
# ---------------------------------------------------------------------------
APP_NAME = os.getenv("APP_NAME", "tasks-api")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
# PORT is only used when you run this file directly (dev). In the container,
# gunicorn binds the port instead — see the Dockerfile.
PORT = int(os.getenv("PORT", "8000"))

# ---------------------------------------------------------------------------
# Logging to stdout — the container-friendly default
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    stream=sys.stdout,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger(APP_NAME)

app = Flask(__name__)

# ---------------------------------------------------------------------------
# In-memory "database". Fine for learning; resets on restart. Swapping this
# for Postgres/Redis later is a great follow-up exercise.
# ---------------------------------------------------------------------------
_tasks: dict[int, dict] = {}
_next_id = 1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
def index():
    """Human-friendly landing info, and a map of what the API offers."""
    return jsonify(
        service=APP_NAME,
        version=APP_VERSION,
        message="A tiny Tasks API for learning containerized deployment.",
        endpoints={
            "health":       "GET  /health",
            "list_tasks":   "GET  /api/tasks",
            "create_task":  "POST /api/tasks   {\"title\": \"...\"}",
            "get_task":     "GET  /api/tasks/<id>",
            "delete_task":  "DELETE /api/tasks/<id>",
        },
    )


@app.get("/health")
def health():
    """
    Liveness/readiness probe target.
    Orchestrators (Kubernetes, ECS, a load balancer) hit this to decide
    whether the container is healthy and should receive traffic.
    Keep it cheap and dependency-light.
    """
    return jsonify(status="ok", service=APP_NAME, version=APP_VERSION, time=_now())


@app.get("/api/tasks")
def list_tasks():
    return jsonify(tasks=list(_tasks.values()), count=len(_tasks))


@app.post("/api/tasks")
def create_task():
    global _next_id
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify(error="'title' is required"), 400

    task = {
        "id": _next_id,
        "title": title,
        "done": False,
        "created_at": _now(),
    }
    _tasks[_next_id] = task
    log.info("created task id=%s title=%r", _next_id, title)
    _next_id += 1
    return jsonify(task), 201


@app.get("/api/tasks/<int:task_id>")
def get_task(task_id: int):
    task = _tasks.get(task_id)
    if task is None:
        return jsonify(error="task not found"), 404
    return jsonify(task)


@app.delete("/api/tasks/<int:task_id>")
def delete_task(task_id: int):
    if _tasks.pop(task_id, None) is None:
        return jsonify(error="task not found"), 404
    log.info("deleted task id=%s", task_id)
    return "", 204


if __name__ == "__main__":
    # Development entrypoint only. In the container we use gunicorn, which is
    # a real WSGI server — Flask's built-in server is not meant for production.
    log.info("starting %s v%s (dev server) on port %s", APP_NAME, APP_VERSION, PORT)
    app.run(host="0.0.0.0", port=PORT, debug=True)
