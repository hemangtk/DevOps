"""API tests - covers /health, /ready, /metrics and the full task CRUD.
Name: Hemang | Enrollment number: 24bcs10209
"""


def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"


def test_ready_reports_database_reachable(client):
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json()["database"] == "reachable"


def test_metrics_is_prometheus_format(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.text
    assert "# TYPE taskboard_http_requests_total counter" in body
    assert "taskboard_tasks_total" in body


def test_create_task(client):
    r = client.post("/api/tasks", json={"title": "write the capstone", "description": "to spec"})
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "write the capstone"
    assert body["done"] is False
    assert body["id"] >= 1


def test_create_task_rejects_empty_title(client):
    r = client.post("/api/tasks", json={"title": ""})
    assert r.status_code == 422          # pydantic validation


def test_list_tasks(client):
    client.post("/api/tasks", json={"title": "one"})
    client.post("/api/tasks", json={"title": "two"})
    r = client.get("/api/tasks")
    assert r.status_code == 200
    assert [t["title"] for t in r.json()] == ["one", "two"]


def test_get_single_task(client):
    tid = client.post("/api/tasks", json={"title": "find me"}).json()["id"]
    r = client.get(f"/api/tasks/{tid}")
    assert r.status_code == 200
    assert r.json()["title"] == "find me"


def test_get_missing_task_is_404(client):
    r = client.get("/api/tasks/9999")
    assert r.status_code == 404
    assert "not found" in r.json()["detail"]


def test_update_task(client):
    tid = client.post("/api/tasks", json={"title": "old"}).json()["id"]
    r = client.put(f"/api/tasks/{tid}", json={"title": "new", "done": True})
    assert r.status_code == 200
    assert r.json()["title"] == "new"
    assert r.json()["done"] is True


def test_update_missing_task_is_404(client):
    r = client.put("/api/tasks/9999", json={"done": True})
    assert r.status_code == 404


def test_delete_task(client):
    tid = client.post("/api/tasks", json={"title": "remove me"}).json()["id"]
    assert client.delete(f"/api/tasks/{tid}").status_code == 204
    assert client.get(f"/api/tasks/{tid}").status_code == 404


def test_delete_missing_task_is_404(client):
    assert client.delete("/api/tasks/9999").status_code == 404
