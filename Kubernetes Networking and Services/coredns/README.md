# CoreDNS

**Name:** Hemang
**Enrollment number:** 24bcs10209

Session 11, Task 4. The Corefile and cluster output below were read from the live minikube
cluster.

---

## What is CoreDNS?

**CoreDNS** is the DNS server that runs *inside* the cluster and answers name lookups for every
Pod. It is a general-purpose, plugin-based DNS server written in Go; Kubernetes uses it by
configuring one specific plugin — `kubernetes` — which reads Services and Pods from the API
server and serves them as DNS records.

It runs as an ordinary Deployment in `kube-system`:

```console
$ kubectl get deployment coredns -n kube-system
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
coredns   1/1     1            1           20m

$ kubectl get svc kube-dns -n kube-system
NAME       TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)                  AGE
kube-dns   ClusterIP   10.96.0.10   <none>        53/UDP,53/TCP,9153/TCP   20m
```

Note the Service is still called **`kube-dns`** even though CoreDNS is what's behind it — the
name was kept so nothing had to be reconfigured during the migration. `10.96.0.10` is the
address injected into every Pod's `/etc/resolv.conf` as `nameserver`.

---

## Why Kubernetes uses CoreDNS

CoreDNS replaced the older **kube-dns** as the default in Kubernetes 1.13.

| | kube-dns | CoreDNS |
|---|---|---|
| Processes per Pod | **3** (`kubedns`, `dnsmasq`, `sidecar`) | **1** |
| Language | Go + C (dnsmasq) | Pure Go |
| Configuration | Flags across three containers | One **Corefile** |
| Extensibility | Hard | Plugin chain — add/remove behaviour per zone |
| Security history | dnsmasq had several CVEs | Smaller surface, memory-safe |

The practical wins: one process instead of three, a single readable config file, and the ability
to add behaviour (rewrite, custom forwarding, per-zone policy) by editing a ConfigMap rather
than patching a deployment.

---

## How Service discovery works

CoreDNS doesn't have a zone file. The `kubernetes` plugin **watches the API server** for
Services, Endpoints and Pods, and synthesises records on the fly:

```text
1. You create a Service            kubectl apply -f service.yaml
2. API server stores it            etcd
3. CoreDNS is WATCHING Services    (a long-lived watch connection)
4. CoreDNS updates its in-memory map
5. The record is instantly resolvable from any Pod
```

No registration step, no reload, no TTL wait on creation. Delete the Service and the record
vanishes just as fast.

What it serves:

| Record | For | Returns |
|---|---|---|
| `A` | A normal Service | The **ClusterIP** |
| `A` | A **headless** Service | **Every ready Pod IP** |
| `CNAME` | An **ExternalName** Service | The external hostname |
| `A` | `<pod-name>.<headless-svc>...` | One specific StatefulSet Pod |
| `SRV` | `_port._proto.<svc>...` | Port and target for named ports |
| `PTR` | Reverse lookups | Name for a cluster IP |

---

## How a DNS query is resolved

```text
Pod (in namespace k8s-lab) asks for "backend-clusterip"
   │
   │ resolver reads /etc/resolv.conf:
   │   search k8s-lab.svc.cluster.local svc.cluster.local cluster.local
   │   nameserver 10.96.0.10
   │   options ndots:5
   │
   │ "backend-clusterip" has 0 dots, which is < ndots:5,
   │ so the search list is tried FIRST
   ▼
   query: backend-clusterip.k8s-lab.svc.cluster.local  ──► 10.96.0.10 (CoreDNS)
                                                              │
   ┌──────────────────────────────────────────────────────────┘
   │ Corefile plugin chain, in order:
   │   errors   → log any failures
   │   health   → (liveness endpoint, not query handling)
   │   kubernetes cluster.local ... → ✅ MATCHES this zone.
   │        Looks up Service "backend-clusterip" in namespace "k8s-lab".
   │        Found → return A 10.100.138.82, ttl 30
   │   (forward is never reached, because kubernetes already answered)
   ▼
   10.100.138.82
```

If the name had **not** matched `cluster.local`, the chain would have fallen through to
`forward . /etc/resolv.conf`, which sends it to the node's upstream resolver — that is how Pods
resolve `github.com`.

---

## CoreDNS configuration — the Corefile

Stored in a ConfigMap, so changing DNS behaviour is a `kubectl edit` away:

```console
$ kubectl get configmap coredns -n kube-system -o jsonpath='{.data.Corefile}'
.:53 {
    log
    errors
    health {
       lameduck 5s
    }
    ready
    kubernetes cluster.local in-addr.arpa ip6.arpa {
       pods insecure
       fallthrough in-addr.arpa ip6.arpa
       ttl 30
    }
    prometheus :9153
    hosts {
       192.168.65.254 host.minikube.internal
       fallthrough
    }
    forward . /etc/resolv.conf {
       max_concurrent 1000
    }
    cache 30 {
       disable success cluster.local
       disable denial cluster.local
    }
    loop
    reload
    loadbalance
}
```

Line by line:

