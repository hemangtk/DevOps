"""Storage layer. Uses Postgres when DATABASE_URL is set, otherwise an
in-memory store so the app runs standalone for tests and local work.
Name: Hemang | Enrollment number: 24bcs10209
"""
import os
import threading

DATABASE_URL = os.getenv("DATABASE_URL", "")

_lock = threading.Lock()
_mem: dict[int, dict] = {}
_next_id = [1]


def using_postgres() -> bool:
    return bool(DATABASE_URL)


def _pg():
    import psycopg
    return psycopg.connect(DATABASE_URL)


def init() -> None:
    if not using_postgres():
        return
    with _pg() as conn, conn.cursor() as cur:
        cur.execute(
            """CREATE TABLE IF NOT EXISTS tasks (
                   id    SERIAL PRIMARY KEY,
                   title TEXT NOT NULL,
                   done  BOOLEAN NOT NULL DEFAULT FALSE
               )"""
        )
        conn.commit()


def list_tasks() -> list[dict]:
    if not using_postgres():
        with _lock:
            return sorted(_mem.values(), key=lambda t: t["id"])
    with _pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, title, done FROM tasks ORDER BY id")
        return [{"id": r[0], "title": r[1], "done": r[2]} for r in cur.fetchall()]


def add_task(title: str) -> dict:
    if not using_postgres():
        with _lock:
            tid = _next_id[0]
            _next_id[0] += 1
            _mem[tid] = {"id": tid, "title": title, "done": False}
            return _mem[tid]
    with _pg() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO tasks (title, done) VALUES (%s, FALSE) RETURNING id, title, done",
            (title,),
        )
        r = cur.fetchone()
        conn.commit()
        return {"id": r[0], "title": r[1], "done": r[2]}


def complete_task(task_id: int) -> dict | None:
    if not using_postgres():
        with _lock:
            t = _mem.get(task_id)
            if t:
                t["done"] = True
            return t
    with _pg() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE tasks SET done = TRUE WHERE id = %s RETURNING id, title, done",
            (task_id,),
        )
        r = cur.fetchone()
        conn.commit()
        return {"id": r[0], "title": r[1], "done": r[2]} if r else None


def healthy() -> bool:
    """Readiness depends on the datastore actually answering."""
    if not using_postgres():
        return True
    try:
        with _pg() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            return cur.fetchone()[0] == 1
    except Exception:
        return False
