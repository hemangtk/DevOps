# Final DevOps Project — TaskBoard

**Name:** Hemang
**Enrollment number:** 24bcs10209

Session 21. The capstone: one application carried from source code to a monitored, autoscaling,
GitOps-managed Kubernetes deployment — using every tool from the previous twenty sessions.

Project: [`final-devops-project/`](final-devops-project/)

---

## 1. Overview

**TaskBoard** is a small task API with a web front page. It is deliberately simple so the
*pipeline around it* is the interesting part.

| Layer | Technology |
|---|---|
| Application | Python 3.12, Flask, psycopg |
| Database | PostgreSQL 16, with a PersistentVolumeClaim |
| Container | Multi-stage Dockerfile, non-root, 254 MB |
| Orchestration | Kubernetes — Deployment, Service, ConfigMap, Secret, Ingress, HPA, PVC, NetworkPolicy |
| Packaging | Helm chart |
| Infrastructure | Terraform (LocalStack) |
| CI/CD | GitHub Actions |
| Security | bandit, pip-audit, gitleaks, Trivy, hardened `securityContext` |
| Monitoring | `/metrics` in Prometheus exposition format |
| GitOps | ArgoCD |

---

## 2. Architecture

```text
   Developer ──push──► GitHub ──► GitHub Actions
                          │         ├── lint + pytest
                          │         ├── SAST / SCA / secret scan
                          │         ├── docker build + smoke test + Trivy
                          │         ├── kubeconform + helm lint
                          │         └── RELEASE GATE ──► ArgoCD
                          │                                 │ pulls
                          └─────────────────────────────────┘
                                                            ▼
┌──────────────────────── Kubernetes namespace: taskboard ────────────────────┐
│                                                                             │
│   Ingress (nginx)  taskboard.local ──► Service taskboard :80                │
│                                              │                              │
│                                   ┌──────────▼──────────┐                   │
│                                   │ Deployment taskboard│  HPA 2→8 @60% CPU │
│                                   │  initContainer: wait-for-postgres       │
│                                   │  startup + readiness + liveness probes  │
│                                   │  runAsNonRoot, readOnlyRootFilesystem   │
│                                   │  ConfigMap + Secret → env               │
│                                   └──────────┬──────────┘                   │
│                                              │ NetworkPolicy: only this app │
│                                   ┌──────────▼──────────┐                   │
│                                   │ Service postgres    │                   │
│                                   │ Deployment postgres │                   │
│                                   │   PVC postgres-data │ 1Gi RWO           │
│                                   └─────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Repository layout

```text
final-devops-project/
├── application/     Flask app, tests, requirements
├── docker/          multi-stage Dockerfile
├── kubernetes/      00-namespace … 07-networkpolicy
├── helm/taskboard/  chart
├── terraform/       S3 artifact bucket
├── security/        the control inventory
├── monitoring/      Prometheus scrape config
├── gitops/          ArgoCD Application
└── (CI lives at .github/workflows/capstone.yml, which must be at the repo root)
```

---

## 3. The application

Three endpoints matter beyond the API itself, and the split between them is deliberate:

```python
@app.route("/health")      # LIVENESS - process only. Does NOT touch the database.
@app.route("/ready")       # READINESS - DOES check the database.
@app.route("/metrics")     # Prometheus exposition format
```

> **Why `/health` must not check the database:** if it did, a slow or restarting database would
> fail liveness on every pod, Kubernetes would restart them all, and the reconnect storm would
> make the outage worse. Section 7 demonstrates exactly this, and shows the correct behaviour.

Tests and lint pass locally before anything is pushed:

```console
$ flake8 app tests --max-line-length=100
clean

