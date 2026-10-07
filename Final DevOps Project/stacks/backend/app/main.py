"""Stacks - a library lending API.
Name: Hemang | Enrollment number: 24bcs10209

Endpoints
  GET    /health              liveness  - process only, never touches the DB
  GET    /ready               readiness - DOES check the DB
  GET    /metrics             Prometheus exposition format
  GET    /api/books           list the catalogue
  POST   /api/books           add a copy
  GET    /api/books/stats     shelf summary (declared BEFORE /{id}, see below)
  GET    /api/books/{id}      read one
  PUT    /api/books/{id}      correct a record, or lend / return a copy
  DELETE /api/books/{id}      withdraw a copy
"""
import time
from datetime import date, timedelta

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import db as database
from app.config import settings
from app.models import Book
from app.schemas import BookCreate, BookOut, BookUpdate, HealthOut, StatsOut

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Library lending API - DevOps capstone. Hemang / 24bcs10209",
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
    counts = _shelf_counts(db)
    reqs = _metrics["requests_total"]
    avg = _metrics["latency_sum"] / reqs if reqs else 0.0
    body = "\n".join(
        [
            "# HELP stacks_http_requests_total Total HTTP requests served.",
            "# TYPE stacks_http_requests_total counter",
            f'stacks_http_requests_total{{version="{settings.APP_VERSION}"}} '
            f'{_metrics["requests_total"]}',
            "# HELP stacks_http_errors_total Total 5xx responses.",
            "# TYPE stacks_http_errors_total counter",
            f'stacks_http_errors_total{{version="{settings.APP_VERSION}"}} '
            f'{_metrics["errors_total"]}',
            "# HELP stacks_request_latency_seconds Average request latency.",
            "# TYPE stacks_request_latency_seconds gauge",
            f"stacks_request_latency_seconds {avg:.6f}",
            "# HELP stacks_uptime_seconds Seconds since process start.",
            "# TYPE stacks_uptime_seconds gauge",
            f"stacks_uptime_seconds {time.time() - _started:.1f}",
            "# HELP stacks_books_total Copies in the catalogue, by state.",
            "# TYPE stacks_books_total gauge",
            f'stacks_books_total{{state="available"}} {counts["available"]}',
            f'stacks_books_total{{state="borrowed"}} {counts["borrowed"]}',
            # overdue is a SUBSET of borrowed, not a fourth state
            "# HELP stacks_books_overdue Loans past their due date.",
            "# TYPE stacks_books_overdue gauge",
            f'stacks_books_overdue {counts["overdue"]}',
            "",
        ]
    )
    return Response(content=body, media_type="text/plain; version=0.0.4")


def _shelf_counts(db: Session) -> dict[str, int]:
    rows = db.execute(select(Book.state, func.count(Book.id)).group_by(Book.state)).all()
    by_state = {state: count for state, count in rows}
    overdue = db.scalar(
        select(func.count(Book.id)).where(
            Book.state == "BORROWED", Book.due_date.is_not(None), Book.due_date < date.today()
        )
    )
    return {
        "total": sum(by_state.values()),
        "available": by_state.get("AVAILABLE", 0),
        "borrowed": by_state.get("BORROWED", 0),
        "overdue": overdue or 0,
    }


# ----------------------------------------------------------------- catalogue
@app.get("/api/books", response_model=list[BookOut], tags=["books"])
def list_books(db: Session = Depends(database.get_db)):
    return db.execute(select(Book).order_by(Book.id)).scalars().all()


@app.post("/api/books", response_model=BookOut, status_code=201, tags=["books"])
def add_book(payload: BookCreate, db: Session = Depends(database.get_db)):
    book = Book(title=payload.title, author=payload.author, isbn=payload.isbn)
    db.add(book)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"isbn {payload.isbn} is already shelved")
    db.refresh(book)
    return book


# NOTE: /stats must be declared before /{book_id}, or FastAPI matches "stats"
# as a path parameter and fails to parse it as an int.
@app.get("/api/books/stats", response_model=StatsOut, tags=["books"])
def shelf_stats(db: Session = Depends(database.get_db)) -> StatsOut:
    return StatsOut(**_shelf_counts(db))


@app.get("/api/books/{book_id}", response_model=BookOut, tags=["books"])
def get_book(book_id: int, db: Session = Depends(database.get_db)):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail=f"book {book_id} not found")
    return book


@app.put("/api/books/{book_id}", response_model=BookOut, tags=["books"])
def update_book(book_id: int, payload: BookUpdate, db: Session = Depends(database.get_db)):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail=f"book {book_id} not found")

    if payload.title is not None:
        book.title = payload.title
    if payload.author is not None:
        book.author = payload.author

    if payload.state == "BORROWED":
        if book.state == "BORROWED":
            raise HTTPException(
                status_code=409, detail=f"book {book_id} is already on loan to {book.borrower}"
            )
        if not payload.borrower:
            raise HTTPException(status_code=422, detail="borrower is required to lend a copy")
        book.state = "BORROWED"
        book.borrower = payload.borrower
        # the caller may set a due date; otherwise apply the standard loan period
        book.due_date = payload.due_date or date.today() + timedelta(days=settings.LOAN_DAYS)
    elif payload.state == "AVAILABLE":
        # returning a copy clears the loan entirely
        book.state = "AVAILABLE"
        book.borrower = None
        book.due_date = None
    elif payload.due_date is not None and book.state == "BORROWED":
        book.due_date = payload.due_date  # a renewal

    db.commit()
    db.refresh(book)
    return book


@app.delete("/api/books/{book_id}", status_code=204, tags=["books"])
def withdraw_book(book_id: int, db: Session = Depends(database.get_db)):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail=f"book {book_id} not found")
    if book.state == "BORROWED":
        raise HTTPException(
            status_code=409, detail=f"book {book_id} is on loan and cannot be withdrawn"
        )
    db.delete(book)
    db.commit()
    return Response(status_code=204)
