# Kubernetes Pods, ReplicaSets and Deployments

**Name:** Hemang
**Enrollment number:** 24bcs10209

Core workload objects and the four deployment strategies, all run on a real minikube cluster
(Kubernetes v1.37.0) in the `k8s-lab` namespace.

| Section | Covers |
|---|---|
| [1](#1-the-hierarchy) | Deployment → ReplicaSet → Pod, and ownership |
| [2](#2-self-healing) | Killing a Pod and watching it come back |
| [3](#3-scaling) | Scaling up and down |
| [4](#4-rolling-update) | Rolling update, rollout history, rollback |
| [5](#5-recreate) | Recreate strategy and its downtime |
| [6](#6-blue-green) | Blue-green cutover via a Service selector |
| [7](#7-canary) | Canary release and promotion |
| [8](#8-pod-lifecycle) | Init containers, readiness, liveness, phases |

Manifests: [`manifests/`](manifests/)

---

## 1. The hierarchy

Three objects, three jobs:

```text
Deployment    "I manage versions and rollouts."
    │          Creates a NEW ReplicaSet for each change to the pod template.
    ▼
ReplicaSet    "I keep exactly N pods alive."
    │          Does nothing about versions — only counting.
    ▼
Pod           "I run containers."
               Disposable. Never created directly in production.
```

[`manifests/deployment.yaml`](manifests/deployment.yaml):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: k8s-lab
spec:
  replicas: 3
  selector:
    matchLabels:          # how the Deployment finds the Pods it owns
      app: web
  template:               # everything below is a Pod spec
    metadata:
      labels:
        app: web          # MUST match spec.selector.matchLabels
    spec:
      containers:
        - name: nginx
          image: nginx:1.25-alpine
          ports:
            - containerPort: 80
          resources:
            requests: { cpu: "10m",  memory: "16Mi" }
            limits:   { cpu: "200m", memory: "128Mi" }
```

```console
$ kubectl apply -f manifests/deployment.yaml
deployment.apps/web created

$ kubectl rollout status deployment/web -n k8s-lab
Waiting for deployment "web" rollout to finish: 0 of 3 updated replicas are available...
deployment "web" successfully rolled out

$ kubectl get deployment,replicaset,pod -n k8s-lab -l app=web
NAME                  READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/web   3/3     3            3           11s

NAME                             DESIRED   CURRENT   READY   AGE
replicaset.apps/web-799d74cf5c   3         3         3       11s

NAME                       READY   STATUS    RESTARTS   AGE
pod/web-799d74cf5c-54mp9   1/1     Running   0          11s
pod/web-799d74cf5c-6kchs   1/1     Running   0          11s
pod/web-799d74cf5c-v844w   1/1     Running   0          11s
```

I created **one** object and got three. The ownership chain is real and queryable:

```console
$ kubectl get rs -n k8s-lab -l app=web -o jsonpath='...ownerReferences...'
web-799d74cf5c <- owned by Deployment/web

$ kubectl get pods -n k8s-lab -l app=web -o jsonpath='...ownerReferences...'
web-799d74cf5c-54mp9 <- owned by ReplicaSet/web-799d74cf5c
web-799d74cf5c-6kchs <- owned by ReplicaSet/web-799d74cf5c
web-799d74cf5c-v844w <- owned by ReplicaSet/web-799d74cf5c
```

The `799d74cf5c` in the ReplicaSet name is a **hash of the pod template**. Change the template
and you get a different hash, hence a different ReplicaSet — which is exactly how rollbacks
work later on.

> **The label selector is the one thing to get right.** `spec.selector.matchLabels` must match
> `spec.template.metadata.labels`, or the API rejects the Deployment. Labels are the only way
> these objects find each other; there are no pointers.

---

## 2. Self-healing

```console
--- before ---
web-799d74cf5c-54mp9 Running 11s
web-799d74cf5c-6kchs Running 11s
web-799d74cf5c-v844w Running 11s

$ kubectl delete pod web-799d74cf5c-54mp9 -n k8s-lab
pod "web-799d74cf5c-54mp9" deleted from k8s-lab namespace

--- after ---
web-799d74cf5c-6kchs Running 19s
web-799d74cf5c-rltq5 Running 8s     <-- NEW pod, 8s old
web-799d74cf5c-v844w Running 19s

$ kubectl get deployment/web -n k8s-lab
NAME   READY   UP-TO-DATE   AVAILABLE   AGE
web    3/3     3            3           19s
```

Still 3/3. The ReplicaSet controller saw 2 pods where its spec says 3 and created one — note
the replacement has a **different name** (`rltq5`, age 8s). It is not the old pod restarted; it
is a brand new one.

### Compare with a bare Pod

```console
$ kubectl run orphan --image=nginx:alpine -n k8s-lab
pod/orphan created

$ kubectl delete pod orphan -n k8s-lab
pod "orphan" deleted from k8s-lab namespace

$ kubectl get pod orphan -n k8s-lab
Error from server (NotFound): pods "orphan" not found
```

Gone for good. **Self-healing is a property of the controller, not of Pods.** This is the whole
argument for never deploying a bare Pod.

---

## 3. Scaling

```console
$ kubectl scale deployment/web -n k8s-lab --replicas=6
deployment.apps/web scaled

$ kubectl get deployment/web -n k8s-lab
NAME   READY   UP-TO-DATE   AVAILABLE   AGE
web    6/6     6            6           28s

$ kubectl get rs -n k8s-lab -l app=web
web-799d74cf5c desired=6 current=6 ready=6

$ kubectl scale deployment/web -n k8s-lab --replicas=2
deployment.apps/web scaled

$ kubectl get deployment/web -n k8s-lab
NAME   READY   UP-TO-DATE   AVAILABLE   AGE
web    2/2     2            2           36s
```

Scaling changes **one number**. No new ReplicaSet appears, because the pod template didn't
change — the same ReplicaSet just has a new target.

![hierarchy, self-healing and scaling](screenshots/deployment-hierarchy-selfheal.png)

---

## 4. Rolling update

The default strategy: replace pods a few at a time so the service never fully goes down.

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 1   # at most 1 pod down at a time
    maxSurge: 1         # at most 1 extra pod above replicas
```

With `replicas: 4`, that means between 3 and 5 pods exist at any moment, and at least 3 are
always serving.

```console
$ kubectl get deploy web-rolling -n k8s-lab -o jsonpath='{.spec.strategy...}'
RollingUpdate maxUnavailable=1 maxSurge=1

$ kubectl set image deployment/web-rolling nginx=nginx:1.27-alpine -n k8s-lab
deployment.apps/web-rolling image updated
```

**Both versions are alive at the same time** during the roll:

```console
  t+1s:  web-rolling-548d57497b-lgdg7(ContainerCreating)   <- new
         web-rolling-548d57497b-nksvk(ContainerCreating)   <- new
         web-rolling-5c848dcfdb-6mf4w(Running)             <- old
         web-rolling-5c848dcfdb-94rrx(Running)             <- old
         web-rolling-5c848dcfdb-9hgdd(Running)             <- old
         web-rolling-5c848dcfdb-zv5d6(Terminating)         <- old, going away
```

`rollout status` narrates the whole thing:

```console
$ kubectl rollout status deployment/web-rolling -n k8s-lab
Waiting for deployment "web-rolling" rollout to finish: 2 out of 4 new replicas have been updated...
Waiting for deployment "web-rolling" rollout to finish: 3 out of 4 new replicas have been updated...
Waiting for deployment "web-rolling" rollout to finish: 1 old replicas are pending termination...
deployment "web-rolling" successfully rolled out
```

### Two ReplicaSets, one active

```console
$ kubectl get rs -n k8s-lab -l app=web-rolling
RS                       DESIRED   READY    IMAGE
web-rolling-548d57497b   4         4        nginx:1.27-alpine
web-rolling-5c848dcfdb   0         <none>   nginx:1.25-alpine
```

The old ReplicaSet isn't deleted — it is **scaled to 0 and kept**. That is what makes rollback
instant.

### Rollback

```console
$ kubectl rollout history deployment/web-rolling -n k8s-lab
REVISION  CHANGE-CAUSE
1         <none>
2         <none>

$ kubectl rollout undo deployment/web-rolling -n k8s-lab
deployment.apps/web-rolling rolled back

$ kubectl get rs -n k8s-lab -l app=web-rolling
RS                       DESIRED   IMAGE
web-rolling-548d57497b   0         nginx:1.27-alpine
web-rolling-5c848dcfdb   4         nginx:1.25-alpine
```

The numbers simply swapped. **No image was rebuilt or re-pulled** — Kubernetes scaled the old
ReplicaSet back up and the new one down. That is why rollback takes seconds.

`CHANGE-CAUSE` is `<none>` because I didn't annotate the change. Adding
`kubectl annotate deployment/web-rolling kubernetes.io/change-cause="upgrade to 1.27"` makes
the history readable — worth doing in real projects.

![rolling update and rollback](screenshots/rolling-update.png)

---

## 5. Recreate

All old pods are killed **first**, then new ones start. Simple, and it has downtime.

```yaml
strategy:
  type: Recreate
```

```console
$ kubectl set image deployment/web-recreate nginx=nginx:1.27-alpine -n k8s-lab
deployment.apps/web-recreate image updated

  t+1s:  running=0   Terminating Terminating Terminating    <-- NOTHING is serving
  t+2s:  running=3   Running Running Running
  t+3s:  running=3   Running Running Running
```

`running=0` at t+1s is the downtime window, captured. On this tiny nginx it lasted about a
second; with a JVM app that takes 40s to warm up, it would be 40s of 503s.

**Use Recreate when** the app cannot tolerate two versions running at once — a schema migration
that isn't backward compatible, or a singleton holding an exclusive lock. Otherwise prefer
RollingUpdate.

---

## 6. Blue-Green

Two complete environments; a **Service selector** decides which one gets traffic.

```yaml
# Deployment app-blue  -> labels: {app: bg-app, version: blue}   image nginx:1.25
# Deployment app-green -> labels: {app: bg-app, version: green}  image nginx:1.27
---
apiVersion: v1
kind: Service
metadata:
  name: bg-service
spec:
  selector:
    app: bg-app
    version: blue     # <-- THE SWITCH
```

Both environments are running the whole time:

```console
$ kubectl get pods -n k8s-lab -l app=bg-app
POD                          VERSION   IMAGE
app-blue-bc48964d6-8hzl8     blue      nginx:1.25-alpine
app-blue-bc48964d6-rmzkg     blue      nginx:1.25-alpine
app-blue-bc48964d6-tlllp     blue      nginx:1.25-alpine
app-green-68c8d97457-6s85h   green     nginx:1.27-alpine
app-green-68c8d97457-9g7hw   green     nginx:1.27-alpine
app-green-68c8d97457-lcf6j   green     nginx:1.27-alpine
```

But only blue is wired to the Service. nginx reports its version in the `Server:` header, so
the response itself proves which pods answered:

```console
$ kubectl get endpoints bg-service -n k8s-lab
app-blue-bc48964d6-8hzl8 app-blue-bc48964d6-rmzkg app-blue-bc48964d6-tlllp

$ curl -I http://bg-service/      # from a pod in the cluster
Server: nginx/1.25.5
```

### Flip the switch

```console
$ kubectl patch service bg-service -n k8s-lab -p '{"spec":{"selector":{"app":"bg-app","version":"green"}}}'
service/bg-service patched

$ kubectl get endpoints bg-service -n k8s-lab
app-green-68c8d97457-6s85h app-green-68c8d97457-9g7hw app-green-68c8d97457-lcf6j

$ curl -I http://bg-service/
Server: nginx/1.27.5
```

One patch, and the endpoints and the served version both changed. **Rollback is the identical
command with `version: blue`** — which is blue-green's real selling point: the old environment
is still running, untouched, ready to take traffic back in a second.

The cost is that you need **double the resources** for the whole period both environments are
up.

![recreate and blue-green](screenshots/recreate-and-bluegreen.png)

---

## 7. Canary

One Service in front of **both** versions. The trick is what the selector *omits*:

```yaml
# canary-stable: replicas 4, labels {app: canary-app, track: stable}  nginx:1.25
# canary-new:    replicas 1, labels {app: canary-app, track: canary}  nginx:1.27
---
spec:
  selector:
    app: canary-app     # NOTE: no 'track' - so it matches BOTH deployments
```

```console
$ kubectl get pods -n k8s-lab -l app=canary-app
POD                              TRACK    IMAGE
canary-new-799c547bfb-l5r45      canary   nginx:1.27-alpine
canary-stable-86d595c6b9-2pfpj   stable   nginx:1.25-alpine
canary-stable-86d595c6b9-7zqmq   stable   nginx:1.25-alpine
canary-stable-86d595c6b9-gg9qn   stable   nginx:1.25-alpine
canary-stable-86d595c6b9-rc7wd   stable   nginx:1.25-alpine

$ kubectl get endpoints canary-service -n k8s-lab
canary-stable-...gg9qn
canary-new-...l5r45        <-- the canary is in the same endpoint list
canary-stable-...2pfpj
canary-stable-...7zqmq
canary-stable-...rc7wd
```

### The split is the replica ratio

40 requests through the Service, counted by `Server:` header:

```console
     24 Server: nginx/1.25.5     <- stable
      8 Server: nginx/1.27.5     <- canary
```

**24 : 8** out of the 32 responses that were captured — about **25% canary**, against a
theoretical 20% (1 canary pod out of 5). `kube-proxy` load-balances randomly per connection, so
a sample this small scatters around the expected ratio rather than hitting it exactly.

That is the honest limitation of this technique: **your traffic granularity is limited by your
replica count.** 1-in-5 pods is the finest split you can get with 5 pods. For a true 1% canary
you need either 100 pods or a service mesh / ingress that splits by weight rather than by pod
count.

### Promote

```console
$ kubectl scale deployment/canary-new    -n k8s-lab --replicas=4
$ kubectl scale deployment/canary-stable -n k8s-lab --replicas=0

$ kubectl get pods -n k8s-lab -l app=canary-app
POD                           TRACK    IMAGE
canary-new-799c547bfb-2f8hl   canary   nginx:1.27-alpine
canary-new-799c547bfb-dh8pc   canary   nginx:1.27-alpine
canary-new-799c547bfb-l5r45   canary   nginx:1.27-alpine
canary-new-799c547bfb-x549l   canary   nginx:1.27-alpine

--- all traffic now on the new version ---
     15 Server: nginx/1.27.5
```

100% on 1.27. Aborting instead would have been `kubectl scale deployment/canary-new --replicas=0`,
affecting only the 20% who had been routed to it.

![canary deployment](screenshots/canary.png)

---

## 8. Pod lifecycle

[`manifests/pod-lifecycle.yaml`](manifests/pod-lifecycle.yaml) creates six pods, one per
situation.

### Phases

| Phase | Meaning |
|---|---|
| `Pending` | Accepted, but not running yet — unscheduled, or still pulling the image |
| `Running` | Bound to a node, at least one container started |
| `Succeeded` | All containers exited **0** and will not restart |
| `Failed` | All containers terminated, at least one **non-zero** |
| `Unknown` | The node stopped reporting |

All five, live at once:

```console
$ kubectl get pods -n k8s-lab -o custom-columns=POD:...,PHASE:...,READY:...,RESTARTS:...
lifecycle-failed               Failed      false    0
lifecycle-init                 Running     true     0
lifecycle-liveness             Running     true     1
lifecycle-pending              Pending     <none>   <none>
lifecycle-readiness            Running     true     0
lifecycle-succeeded            Succeeded   false    0
```

### Init containers

Run to completion, in order, **before** any app container starts. For waiting on a dependency,
running a migration, or fetching config.

```console
--- t+3s ---
lifecycle-init 0/1 Init:0/1 0          <-- "Init:0/1" = 0 of 1 init containers done

$ kubectl logs lifecycle-init -c wait-for-it -n k8s-lab
init: preparing...
init: done

$ kubectl get pod lifecycle-init -o jsonpath='...'
initContainer: Completed exitCode=0
app container: 2026-09-17T17:19:36Z
```

The app container's `startedAt` is after the init container's `Completed` — the ordering is
enforced, not hoped for. Note `-c wait-for-it` is required: `kubectl logs` on a pod with init
containers needs to be told which container you mean.

### Readiness probe — "should I get traffic?"

```console
--- t+14s: running, but NOT ready ---
lifecycle-readiness 0/1 Running 0

--- t+25s: the probe's file was created at t+15s ---
lifecycle-readiness 1/1 Running 0
ready=true
```

`Running` and `Ready` are different things. A failing readiness probe pulls the pod out of
Service endpoints but **does not restart it** — the app is alive, just not able to serve yet.
This is what prevents traffic hitting a pod that is still warming up.

### Liveness probe — "am I broken?"

The container creates `/tmp/healthy`, then deletes it after 20s so the probe starts failing:

```console
$ kubectl get pod lifecycle-liveness -n k8s-lab
lifecycle-liveness 1/1 Running restarts=1

$ kubectl get pod lifecycle-liveness -o jsonpath='...'
restartCount=1
lastState=Error

$ kubectl get events ... | grep -E 'Unhealthy|Killing'
Unhealthy   2     Liveness probe failed: cat: can't open '/tmp/healthy': No such file or directory
Killing     1     Container app failed liveness probe, will be restarted
```

`Unhealthy` fired **twice** — matching `failureThreshold: 2` — and only then did `Killing`
happen. Kubernetes does not restart on a single blip.

> **The distinction that matters:** readiness failing = *stop sending traffic*.
> Liveness failing = *kill and restart the container*. Putting a slow dependency check in a
> liveness probe is a classic way to build a restart loop: the database gets slow, every pod
> fails liveness, every pod restarts, and the outage gets worse.

### Pending — why it never scheduled

```console
$ kubectl describe pod lifecycle-pending -n k8s-lab
  Warning  FailedScheduling  34s (x3 over 45s)  default-scheduler
  0/1 nodes are available: 1 Insufficient memory.
  preemption: 0/1 nodes are available: 1 Preemption is not helpful for scheduling.
```

This pod requested 500Gi. The scheduler tells you exactly why in the Events — which is why
`describe` beats `get` when something is stuck.

### Succeeded and Failed

```console
$ kubectl logs lifecycle-succeeded -n k8s-lab
doing work
finished

$ kubectl logs lifecycle-failed -n k8s-lab
about to fail
```

Both have `restartPolicy: Never`, so they stay in their terminal phase. With the default
`restartPolicy: Always`, the failed one would have gone into `CrashLoopBackOff` — Kubernetes
restarting it with increasing backoff (10s, 20s, 40s… capped at 5 min).

![pod lifecycle](screenshots/pod-lifecycle.png)

---

## Reproduce

```bash
kubectl create namespace k8s-lab

kubectl apply -f manifests/deployment.yaml
kubectl apply -f manifests/rolling-update.yaml
kubectl set image deployment/web-rolling nginx=nginx:1.27-alpine -n k8s-lab
kubectl rollout status  deployment/web-rolling -n k8s-lab
kubectl rollout history deployment/web-rolling -n k8s-lab
kubectl rollout undo    deployment/web-rolling -n k8s-lab

kubectl apply -f manifests/recreate.yaml
kubectl apply -f manifests/blue-green.yaml
kubectl patch service bg-service -n k8s-lab -p '{"spec":{"selector":{"app":"bg-app","version":"green"}}}'

kubectl apply -f manifests/canary.yaml
kubectl apply -f manifests/pod-lifecycle.yaml

kubectl delete namespace k8s-lab       # clean up everything at once
```

---

## Strategy comparison

| | Downtime | Extra resources | Rollback speed | Blast radius of a bad release |
|---|---|---|---|---|
| **RollingUpdate** | None | ~1 extra pod | Fast (scale old RS up) | Grows as the roll proceeds |
| **Recreate** | **Yes** | None | Slow (another full cycle) | Everyone, immediately |
| **Blue-Green** | None | **2× for the cutover** | Instant (flip selector back) | Everyone, but only after the flip |
| **Canary** | None | 1 extra pod | Instant (scale canary to 0) | **Only the canary %** |

Default to RollingUpdate. Reach for Blue-Green when you need an instant, complete rollback path,
and Canary when you want real users to validate a release before everyone gets it.

---

## What I took away

1. **Deployments manage versions; ReplicaSets manage counts.** Every template change mints a
   new ReplicaSet named after the template hash, and the old ones are kept at 0 replicas — that
   is the entire rollback mechanism.
2. **Labels and selectors are the wiring.** Blue-green and canary differ only in which labels
   the Service selector includes. No code changes, no proxy config.
3. **Self-healing belongs to the controller.** A deleted Pod under a ReplicaSet returns with a
   new name; a bare Pod stays dead.
4. **Readiness and liveness solve different problems** and conflating them causes outages.
5. **Canary granularity is bounded by replica count.** 1 in 5 pods is a 20% canary, and the
   observed 24:8 split shows kube-proxy's randomness around that target.
