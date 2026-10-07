"""TaskBoard API - the capstone application.
Name: Hemang | Enrollment number: 24bcs10209
"""
import os
import time

from flask import Flask, jsonify, request

from app import db

app = Flask(__name__)

APP_VERSION = os.getenv("APP_VERSION", "dev")
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")      # from ConfigMap
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")           # from ConfigMap

_started = time.time()
_requests = {"total": 0, "errors": 0}

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>TaskBoard</title>
<style>body{{font-family:system-ui,sans-serif;max-width:720px;margin:4rem auto;
background:#111;color:#eee}}h1{{margin-bottom:.2rem}}code{{color:#8cc}}
li{{margin:.3rem 0}}.done{{opacity:.5;text-decoration:line-through}}</style></head>
<body><h1>TaskBoard</h1>
<p><code>version {version} &middot; env {env} &middot; store {store}</code></p>
<p>Hemang &middot; 24bcs10209</p>
<h3>Tasks</h3><ul>{items}</ul>
<p><code>GET /health</code> &middot; <code>GET /ready</code> &middot;
<code>GET /metrics</code> &middot; <code>GET /api/tasks</code></p>
</body></html>"""


@app.before_request
def _count():
    _requests["total"] += 1


@app.route("/")
def index():
    tasks = db.list_tasks()
    items = "".join(
        f'<li class="{"done" if t["done"] else ""}">#{t["id"]} {t["title"]}</li>'
        for t in tasks
    ) or "<li><em>no tasks yet</em></li>"
    return PAGE.format(
        version=APP_VERSION,
        env=ENVIRONMENT,
        store="postgres" if db.using_postgres() else "memory",
        items=items,
    )


# --- probes -----------------------------------------------------------------
@app.route("/health")
def health():
    """LIVENESS: is the process itself alive? Deliberately does NOT check the
    database - a slow database must not cause every pod to be restarted."""
    return jsonify(status="ok", version=APP_VERSION, uptime_s=round(time.time() - _started, 1))


@app.route("/ready")
def ready():
    """READINESS: can this pod actually serve traffic? This DOES check the
    datastore, so a pod with no database is removed from Service endpoints."""
    if db.healthy():
        return jsonify(status="ready", store="postgres" if db.using_postgres() else "memory")
    _requests["errors"] += 1
    return jsonify(status="not-ready", reason="datastore unreachable"), 503


# --- metrics ----------------------------------------------------------------
@app.route("/metrics")
def metrics():
    """Prometheus exposition format."""
    lines = [
        "# HELP taskboard_requests_total Total HTTP requests served.",
        "# TYPE taskboard_requests_total counter",
        f'taskboard_requests_total{{version="{APP_VERSION}"}} {_requests["total"]}',
        "# HELP taskboard_errors_total Total failed readiness checks.",
        "# TYPE taskboard_errors_total counter",
        f'taskboard_errors_total{{version="{APP_VERSION}"}} {_requests["errors"]}',
        "# HELP taskboard_uptime_seconds Seconds since process start.",
        "# TYPE taskboard_uptime_seconds gauge",
        f"taskboard_uptime_seconds {time.time() - _started:.1f}",
        "# HELP taskboard_tasks Number of tasks stored.",
        "# TYPE taskboard_tasks gauge",
        f"taskboard_tasks {len(db.list_tasks())}",
    ]
    return "\n".join(lines) + "\n", 200, {"Content-Type": "text/plain; version=0.0.4"}


# --- api --------------------------------------------------------------------
@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    return jsonify(tasks=db.list_tasks())


@app.route("/api/tasks", methods=["POST"])
def create_task():
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    if not title:
        _requests["errors"] += 1
        return jsonify(error="title is required"), 400
    return jsonify(db.add_task(title)), 201


@app.route("/api/tasks/<int:task_id>/complete", methods=["POST"])
def finish_task(task_id):
    task = db.complete_task(task_id)
    if task is None:
        return jsonify(error=f"task {task_id} not found"), 404
    return jsonify(task)


def create_app():
    db.init()
    return app


if __name__ == "__main__":
    db.init()
    # bandit B104: 0.0.0.0 is required inside a container - see DevSecOps notes.
    app.run(host="0.0.0.0", port=8000)  # nosec B104