$ pytest --cov=app
tests/test_api.py::test_health_is_ok PASSED
tests/test_api.py::test_ready_is_ok_with_memory_store PASSED
tests/test_api.py::test_metrics_exposes_prometheus_format PASSED
tests/test_api.py::test_create_and_list_task PASSED
tests/test_api.py::test_create_task_rejects_empty_title PASSED
tests/test_api.py::test_complete_task PASSED
tests/test_api.py::test_complete_missing_task_is_404 PASSED
============================== 7 passed in 0.60s ===============================
```

---

## 4. Docker

A multi-stage build that compiles dependency wheels in one stage and ships only the installed
packages in the next, with a non-root user because the Kubernetes `securityContext` demands one:

```dockerfile
FROM python:3.12-slim AS build
RUN pip wheel --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin taskboard
COPY --from=build /wheels /wheels
RUN pip install --no-index --find-links=/wheels -r requirements.txt && rm -rf /wheels
USER 10001
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')"
```

```console
$ docker build -f docker/Dockerfile --build-arg APP_VERSION=1.0.0 -t taskboard:1.0.0 .
REPOSITORY   TAG       SIZE
taskboard    1.0.0     254MB
```

---

## 5. Kubernetes deployment

```console
$ kubectl apply -f kubernetes/
namespace/taskboard created
configmap/taskboard-config created
secret/taskboard-secret created
persistentvolumeclaim/postgres-data created
deployment.apps/postgres created
service/postgres created
deployment.apps/taskboard created
service/taskboard created
horizontalpodautoscaler.autoscaling/taskboard created
ingress.networking.k8s.io/taskboard created
networkpolicy.networking.k8s.io/postgres-allow-app-only created
```

Everything running:

```console
$ kubectl get all,pvc,configmap,secret,ingress,hpa,networkpolicy -n taskboard
pod/postgres-fbd8c8ff-tc8rs      1/1   Running
pod/taskboard-659779dbc7-2xhzr   1/1   Running
pod/taskboard-659779dbc7-r627x   1/1   Running
service/postgres    ClusterIP   10.109.221.22    5432/TCP
service/taskboard   ClusterIP   10.106.193.155   80/TCP
deployment.apps/postgres    1/1
deployment.apps/taskboard   2/2
hpa/taskboard                Deployment/taskboard   cpu: <unknown>/60%   2   8   2
pvc/postgres-data            Bound   pvc-f89c1dfb...   1Gi   RWO   standard
configmap/taskboard-config   3
secret/taskboard-secret      Opaque   2
ingress/taskboard            nginx   taskboard.local   192.168.49.2   80
networkpolicy/postgres-allow-app-only   app=postgres
```

### The init container sequenced the startup

```console
$ kubectl logs <pod> -c wait-for-postgres
postgres:5432 - no response
waiting for postgres...
postgres:5432 - no response
waiting for postgres...
postgres:5432 - accepting connections
postgres is ready
```

### ConfigMap and Secret reached the container

```console
$ kubectl exec <pod> -c api -- printenv ENVIRONMENT LOG_LEVEL POSTGRES_DB POSTGRES_USER
production
INFO
taskboard
taskboard

$ kubectl exec <pod> -c api -- sh -c 'echo $DATABASE_URL | sed "s|:[^:@]*@|:***@|"'
postgresql://taskboard:***@postgres:5432/taskboard
```

The password is never printed — the `DATABASE_URL` is assembled from a ConfigMap key and two
Secret keys using `$(VAR)` interpolation.

### Probes

```console
$ kubectl exec <pod> -c api -- curl -s localhost:8000/health
{"status":"ok","uptime_s":2.2,"version":"1.0.0"}

$ kubectl exec <pod> -c api -- curl -s localhost:8000/ready
{"status":"ready","store":"postgres"}
```

`store: postgres` confirms the app is genuinely talking to the database, not falling back to its
in-memory store.

![full stack deployed](screenshots/deploy-full-stack.png)

---

## 6. End to end, through the Ingress

```console
$ curl -X POST -H 'Host: taskboard.local' -d '{"title":"Finish the DevOps capstone"}' http://<node>/api/tasks
{"done":false,"id":1,"title":"Finish the DevOps capstone"}
{"done":false,"id":2,"title":"Submit the form"}
{"done":false,"id":3,"title":"Tear down the cluster"}

$ curl -H 'Host: taskboard.local' http://<node>/api/tasks
{"tasks":[{"done":false,"id":1,...},{"done":false,"id":2,...},{"done":false,"id":3,...}]}

