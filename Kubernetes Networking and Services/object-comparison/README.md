# Kubernetes Object Comparison

**Name:** Hemang
**Enrollment number:** 24bcs10209

Session 11, Task 2. Three comparisons that come up constantly, both in practice and in
interviews.

---

## 1. Deployment vs ReplicaSet

| | **ReplicaSet** | **Deployment** |
|---|---|---|
| **Purpose** | Keep exactly *N* identical Pods alive | Manage **versions** of a ReplicaSet over time |
| **Pod management** | Creates/deletes Pods to match `replicas` | Never touches Pods directly — it drives ReplicaSets |
| **Scaling** | Yes, by changing `replicas` | Yes — it passes the number down to the active ReplicaSet |
| **Rolling updates** | **No.** Changing its template does nothing to running Pods | **Yes.** Creates a new ReplicaSet and shifts replicas across |
| **Rollback** | No concept of history | `kubectl rollout undo` — old ReplicaSets are kept at 0 |
| **Written by hand?** | Almost never | Nearly always |

### The relationship

```text
Deployment  "web"
   │  owns (and creates a new one per template change)
   ├── ReplicaSet  web-5c848dcfdb   replicas=0   nginx:1.25   ← previous version
   └── ReplicaSet  web-548d57497b   replicas=4   nginx:1.27   ← current version
          │  owns
          ├── Pod web-548d57497b-765tq
          ├── Pod web-548d57497b-bzwlh
          └── ...
```

The suffix (`548d57497b`) is a **hash of the Pod template**. Change the image and the hash
changes, so a *different* ReplicaSet is created. That is the entire mechanism behind rolling
updates and rollbacks — proven in
[the Deployments topic](../../Kubernetes%20Pods%20ReplicaSets%20and%20Deployments/#4-rolling-update),
where `rollout undo` just swapped `replicas` between two ReplicaSets with no image re-pull.

**Rule of thumb:** a ReplicaSet answers *"how many?"*; a Deployment answers *"which version, and
how do we get there safely?"* You want a Deployment.

---

## 2. Deployment vs DaemonSet vs StatefulSet

| | **Deployment** | **DaemonSet** | **StatefulSet** |
|---|---|---|---|
| **Use case** | Stateless apps — web servers, APIs | One Pod **per node** — log shippers, CNI, node exporters | Stateful apps — databases, Kafka, Zookeeper |
| **Pod creation** | *N* interchangeable Pods, any node | Exactly one per eligible node; new node → new Pod automatically | *N* Pods created **in order**, 0 → 1 → 2 |
| **Pod names** | Random suffix: `web-548d57497b-765tq` | Random suffix, pinned to a node | **Stable ordinal**: `mysql-0`, `mysql-1`, `mysql-2` |
| **Scaling** | `replicas`, any order, parallel | Not set by you — it follows the node count | Ordered; scale-down removes the **highest** ordinal first |
| **Networking** | One Service load-balances across all Pods | Usually reached via the node, or not at all | **Headless** Service gives each Pod its own DNS name |
| **Storage** | Usually none, or one shared PVC | Usually `hostPath` to read node state | `volumeClaimTemplates` — **a PVC per Pod**, reattached by ordinal |
| **Pod identity** | Disposable, interchangeable | Tied to a node | **Sticky** — `mysql-0` is always `mysql-0`, same name, same disk |
| **Example** | `nginx`, a REST API | `fluentd`, `node-exporter`, `kube-proxy` | `mysql`, `postgres`, `elasticsearch` |

### When each one is right

- **Deployment** — the default. If any replica can serve any request and losing one costs
  nothing, use this.
- **DaemonSet** — when the workload is *about the node itself*: collecting its logs, exporting
  its metrics, providing its networking. You never set a replica count; adding a node adds a Pod.
- **StatefulSet** — when Pods are **not** interchangeable. A database primary has data the
  replicas don't. `mysql-0` must come back as `mysql-0` and must get **its own disk** back, not
  a fresh one. That is what the ordinal naming plus `volumeClaimTemplates` guarantee.

The giveaway for StatefulSet is: *"would it break if these Pods swapped identities?"* If yes,
you need stable identity and stable storage.

---

## 3. ReplicaSet vs Service

These are not alternatives — they solve **completely different problems** and you almost always
need both.

| | **ReplicaSet** | **Service** |
|---|---|---|
| **Responsibility** | *Running* the Pods — keeping N alive | *Reaching* the Pods — a stable address in front of them |
| **What it watches** | Pod count vs desired | Which Pods match its selector and are **Ready** |
| **What it creates** | Pods | A virtual IP + DNS name + Endpoints list |
| **If it disappears** | Pods stop being replaced | Pods keep running, but nothing can find them reliably |
| **Layer** | Workload / lifecycle | Networking |

### Why a Service is required

Pod IPs are ephemeral. In
[the Deployments topic](../../Kubernetes%20Pods%20ReplicaSets%20and%20Deployments/#2-self-healing)
I deleted a Pod and the ReplicaSet replaced it with a **different name and a different IP**.
The ReplicaSet did its job perfectly — three Pods alive — but any client holding the old IP is
now broken.

A Service fixes exactly that, and nothing else:

```text
Client ──► Service (stable ClusterIP 10.100.138.82, stable DNS name)
                │  kube-proxy DNATs to one of the current Endpoints
                ├──► Pod 10.244.0.58   ┐
                ├──► Pod 10.244.0.59   ├─ membership maintained by the
                └──► Pod 10.244.0.60   ┘  endpoint controller, not the ReplicaSet
```

### How traffic actually reaches a Pod

1. The client resolves `backend-clusterip` through **CoreDNS** → the Service's ClusterIP.
2. The packet is sent to that ClusterIP, which belongs to no network interface anywhere.
3. **kube-proxy** has programmed iptables/IPVS rules on every node for that ClusterIP. The rule
   DNATs the packet to one Pod IP from the Endpoints list, chosen at random.
4. The packet reaches the Pod. The reply is un-NATed on the way back, so the client still sees
   the ClusterIP as its peer.

That last detail is observable: `curl -w '%{remote_ip}'` against the Service returned
**`10.100.138.82`, the ClusterIP** — never a Pod IP.

The two objects meet at **labels**: the ReplicaSet stamps `app: backend` onto the Pods it
creates, and the Service selects `app: backend`. Break that string on either side and you get
a Service with zero endpoints — demonstrated with a one-character typo in
[the Services topic](../#10-troubleshooting-the-empty-endpoints-bug).

---

## Summary

| Question | Object |
|---|---|
| How many Pods, and are they still alive? | **ReplicaSet** |
| Which version, and how do we roll it out safely? | **Deployment** |
| One Pod on every node? | **DaemonSet** |
| Stable names and stable disks per Pod? | **StatefulSet** |
| How does anything find these Pods? | **Service** |
