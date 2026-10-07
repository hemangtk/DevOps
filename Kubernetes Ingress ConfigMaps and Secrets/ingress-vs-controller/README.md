# Ingress vs Ingress Controller

**Name:** Hemang
**Enrollment number:** 24bcs10209

Session 12, Task 4. The outputs below are from the live minikube cluster; the full routing run
is in [the parent README](../#4-ingress).

---

## The one-sentence version

> An **Ingress** is a set of routing *rules* stored in the API server.
> An **Ingress Controller** is a *program* that reads those rules and actually proxies traffic.
> Rules without a program do nothing; a program without rules has nothing to do.

---

## What is an Ingress?

An **Ingress** is a Kubernetes API object (`networking.k8s.io/v1`) that describes how external
HTTP/HTTPS traffic should reach Services inside the cluster. It is **declarative data** — a
config file in the API server, nothing more.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  ingressClassName: nginx
  rules:
    - host: devops.local
      http:
        paths:
          - path: /api(/|$)(.*)
            pathType: ImplementationSpecific
            backend:
              service: { name: api-svc, port: { number: 80 } }
          - path: /
            pathType: Prefix
            backend:
              service: { name: frontend-svc, port: { number: 80 } }
```

It can express:

- **Host-based routing** — `api.example.com` vs `www.example.com`
- **Path-based routing** — `/api` vs `/`
- **TLS termination** — certificates from a Secret
- **A default backend** — where unmatched requests go

What it **cannot** do on its own: move a single packet.

---

## What is an Ingress Controller?

An **Ingress Controller** is a Pod running an actual reverse proxy — nginx, HAProxy, Traefik,
Envoy — plus a control loop that:

1. **Watches** the API server for Ingress objects.
2. **Translates** them into that proxy's native configuration.
3. **Reloads** the proxy.
4. **Watches Endpoints** too, so the proxy's upstreams follow Pods as they come and go.

```console
$ kubectl get pods -n ingress-nginx
ingress-nginx-controller-d7cd8c989-rwqh5   1/1   Running

$ kubectl get ingressclass
NAME              CONTROLLER             PARAMETERS   AGE
nginx (default)   k8s.io/ingress-nginx   <none>       17m
```

It is an ordinary workload — a Deployment, with a Service in front of it — that happens to
have RBAC permission to read Ingresses cluster-wide.

---

## The difference

| | **Ingress** | **Ingress Controller** |
|---|---|---|
| **What it is** | An API object — YAML | A running Pod — a reverse proxy + control loop |
| **Role** | Declares *what* routing should happen | Makes it *actually* happen |
| **Ships with Kubernetes?** | Yes, the API type is built in | **No** — you install one |
| **How many** | Many, one per app or team | Usually one (or one per class) for the cluster |
| **Namespace** | Namespaced, next to your app | Usually its own namespace (`ingress-nginx`) |
| **If removed** | That app stops being routed | **Every** Ingress stops working |
| **Analogy** | A street sign | The driver who reads it |

---

## Why both are required

The split exists so that **routing intent is portable** while the implementation is pluggable.

- **Separation of concerns.** An app team writes an Ingress in their own namespace without any
  permission to touch the shared proxy. The platform team owns the controller.
- **Pluggability.** The same Ingress YAML works whether the cluster runs ingress-nginx, Traefik,
  HAProxy or a cloud ALB controller. Swap the controller, keep the manifests.
- **One entry point, many apps.** Without Ingress, exposing 30 services means 30 LoadBalancer
  Services and 30 cloud load balancers. With Ingress, one controller behind one LB serves all
  30, routing by host and path — and holds one TLS certificate instead of 30.
- **Kubernetes stays unopinionated.** Shipping nginx in-tree would force a choice on everyone.

### What happens if the controller is missing

The Ingress is created perfectly happily, and simply never works:

```console
$ kubectl apply -f ingress.yaml
ingress.networking.k8s.io/app-ingress created     # accepted

$ kubectl get ingress
NAME          CLASS   HOSTS          ADDRESS   PORTS   AGE
app-ingress   nginx   devops.local             80      8s
                                     ^^^^^^^
                                     empty forever — nothing claimed it
```

No error, no warning. The empty `ADDRESS` is the only clue. This is the single most common
"my Ingress doesn't work" cause.

With a controller present, it claims the Ingress and resolves the rules to live Pod IPs:

```console
$ kubectl describe ingress app-ingress -n k8s-lab
Rules:
  Host          Path  Backends
  ----          ----  --------
  devops.local
                /api(/|$)(.*)   api-svc:80      (10.244.0.78:80,10.244.0.79:80)
                /               frontend-svc:80 (10.244.0.76:80,10.244.0.77:80)
Events:
  Normal  Sync   8s   nginx-ingress-controller  Scheduled for sync
```

That `Sync` event, attributed to `nginx-ingress-controller`, is the controller announcing it has
picked up the rules. And the routing then genuinely works:

```console
$ curl -H 'Host: devops.local' http://192.168.49.2/
<h1>FRONTEND service</h1>

$ curl -H 'Host: devops.local' http://192.168.49.2/api
<h1>API service</h1>
```

---

## How they fit together

```text
                 ┌──────────────── Kubernetes API server ───────────────┐
                 │   Ingress "app-ingress"   (rules: / → frontend-svc,  │
                 │                                   /api → api-svc)    │
                 └───────────────────────┬──────────────────────────────┘
                                         │ watch
                                         ▼
  Internet ──► LoadBalancer/NodePort ──► Ingress Controller Pod
                                         (nginx + control loop)
                                         │ writes nginx.conf, reloads
                                         │ routes by Host + path
                        ┌────────────────┴────────────────┐
                        ▼                                 ▼
                  frontend-svc (ClusterIP)          api-svc (ClusterIP)
                        │                                 │
                 frontend Pods                        api Pods
```

Note both backend Services stay **ClusterIP** — not exposed externally. Only the controller is.

---

## `IngressClass` — which controller takes which Ingress

A cluster can run several controllers. `IngressClass` decides ownership:

```yaml
spec:
  ingressClassName: nginx     # this Ingress belongs to the nginx controller
```

An Ingress with no `ingressClassName` is claimed by the **default** class — here `nginx (default)`.
If no class is set and no default exists, **no controller claims it** and it silently does
nothing. A realistic split is an `internal` class on a private LB and an `external` class on a
public one.

---

## Common controllers

| Controller | Notes |
|---|---|
| **ingress-nginx** | The community default. What `minikube addons enable ingress` installs |
| **Traefik** | Config via CRDs, automatic Let's Encrypt, default in K3s |
| **HAProxy** | Very high performance, strong TCP/L4 support |
| **AWS ALB Controller** | Creates a real ALB per Ingress — AWS-native |
| **Istio Gateway** | Part of a service mesh; richer traffic policy |

Annotations are **controller-specific**: `nginx.ingress.kubernetes.io/rewrite-target` means
nothing to Traefik. This is the main portability caveat — the `spec` is standard, the
annotations are not. The newer **Gateway API** exists largely to fix that.

---

## Troubleshooting

| Symptom | Cause | Check |
|---|---|---|
| `ADDRESS` stays empty | No controller, or wrong `ingressClassName` | `kubectl get pods -n ingress-nginx`, `kubectl get ingressclass` |
| 404 from the proxy | `Host` header doesn't match any rule | `kubectl describe ingress` |
| 503 from the proxy | Backend Service has **no endpoints** | `kubectl get endpoints <svc>` |
| Backend 404s on every path | Missing `rewrite-target` | The app receives `/api/foo`, not `/foo` |
| TLS not applied | Secret missing, wrong namespace, or wrong type | `kubectl get secret -n <ns>` |

The 404-vs-503 distinction is the quick diagnostic: **404 = the controller didn't match a rule**
(your Ingress is wrong); **503 = it matched but found nothing to forward to** (your Service is
wrong).

---

## Summary

1. **Ingress = rules. Controller = the program that enforces them.** Both, or nothing happens.
2. **Kubernetes ships the API type but no implementation** — installing a controller is on you.
3. **An Ingress with no controller fails silently**, with an empty `ADDRESS` as the only hint.
4. **`IngressClass` routes rules to controllers** when more than one exists.
5. **The `spec` is portable; annotations are not.** Gateway API is the standards-based successor.
