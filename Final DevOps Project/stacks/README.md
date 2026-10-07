# Stacks

**Name:** Hemang · **Enrollment number:** 24bcs10209

A small library lending desk, built as the DevOps final capstone. The application itself is
deliberately modest; the point is the pipeline around it — from a commit to a scanned image in a
registry to a running, autoscaling, monitored Kubernetes deployment.

The full write-up, with rubric mapping and captured evidence, is in the
[project README](../README.md).

---

## What the application does

Stacks keeps a catalogue of physical copies. Each copy is either **on the shelf** or **on loan**
to a named borrower with a due date, and a loan whose due date has passed reads as **overdue**.
A React single-page app talks to a FastAPI backend, which persists to PostgreSQL through
SQLAlchemy with the schema managed by Alembic.

```text
Browser ──► React SPA (nginx)  ──/api──►  FastAPI  ──►  PostgreSQL
            port 3000                      port 8000       port 5432
```

nginx proxies `/api` to the backend, so the browser only ever sees **one origin** — no CORS in
production.

### Three decisions worth knowing before reading the code

- **`overdue` is not stored.** It is derived from `due_date` on every read, so a loan becomes
  overdue by the passage of time rather than by something remembering to update a row.
- **ISBN is normalised and unique.** Hyphens are stripped on the way in, and the migration adds a
  `UNIQUE` constraint, so the duplicate check does not depend on the API being the only writer.
- **The rules are mostly refusals.** A copy on loan cannot be lent again and cannot be
  withdrawn; both answer `409`.

### API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | **Liveness.** Process only — never touches the database |
| `GET` | `/ready` | **Readiness.** *Does* check the database |
| `GET` | `/metrics` | Prometheus exposition format |
| `GET` | `/api/books` | The catalogue |
| `POST` | `/api/books` | Shelve a copy |
| `GET` | `/api/books/stats` | `{total, available, borrowed, overdue}` |
| `GET` | `/api/books/{id}` | One copy |
| `PUT` | `/api/books/{id}` | Correct the record, or **lend / return** |
| `DELETE` | `/api/books/{id}` | Withdraw a copy |

> **Why `/health` must not check the database:** if it did, a slow database would fail liveness
> on every pod, Kubernetes would restart them all, and the reconnect storm would deepen the
> outage. `/ready` checks the database so an unhealthy pod is pulled out of Service endpoints
> *without* being restarted.
>
> `/ready`'s deliberate 503 is counted in `stacks_not_ready_total`, **not**
> `stacks_http_errors_total` — otherwise every normal rollout spikes the error panel.

---

## Layout

```text
stacks/
├── backend/           FastAPI + SQLAlchemy + Alembic, pytest, Dockerfile
│   ├── app/           config, db, models, schemas, main
│   ├── alembic/       env.py + versions/0001_create_books.py
│   └── tests/         20 tests against a throwaway SQLite DB
├── frontend/          React + Vite, nginx.conf, multi-stage Dockerfile
├── docker-compose.yml postgres + backend + frontend
├── k8s/               namespace
├── helm/stacks/       chart: backend, frontend, postgres, ingress, HPA, SM
├── terraform/         VPC + 2 public subnets + EKS + managed node group
├── monitoring/        Prometheus + Grafana, and the dashboard ConfigMap
├── troubleshooting/   two deliberately broken manifests
└── scripts/           load-test.sh
```

CI lives at [`.github/workflows/stacks.yml`](../../.github/workflows/stacks.yml), which must sit
at the repository root.

---

## Run it locally

```bash
docker compose up --build
```

| | |
|---|---|
| Frontend | <http://localhost:3000> |
| Backend | <http://localhost:8000> |
| API docs | <http://localhost:8000/docs> |

The backend runs `alembic upgrade head` before starting, so the schema is created on first boot.

```bash
curl localhost:8000/health

curl -X POST -H 'Content-Type: application/json' \
     -d '{"title":"The Pragmatic Programmer","author":"Hunt & Thomas","isbn":"978-0-13-595705-9"}' \
     localhost:8000/api/books

curl -X PUT -H 'Content-Type: application/json' \
     -d '{"state":"BORROWED","borrower":"Hemang"}' localhost:8000/api/books/1

curl localhost:8000/api/books/stats
```

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest -v --cov=app
```

20 tests, 95% coverage. They use a temporary **SQLite** database — never Postgres — so they are
isolated and need no running services.

## Deploy to Kubernetes

```bash
kubectl apply -f k8s/namespace.yaml

helm upgrade --install stacks helm/stacks -n stacks --wait
# or an environment overlay:
helm upgrade --install stacks helm/stacks -n stacks -f helm/stacks/values-prod.yaml

kubectl get pods,svc,ingress,hpa -n stacks
```

Add `stacks.local` to `/etc/hosts` pointing at the ingress IP, then visit it. The chart waits for
Postgres and then runs Alembic in init containers, so a fresh database is migrated automatically.

## Infrastructure

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform plan
terraform apply          # use_localstack = false targets real AWS
```

Provisions a VPC, two public subnets in two availability zones, an internet gateway and routing,
plus an EKS cluster with a managed node group and the IAM roles they need. **Against LocalStack
the two EKS resources fail with HTTP 501** — its free tier does not implement EKS. The other 13
are created for real.

## Monitoring

```bash
kubectl apply -f monitoring/in-cluster-stack.yaml
kubectl apply -f monitoring/grafana-dashboard.yaml -n monitoring
kubectl -n monitoring port-forward svc/grafana 3131:3000
```

Backend pods carry `prometheus.io/scrape` annotations, so Prometheus discovers them
automatically. The bundled dashboard shows request rate, latency, pods up, errors, readiness
503s and the shelf over time.

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

- Both images run as **non-root** (uid 10001 backend, uid 10002 frontend). `runAsNonRoot: true`
  in the pod spec refuses to start a container whose user resolves to uid 0, so the Dockerfile
  and the manifest have to agree.
- The backend container runs with `readOnlyRootFilesystem`, `drop: ["ALL"]` and
  `allowPrivilegeEscalation: false`.
- Trivy gates the pipeline on **fixable** HIGH/CRITICAL in **both** images, and the push job is
  downstream of the scan, so a failing image never reaches the registry. The frontend is clean
  because of `apk upgrade --no-cache` — without it the published `nginx:1.27-alpine` tag reports
  dozens of fixable HIGH findings.
- `.env` is gitignored; only `.env.example` is committed. The Helm chart's demo credentials
  belong in Sealed Secrets or the External Secrets Operator in production.
