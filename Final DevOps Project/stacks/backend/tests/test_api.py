"""API tests for Stacks. Runs against a throwaway SQLite database.
Name: Hemang | Enrollment number: 24bcs10209
"""
from datetime import date, timedelta

PRAGMATIC = {
    "title": "The Pragmatic Programmer",
    "author": "Hunt & Thomas",
    "isbn": "9780135957059",
}
SICP = {"title": "SICP", "author": "Abelson & Sussman", "isbn": "9780262510875"}


def _add(client, payload=None):
    response = client.post("/api/books", json=payload or PRAGMATIC)
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------- ops
def test_health_does_not_touch_the_database(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"


def test_ready_reports_the_database(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "reachable"


def test_metrics_are_prometheus_formatted(client):
    _add(client)
    text = client.get("/metrics").text
    assert "# TYPE stacks_http_requests_total counter" in text
    assert 'stacks_books_total{state="available"} 1' in text


# --------------------------------------------------------------- catalogue
def test_catalogue_starts_empty(client):
    assert client.get("/api/books").json() == []


def test_add_a_copy(client):
    book = _add(client)
    assert book["title"] == "The Pragmatic Programmer"
    assert book["state"] == "AVAILABLE"
    assert book["borrower"] is None
    assert book["overdue"] is False


def test_isbn_hyphens_are_normalised(client):
    book = _add(client, {**PRAGMATIC, "isbn": "978-0-13-595705-9"})
    assert book["isbn"] == "9780135957059"


def test_a_bad_isbn_is_rejected(client):
    response = client.post("/api/books", json={**PRAGMATIC, "isbn": "not-an-isbn"})
    assert response.status_code == 422


def test_a_blank_title_is_rejected(client):
    response = client.post("/api/books", json={**PRAGMATIC, "title": ""})
    assert response.status_code == 422


def test_the_same_isbn_cannot_be_shelved_twice(client):
    _add(client)
    response = client.post("/api/books", json=PRAGMATIC)
    assert response.status_code == 409
    assert "already shelved" in response.json()["detail"]


def test_get_one_and_404(client):
    book = _add(client)
    assert client.get(f"/api/books/{book['id']}").json()["isbn"] == PRAGMATIC["isbn"]
    assert client.get("/api/books/9999").status_code == 404


# ------------------------------------------------------------------ loans
def test_lending_sets_a_borrower_and_a_due_date(client):
    book = _add(client)
    lent = client.put(f"/api/books/{book['id']}", json={"state": "BORROWED", "borrower": "Hemang"})
    assert lent.status_code == 200
    body = lent.json()
    assert body["state"] == "BORROWED"
    assert body["borrower"] == "Hemang"
    # the default loan period is 14 days
    assert body["due_date"] == str(date.today() + timedelta(days=14))


def test_lending_without_a_borrower_is_rejected(client):
    book = _add(client)
    response = client.put(f"/api/books/{book['id']}", json={"state": "BORROWED"})
    assert response.status_code == 422


def test_a_copy_cannot_be_lent_twice(client):
    book = _add(client)
    client.put(f"/api/books/{book['id']}", json={"state": "BORROWED", "borrower": "Hemang"})
    second = client.put(f"/api/books/{book['id']}", json={"state": "BORROWED", "borrower": "Asha"})
    assert second.status_code == 409
    assert "already on loan" in second.json()["detail"]


def test_returning_clears_the_loan(client):
    book = _add(client)
    client.put(f"/api/books/{book['id']}", json={"state": "BORROWED", "borrower": "Hemang"})
    returned = client.put(f"/api/books/{book['id']}", json={"state": "AVAILABLE"}).json()
    assert returned["state"] == "AVAILABLE"
    assert returned["borrower"] is None
    assert returned["due_date"] is None


def test_overdue_is_derived_from_the_due_date(client):
    book = _add(client)
    yesterday = str(date.today() - timedelta(days=1))
    lent = client.put(
        f"/api/books/{book['id']}",
        json={"state": "BORROWED", "borrower": "Hemang", "due_date": yesterday},
    ).json()
    # nothing wrote an "OVERDUE" state - it is computed
    assert lent["state"] == "BORROWED"
    assert lent["overdue"] is True


# ------------------------------------------------------------------ stats
def test_stats_counts_each_state(client):
    first = _add(client)
    second = _add(client, SICP)
    client.put(f"/api/books/{first['id']}", json={"state": "BORROWED", "borrower": "Hemang"})
    client.put(
        f"/api/books/{second['id']}",
        json={
            "state": "BORROWED",
            "borrower": "Asha",
            "due_date": str(date.today() - timedelta(days=3)),
        },
    )
    stats = client.get("/api/books/stats").json()
    assert stats == {"total": 2, "available": 0, "borrowed": 2, "overdue": 1}


def test_stats_route_is_not_shadowed_by_the_id_route(client):
    """/api/books/stats must not be parsed as /api/books/{book_id}."""
    assert client.get("/api/books/stats").status_code == 200


# --------------------------------------------------------------- withdraw
def test_withdraw_a_copy(client):
    book = _add(client)
    assert client.delete(f"/api/books/{book['id']}").status_code == 204
    assert client.get(f"/api/books/{book['id']}").status_code == 404


def test_a_copy_on_loan_cannot_be_withdrawn(client):
    book = _add(client)
    client.put(f"/api/books/{book['id']}", json={"state": "BORROWED", "borrower": "Hemang"})
    response = client.delete(f"/api/books/{book['id']}")
    assert response.status_code == 409
    assert "on loan" in response.json()["detail"]


def test_probe_503s_are_not_counted_as_application_errors(client, monkeypatch):
    """A readiness 503 during startup must not page anyone."""
    from app import db as database
    from app.main import _metrics

    before_err = _metrics["errors_total"]
    before_nr = _metrics["not_ready_total"]

    monkeypatch.setattr(database, "database_reachable", lambda: False)
    assert client.get("/ready").status_code == 503

    assert _metrics["errors_total"] == before_err        # unchanged
    assert _metrics["not_ready_total"] == before_nr + 1  # counted separately
