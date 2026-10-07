"""Unit tests run by the CI pipeline.
Name: Hemang | Enrollment number: 24bcs10209
"""
import pytest

from app import db
from app.main import app as flask_app


@pytest.fixture(autouse=True)
def _clean():
    db._mem.clear()
    db._next_id[0] = 1
    yield


@pytest.fixture
def client():
    flask_app.config.update(TESTING=True)
    with flask_app.test_client() as c:
        yield c


def test_health_is_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_ready_is_ok_with_memory_store(client):
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ready"


def test_metrics_exposes_prometheus_format(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "taskboard_requests_total" in body
    assert "# TYPE taskboard_requests_total counter" in body


def test_create_and_list_task(client):
    created = client.post("/api/tasks", json={"title": "write the capstone"})
    assert created.status_code == 201
    assert created.get_json()["title"] == "write the capstone"

    listed = client.get("/api/tasks").get_json()["tasks"]
    assert len(listed) == 1
    assert listed[0]["done"] is False


def test_create_task_rejects_empty_title(client):
    r = client.post("/api/tasks", json={"title": "   "})
    assert r.status_code == 400
    assert "required" in r.get_json()["error"]


def test_complete_task(client):
    tid = client.post("/api/tasks", json={"title": "ship it"}).get_json()["id"]
    r = client.post(f"/api/tasks/{tid}/complete")
    assert r.status_code == 200
    assert r.get_json()["done"] is True


def test_complete_missing_task_is_404(client):
    r = client.post("/api/tasks/9999/complete")
    assert r.status_code == 404
