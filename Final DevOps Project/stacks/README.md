# Stacks

**Name:** Hemang · **Enrollment number:** 24bcs10209

A task-management application built as the DevOps final capstone. The application itself is
deliberately small; the point is the pipeline around it — from a commit to a scanned image in a
registry to a running, autoscaling, monitored Kubernetes deployment.

---

## What the application does

Stacks lets you create, list, update, complete and delete tasks. A React single-page app
talks to a FastAPI backend, which persists to PostgreSQL through SQLAlchemy, with the schema
managed by Alembic migrations.

```text
Browser ──► React SPA (nginx)  ──/api──►  FastAPI  ──►  PostgreSQL
            port 8080                      port 8000       port 5432
```

nginx proxies `/api` to the backend, so the browser only ever sees **one origin** — no CORS in
production.

### API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | **Liveness.** Process only — never touches the database |
| `GET` | `/ready` | **Readiness.** *Does* check the database |
| `GET` | `/metrics` | Prometheus exposition format |
| `GET` | `/api/tasks` | List all tasks |
| `POST` | `/api/tasks` | Create a task |
| `GET` | `/api/tasks/{id}` | Fetch one task |
| `PUT` | `/api/tasks/{id}` | Update title, description or done |
| `DELETE` | `/api/tasks/{id}` | Delete a task |

> **Why `/health` must not check the database:** if it did, a slow database would fail liveness
> on every pod, Kubernetes would restart them all, and the reconnect storm would deepen the
> outage. `/ready` checks the database so an unhealthy pod is pulled out of Service endpoints
> *without* being restarted.

---

## Layout

```text
stacks/
├── backend/           FastAPI + SQLAlchemy + Alembic, pytest, Dockerfile
│   ├── app/           config, db, models, schemas, main
│   ├── alembic/       env.py + versions/0001_create_tasks.py
│   └── tests/         12 tests against a throwaway SQLite DB
├── frontend/          React + Vite, nginx.conf, multi-stage Dockerfile
├── docker-compose.yml postgres + backend + frontend
├── k8s/               namespace
├── helm/stacks/    chart: backend, frontend, postgres, ingress, HPA, SM
├── terraform/         VPC + 2 public subnets + EKS + managed node group
├── monitoring/        kube-prometheus-stack values + Grafana dashboard
├── troubleshooting/   two deliberately broken manifests
└── scripts/           load-test.sh
```

CI lives at [`.github/workflows/stacks.yml`](../../.github/workflows/stacks.yml), which
must sit at the repository root.

---

## Run it locally

```bash
docker compose up --build
```

| | |
|---|---|
| Frontend | <http://localhost:8080> |
| Backend | <http://localhost:8000> |
| API docs | <http://localhost:8000/docs> |

The backend runs `alembic upgrade head` before starting, so the schema is created on first boot.

```bash
curl localhost:8000/health
curl -X POST -H 'Content-Type: application/json' \
     -d '{"title":"first task"}' localhost:8000/api/tasks
curl localhost:8000/api/tasks
```

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest --cov=app
```

12 tests, 95% coverage. They use a temporary **SQLite** database — never Postgres — so they are
isolated and need no running services.

## Deploy to Kubernetes

```bash
kubectl apply -f k8s/namespace.yaml

helm upgrade --install stacks helm/stacks -n stacks --wait
# or an environment overlay:
helm upgrade --install stacks helm/stacks -n stacks -f helm/stacks/values-prod.yaml

kubectl get pods,svc,ingress,hpa -n stacks
```

Add `stacks.local` to `/etc/hosts` pointing at the ingress IP, then visit it. The chart runs
Alembic in an init container, so a fresh database is migrated automatically.

## Infrastructure

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform plan
terraform apply          # use_localstack = false targets real AWS
```

Provisions a VPC, two public subnets in two availability zones, an internet gateway and routing,
plus an EKS cluster with a managed node group and the IAM roles they need.

## Monitoring

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace -f monitoring/prometheus-values.yaml
kubectl apply -f monitoring/grafana-dashboard.yaml -n monitoring
```

Backend pods carry `prometheus.io/scrape` annotations, so Prometheus discovers them
automatically. The bundled dashboard shows request rate, latency, task count and pods up.

---

## Technology

| Layer | Choice |
|---|---|
| Frontend | React 18, Vite 5, nginx |
| Backend | FastAPI, Uvicorn, SQLAlchemy 2, Pydantic v2 |
| Database | PostgreSQL 16, Alembic migrations |
| Containers | Multi-stage Dockerfiles, **non-root** in both |
| Orchestration | Kubernetes, Helm |
| Infrastructure | Terraform, AWS VPC + EKS |
| CI/CD | GitHub Actions, GHCR, images tagged by commit SHA |
| Security | bandit, pip-audit, gitleaks, Trivy, hardened `securityContext` |
| Observability | Prometheus, Grafana |

---

## Security notes

- Both images run as **non-root** (uid 10001 backend, 10002 frontend).
- The backend container runs with `readOnlyRootFilesystem`, `drop: ["ALL"]` and
  `allowPrivilegeEscalation: false`.
- Trivy gates the pipeline on **fixable** HIGH/CRITICAL in **both** images. Two real findings
  were fixed rather than suppressed: FastAPI was upgraded to patch three starlette CVEs, and the
  frontend image runs `apk upgrade` to pick up patched OpenSSL.
- `.env` is gitignored; only `.env.example` is committed. The Helm chart's demo credentials
  belong in Sealed Secrets or the External Secrets Operator in production.
