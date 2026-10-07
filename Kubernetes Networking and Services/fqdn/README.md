# FQDN in Kubernetes

**Name:** Hemang
**Enrollment number:** 24bcs10209

Session 11, Task 3. Everything below was verified against the live cluster — the captured
output is in [the parent README](../#9-cluster-dns).

---

## What is an FQDN?

A **Fully Qualified Domain Name** is a name that is complete and unambiguous — it names the
host *and* every domain above it, right up to the root. No search path is needed to resolve it.

```text
backend-clusterip.k8s-lab.svc.cluster.local
└─────┬────────┘ └──┬──┘ └┬┘ └──────┬──────┘
   hostname      subdomain │     root domain
                           └ the "svc" level
```

`backend-clusterip` on its own is a **relative** name — it only resolves if the resolver
completes it from a search list. The FQDN always resolves, from any namespace.

---

## Kubernetes Service DNS

Every Service automatically gets a DNS A record. No registration, no config — creating the
Service is enough, because CoreDNS watches the API server.

```console
$ kubectl get svc backend-clusterip -n k8s-lab
NAME                TYPE        CLUSTER-IP      PORT(S)
backend-clusterip   ClusterIP   10.100.138.82   80/TCP

$ nslookup backend-clusterip.k8s-lab.svc.cluster.local
Server:     10.96.0.10
Name:   backend-clusterip.k8s-lab.svc.cluster.local
Address: 10.100.138.82          # exactly the ClusterIP
```

---

## The naming convention

```text
<service-name>.<namespace>.svc.<cluster-domain>
```

| Part | Value here | Meaning |
|---|---|---|
| `<service-name>` | `backend-clusterip` | `metadata.name` of the Service |
| `<namespace>` | `k8s-lab` | Where the Service lives |
| `svc` | `svc` | Fixed — distinguishes Services from Pods |
| `<cluster-domain>` | `cluster.local` | Cluster-wide default, set at install time |

### Pods get records too

```text
<pod-ip-with-dashes>.<namespace>.pod.cluster.local
10-244-0-58.k8s-lab.pod.cluster.local
```

Note `pod` instead of `svc`. These are rarely useful directly — the IP is already in the name,
so it solves nothing. The exception is **StatefulSet Pods behind a headless Service**, which get
genuinely stable per-Pod names:

```text
<pod-name>.<headless-service>.<namespace>.svc.cluster.local
mysql-0.backend-headless.k8s-lab.svc.cluster.local
```

That name survives rescheduling, which is what lets you address "the primary" specifically.

### Named ports get SRV records

```text
_<port-name>._<protocol>.<service>.<namespace>.svc.cluster.local
_http._tcp.backend-clusterip.k8s-lab.svc.cluster.local
```

---

## Namespace-based DNS, and why short names work

Every Pod gets a resolver config injected by the kubelet:

```console
$ cat /etc/resolv.conf
search k8s-lab.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.96.0.10
options ndots:5
```

The **search list** is what makes short names work. From a Pod in `k8s-lab`:

| You write | Tried as | Result |
|---|---|---|
| `backend-clusterip` | `backend-clusterip.k8s-lab.svc.cluster.local` | ✅ first search entry |
| `backend-clusterip.k8s-lab` | `backend-clusterip.k8s-lab.svc.cluster.local` | ✅ second entry |
| `backend-clusterip.k8s-lab.svc` | `...svc.cluster.local` | ✅ third entry |
| `backend-clusterip.k8s-lab.svc.cluster.local` | itself | ✅ already fully qualified |

**The namespace is the key variable.** A Pod in `k8s-lab` reaches a Service in `k8s-lab` by its
short name. To reach a Service in a *different* namespace, the short name fails — you must
qualify it at least as far as the namespace:

```text
from k8s-lab → service "api" in k8s-lab        :  api                 ✅
from k8s-lab → service "api" in production     :  api                 ❌ resolves to the wrong thing or NXDOMAIN
from k8s-lab → service "api" in production     :  api.production      ✅
```

This is a very common bug: an app works in dev (everything in one namespace) and breaks in prod
(split across namespaces) because the code hard-codes a short name.

### `ndots:5`

Any name with **fewer than 5 dots** is tried against the search list *first*, before being
tried as an absolute name. So `google.com` (1 dot) inside a Pod does four failing lookups —
`google.com.k8s-lab.svc.cluster.local`, `google.com.svc.cluster.local`,
`google.com.cluster.local` — before finally resolving. That is a well-known source of DNS
latency. Writing `google.com.` with a trailing dot marks it absolute and skips the search list
entirely.

---

## Pod-to-Service communication

```text
Pod "frontend" (k8s-lab)                          CoreDNS (10.96.0.10)
   │                                                      │
   │ 1. connect to "backend-clusterip"                     │
   │ 2. resolver appends search domain ────────────────────►│
   │                                                        │ kubernetes plugin
   │ 3. ◄─────────────── A record: 10.100.138.82 ───────────┘ answers from the
   │                                                          API server's state
   │ 4. send packet to 10.100.138.82:80
   │        │
   │        ▼  kube-proxy iptables/IPVS rule
   │    DNAT to one Ready endpoint, chosen at random
   │        │
   └────────┴──► Pod 10.244.0.59:80
```

Two independent systems: **CoreDNS** turns the name into a Service IP; **kube-proxy** turns the
Service IP into a Pod IP. A failure in the first gives `NXDOMAIN` / `bad address`; a failure in
the second gives a connection timeout or refusal with DNS working fine. Knowing which half
broke is most of the debugging.

---

## Examples

| FQDN | What it is |
|---|---|
| `kubernetes.default.svc.cluster.local` | The API server itself — reachable from any Pod |
| `kube-dns.kube-system.svc.cluster.local` | CoreDNS's own Service |
| `backend-clusterip.k8s-lab.svc.cluster.local` | A normal ClusterIP Service → one virtual IP |
| `backend-headless.k8s-lab.svc.cluster.local` | A **headless** Service → returns **all** Pod IPs |
| `mysql-0.backend-headless.k8s-lab.svc.cluster.local` | One specific StatefulSet Pod |
| `external-api.k8s-lab.svc.cluster.local` | An ExternalName Service → a **CNAME** to `example.com` |
| `10-244-0-58.k8s-lab.pod.cluster.local` | A Pod, addressed by IP-as-name |

The headless and ExternalName cases are worth contrasting, both verified live:

```console
# headless -> every pod IP, no virtual IP
$ nslookup backend-headless.k8s-lab.svc.cluster.local
Address: 10.244.0.60
Address: 10.244.0.59
Address: 10.244.0.58

# ExternalName -> a CNAME straight out of the cluster
$ nslookup external-api.k8s-lab.svc.cluster.local
external-api.k8s-lab.svc.cluster.local  canonical name = example.com
Name:   example.com
Address: 104.20.23.154
```

---

## Practical takeaways

1. **Use the namespace-qualified name** (`api.production`) for anything crossing a namespace.
   Short names silently resolve to the wrong namespace or not at all.
2. **Use the full FQDN in config files** when you want zero ambiguity — it is immune to the
   search path and to `ndots`.
3. **A trailing dot** makes a name absolute and skips the search list — worth it for external
   hostnames in hot paths.
4. **DNS failure ≠ network failure.** `nslookup` the FQDN first; if that works, the problem is
   endpoints or kube-proxy, not naming.