$ curl -X POST -H 'Host: taskboard.local' http://<node>/api/tasks/1/complete
{"done":true,"id":1,"title":"Finish the DevOps capstone"}
```

The rendered page:

```html
<h1>TaskBoard</h1>
version 1.0.0
<li class="done">#1 Finish the DevOps capstone</li>
<li class="">#2 Submit the form</li>
<li class="">#3 Tear down the cluster</li>
```

### Metrics

```console
$ curl -H 'Host: taskboard.local' http://<node>/metrics
# HELP taskboard_requests_total Total HTTP requests served.
# TYPE taskboard_requests_total counter
taskboard_requests_total{version="1.0.0"} 14
# TYPE taskboard_errors_total counter
taskboard_errors_total{version="1.0.0"} 0
# TYPE taskboard_uptime_seconds gauge
taskboard_uptime_seconds 23.3
# TYPE taskboard_tasks gauge
taskboard_tasks 3
```

### Storage really persists

```console
$ kubectl get pods -l app=postgres
postgres-fbd8c8ff-tc8rs   Running

$ kubectl delete pod postgres-fbd8c8ff-tc8rs -n taskboard
pod deleted

$ kubectl get pods -l app=postgres
postgres-fbd8c8ff-xptdq   Running          ← different pod

$ curl -H 'Host: taskboard.local' http://<node>/api/tasks
{"tasks":[{"done":true,"id":1,...},{"done":false,"id":2,...},{"done":false,"id":3,...}]}
```

**The database pod was destroyed and the data survived** — including task 1's completed state.
That is the PVC doing its job.

![end to end and persistence](screenshots/end-to-end-and-persistence.png)

---

## 7. Troubleshooting challenge

### Break 1 — wrong database password in the Secret

```console
$ kubectl patch secret taskboard-secret -p '{"stringData":{"POSTGRES_PASSWORD":"wrong-password"}}'
$ kubectl rollout restart deployment/taskboard -n taskboard

$ kubectl get pods -l app=taskboard
taskboard-597fb5c658-zw8fd   0/1   CrashLoopBackOff   restarts=3    ← the new pod
taskboard-659779dbc7-2xhzr   1/1   Running            restarts=0    ← old, still serving
taskboard-659779dbc7-r627x   1/1   Running            restarts=0    ← old, still serving

$ kubectl get events --field-selector reason=Unhealthy
Startup probe failed: Get "http://10.244.0.101:8000/health": connect: connection refused

$ kubectl get endpoints taskboard        # still the two OLD pods
taskboard   10.244.0.98:8000,10.244.0.99:8000
ingress -> HTTP 200                      # users never noticed
```

> **I expected this to produce "Running but not Ready" and it did not** — the app calls
> `db.init()` before binding its port, so a bad password kills the process outright and the
> **startup** probe fails with `connection refused`.
>
> The more interesting result is what *didn't* happen: **the service never went down.**
> `strategy.rollingUpdate.maxUnavailable: 0` means Kubernetes refuses to retire a healthy old
> pod until a new one reports Ready. The broken pod never did, so the old ones kept serving and
> the rollout simply stalled. A bad config became a stuck deployment instead of an outage.

Fixing the Secret and restarting recovered cleanly, with the data intact.

### Break 2 — the database disappears

This is the one that isolates readiness from liveness:

```console
$ kubectl scale deployment/postgres -n taskboard --replicas=0
deployment.apps/postgres scaled

$ kubectl get pods
taskboard-78c8988cfb-nn6dp   ready=0/1   Running   restarts=0
taskboard-78c8988cfb-qtd7g   ready=0/1   Running   restarts=0
```

**Running. Not Ready. Zero restarts.** Asking both probe endpoints directly:

```console
GET /health ->  200 {"status":"ok","uptime_s":...,"version":"1.0.0"}
GET /ready  ->  503 {"reason":"datastore unreachable","status":"not-ready"}

$ kubectl get events --field-selector reason=Unhealthy
10   Readiness probe failed: HTTP probe failed with statuscode: 503
```

The consequence:

```console
$ kubectl get endpoints taskboard
taskboard   <empty>

ingress -> HTTP 503          # no healthy backends
restarts: 0                  # nothing was killed
```

And the recovery:

```console
$ kubectl scale deployment/postgres -n taskboard --replicas=1

