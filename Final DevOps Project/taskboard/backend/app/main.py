"""TaskBoard FastAPI backend.
Name: Hemang | Enrollment number: 24bcs10209

Endpoints
  GET    /health              liveness  - process only, never touches the DB
  GET    /ready               readiness - DOES check the DB
  GET    /metrics             Prometheus exposition format
  GET    /api/tasks           list
  POST   /api/tasks           create
  GET    /api/tasks/{id}      read one
  PUT    /api/tasks/{id}      update
  DELETE /api/tasks/{id}      delete
"""
import time

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import db as database
from app.config import settings
from app.models import Task
from app.schemas import HealthOut, TaskCreate, TaskOut, TaskUpdate

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Task management API - DevOps capstone. Hemang / 24bcs10209",
)

# the frontend is served from a different origin in dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_started = time.time()
_metrics = {"requests_total": 0, "errors_total": 0, "latency_sum": 0.0}


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    begin = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - begin
    _metrics["requests_total"] += 1
    _metrics["latency_sum"] += elapsed
    if response.status_code >= 500:
        _metrics["errors_total"] += 1
    return response


# ----------------------------------------------------------------- probes
@app.get("/health", response_model=HealthOut, tags=["ops"])
def health() -> HealthOut:
    """LIVENESS. Deliberately does NOT touch the database: a slow database must
    not cause Kubernetes to restart every pod."""
    return HealthOut(
        status="ok", version=settings.APP_VERSION, environment=settings.ENVIRONMENT
    )


@app.get("/ready", tags=["ops"])
def ready(response: Response):
    """READINESS. DOES check the database, so a pod that cannot serve is removed
    from Service endpoints without being restarted."""
    if database.database_reachable():
        return {"status": "ready", "database": "reachable"}
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "not-ready", "database": "unreachable"}


@app.get("/metrics", tags=["ops"])
def metrics(db: Session = Depends(database.get_db)) -> Response:
    task_count = db.scalar(select(func.count()).select_from(Task)) or 0
    avg = _metrics["latency_sum"] / _metrics["requests_total"] if _metrics["requests_total"] else 0.0
    body = "\n".join(
        [
            "# HELP taskboard_http_requests_total Total HTTP requests served.",
            "# TYPE taskboard_http_requests_total counter",
            f'taskboard_http_requests_total{{version="{settings.APP_VERSION}"}} '
            f'{_metrics["requests_total"]}',
            "# HELP taskboard_http_errors_total Total 5xx responses.",
            "# TYPE taskboard_http_errors_total counter",
            f'taskboard_http_errors_total{{version="{settings.APP_VERSION}"}} '
            f'{_metrics["errors_total"]}',
            "# HELP taskboard_request_latency_seconds Average request latency.",
            "# TYPE taskboard_request_latency_seconds gauge",
            f"taskboard_request_latency_seconds {avg:.6f}",
            "# HELP taskboard_uptime_seconds Seconds since process start.",
            "# TYPE taskboard_uptime_seconds gauge",
            f"taskboard_uptime_seconds {time.time() - _started:.1f}",
            "# HELP taskboard_tasks_total Tasks currently stored.",
            "# TYPE taskboard_tasks_total gauge",
            f"taskboard_tasks_total {task_count}",
            "",
        ]
    )
    return Response(content=body, media_type="text/plain; version=0.0.4")


# ----------------------------------------------------------------- CRUD
@app.get("/api/tasks", response_model=list[TaskOut], tags=["tasks"])
def list_tasks(db: Session = Depends(database.get_db)):
    return db.execute(select(Task).order_by(Task.id)).scalars().all()


@app.post("/api/tasks", response_model=TaskOut, status_code=201, tags=["tasks"])
def create_task(payload: TaskCreate, db: Session = Depends(database.get_db)):
    task = Task(title=payload.title, description=payload.description)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.get("/api/tasks/{task_id}", response_model=TaskOut, tags=["tasks"])
def get_task(task_id: int, db: Session = Depends(database.get_db)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"task {task_id} not found")
    return task


@app.put("/api/tasks/{task_id}", response_model=TaskOut, tags=["tasks"])
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(database.get_db)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"task {task_id} not found")
    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description
    if payload.done is not None:
        task.done = payload.done
    db.commit()
    db.refresh(task)
    return task


@app.delete("/api/tasks/{task_id}", status_code=204, tags=["tasks"])
def delete_task(task_id: int, db: Session = Depends(database.get_db)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"task {task_id} not found")
    db.delete(task)
    db.commit()
    return Response(status_code=204)