| Directive | What it does |
|---|---|
| `.:53` | Serve **all** zones (`.`) on port 53 |
| `log` | Log every query — useful for debugging, noisy in production |
| `errors` | Log errors |
| `health { lameduck 5s }` | `/health` endpoint; on shutdown keep reporting healthy for 5s so in-flight queries drain |
| `ready` | `/ready` endpoint — signals when plugins are ready to serve |
| `kubernetes cluster.local ...` | **The Kubernetes plugin.** Serves the cluster zone from the API server |
| `pods insecure` | Serve `<ip>.<ns>.pod.cluster.local` without verifying the Pod exists |
| `fallthrough in-addr.arpa ip6.arpa` | If a reverse lookup isn't ours, pass it to the next plugin |
| `ttl 30` | Records are cacheable for 30 seconds |
| `prometheus :9153` | Export metrics — query counts, latency, cache hit rate |
| `hosts { ... }` | A static entry, here mapping `host.minikube.internal` to the host machine |
| `forward . /etc/resolv.conf` | **Everything else** goes upstream, using the node's own resolver |
| `cache 30` | Cache answers for 30s |
| `loop` | Detect forwarding loops and crash loudly rather than melt down |
| `reload` | Watch the ConfigMap and reload automatically — no restart needed |
| `loadbalance` | Shuffle A records in responses, spreading client-side load |

**Plugin order in the file is not execution order** — CoreDNS uses a fixed internal priority.
But `kubernetes` always gets the cluster zone before `forward` sees it, which is the part that
matters.

### Customising

A common production change is sending one domain to a specific resolver:

```text
company.internal:53 {
    errors
    cache 30
    forward . 10.0.0.53
}
```

Prefer the **`coredns-custom`** ConfigMap on managed clusters (AKS/GKE), since edits to the main
`coredns` ConfigMap get reverted on upgrade.

---

## Troubleshooting DNS

### 1. Is CoreDNS running?

```console
$ kubectl get pods -n kube-system -l k8s-app=kube-dns
coredns-559f6c778d-p8tt7   1/1   Running

$ kubectl logs -n kube-system -l k8s-app=kube-dns --tail=20
```

`CrashLoopBackOff` with `plugin/loop: Loop ... detected` means the node's `/etc/resolv.conf`
points back at CoreDNS itself — common on systems using `systemd-resolved` with a `127.0.0.53`
stub.

### 2. Does the Pod have the right resolver?

```console
$ kubectl exec <pod> -- cat /etc/resolv.conf
search k8s-lab.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.96.0.10
options ndots:5
```

Wrong nameserver → the Pod's `dnsPolicy` is wrong (`Default` inherits the node's resolver
instead of using cluster DNS).

### 3. Can you resolve the FQDN?

```console
$ kubectl run dns --rm -i --restart=Never --image=busybox:1.36 -- \
    nslookup backend-clusterip.k8s-lab.svc.cluster.local
Server:     10.96.0.10
Name:   backend-clusterip.k8s-lab.svc.cluster.local
Address: 10.100.138.82
```

Always test the **FQDN first**. If the FQDN works but the short name doesn't, the problem is the
search path or namespace, not CoreDNS.

> **A trap worth knowing:** busybox's `nslookup` does **not** walk the search list the way the
> libc resolver does. In [the parent README](../#9-cluster-dns) `nslookup backend-clusterip`
> returned `NXDOMAIN` while `curl http://backend-clusterip/` from the same namespace worked
> perfectly, 30 times. Use the FQDN, or `dig` from a `dnsutils` image, when testing by hand —
> otherwise you will chase a DNS bug that does not exist.

### 4. Is it DNS at all, or the Service?

```console
$ kubectl get endpoints <service>
```

`<none>` means the Service has no Pods behind it — the selector is wrong or the Pods aren't
Ready. DNS will happily resolve the name to a ClusterIP that routes nowhere.

### 5. Check the metrics

```console
$ kubectl port-forward -n kube-system svc/kube-dns 9153:9153
$ curl -s localhost:9153/metrics | grep coredns_dns_request
```

### Quick reference

| Symptom | Likely cause |
|---|---|
| `NXDOMAIN` on FQDN | Service doesn't exist, or wrong namespace in the name |
| Short name fails, FQDN works | Search path / wrong namespace / busybox `nslookup` quirk |
| All DNS fails in every Pod | CoreDNS down, or the `kube-dns` Service has no endpoints |
| CoreDNS in `CrashLoopBackOff` | `plugin/loop` — node resolver points back at CoreDNS |
| External names fail, cluster names work | `forward` upstream is unreachable |
| Name resolves, connection fails | **Not DNS.** Check Service endpoints and kube-proxy |
| Intermittent slow lookups | `ndots:5` doing extra lookups; use a trailing dot or `dnsConfig` |

---

## What I took away

1. **CoreDNS is a watcher, not a zone file.** It builds records from live API server state, so
   DNS is correct the instant a Service is created.
2. **The Corefile is the whole configuration**, in one ConfigMap, with `reload` picking up
   changes automatically.
3. **`kubernetes` answers the cluster zone, `forward` handles everything else** — one server
   covering both internal and external names.
4. **"DNS is broken" usually isn't.** Check endpoints before blaming CoreDNS, and test with the
   FQDN before blaming the search path.