$ kubectl get pods
postgres-fbd8c8ff-mkv96      ready=1/1   Running   restarts=0
taskboard-78c8988cfb-nn6dp   ready=1/1   Running   restarts=0
taskboard-78c8988cfb-qtd7g   ready=1/1   Running   restarts=0

ingress -> HTTP 200
{"tasks":[{"done":true,"id":1,...}, ...]}      # data intact
```

**The app recovered on its own with zero restarts.** Had `/health` checked the database, both
pods would have been in `CrashLoopBackOff` instead — restarting repeatedly, losing warm state,
and hammering the database the moment it came back. This is the single clearest demonstration in
the whole coursework of why the two probes exist separately.

![troubleshooting](screenshots/troubleshooting.png)

---

## 8. CI/CD and DevSecOps

[`.github/workflows/capstone.yml`](../.github/workflows/capstone.yml):

```text
test ─────┐
security ─┼──► gate ──► (deploy)
image ────┤
manifests ┘
```

| Job | Does |
|---|---|
| **test** | flake8 + pytest with coverage |
| **security** | bandit (SAST), pip-audit (SCA), gitleaks (secrets, full history) |
| **image** | Build, smoke-test the running container, Trivy scan gating on fixable CRITICAL |
| **manifests** | `kubeconform -strict` on the YAML, `helm lint` on the chart |
| **gate** | Fails unless all four succeeded — deploy cannot run otherwise |

The security controls are inventoried in
[`final-devops-project/security/README.md`](final-devops-project/security/), including an honest
note about the one real gap: the Secret manifest is committed, which production would replace
with Sealed Secrets or an external secret store.

---

## 9. Helm and Terraform

```console
$ helm lint helm/taskboard
1 chart(s) linted, 0 chart(s) failed
```

Terraform provisions an S3 artifact bucket with versioning and public access blocked, targeting
LocalStack exactly as in [Session 18](../Terraform%20and%20IaC/) and
[Session 19](../Cloud%20and%20Terraform%20in%20Action/).

---

## 10. GitOps

[`final-devops-project/gitops/argocd-application.yaml`](final-devops-project/gitops/) points
ArgoCD at `Final DevOps Project/final-devops-project/kubernetes` in this repository, with
`prune: true` and `selfHeal: true` — the same mechanism proven in
[Session 20](../Monitoring%20Observability%20and%20GitOps/#task-3--gitops), where a manual scale
was reverted in under a second.

---

## 11. Reproduce

```bash
minikube start --cpus=4 --memory=4096
minikube addons enable ingress metrics-server default-storageclass

cd final-devops-project
docker build -f docker/Dockerfile --build-arg APP_VERSION=1.0.0 -t taskboard:1.0.0 .
minikube image load taskboard:1.0.0

kubectl apply -f kubernetes/
kubectl rollout status deployment/postgres  -n taskboard
kubectl rollout status deployment/taskboard -n taskboard

minikube ssh -- "curl -s -H 'Host: taskboard.local' http://localhost/api/tasks"

# troubleshooting
kubectl scale deployment/postgres -n taskboard --replicas=0    # watch readiness fail
kubectl scale deployment/postgres -n taskboard --replicas=1    # watch it recover

kubectl delete namespace taskboard
```

---

## 12. Lessons learned

1. **The probe split is not academic.** Taking the database away produced `Running, 0/1 Ready,
   0 restarts` and automatic recovery. A liveness probe that checked the database would have
   turned a dependency outage into a cluster-wide restart loop.
2. **`maxUnavailable: 0` saved a release.** A broken Secret produced a *stalled rollout* instead
   of an outage, because Kubernetes would not retire healthy pods for one that never became
   Ready.
3. **Init containers make ordering explicit.** The app never saw a connection error at startup
   because `wait-for-postgres` had already proven the database was accepting connections.
4. **State is the thing that needs care.** Everything else in this stack is disposable; the PVC
   is what made deleting the database pod a non-event.
5. **Gates only matter if something downstream depends on them.** `needs: [gate]` is the line
   that turns scanning into enforcement.
6. **Writing the health endpoints is an application concern.** No amount of Kubernetes
   configuration can fix an app that cannot say whether it is ready.
7. **Verify at the layer you care about.** `kubectl get pods` showing `Running` meant very little;
   `curl` through the Ingress returning real JSON from Postgres meant everything.
