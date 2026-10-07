# Kubernetes Volumes

**Name:** Hemang
**Enrollment number:** 24bcs10209

Session 13, Task 1. Every claim below was verified on a live minikube cluster — the captured
runs are in [the parent README](../#1-volumes).

---

## The problem volumes solve

A container's filesystem is **ephemeral**. When a container restarts, its writable layer is
thrown away and rebuilt from the image. Two separate problems follow:

1. **Data loss on restart** — a database would lose everything every crash.
2. **No sharing** — two containers in the same Pod cannot see each other's files.

A **Volume** is a directory, backed by some storage medium, that is mounted into one or more
containers. Its *lifetime* is the whole point, and it differs per type.

```text
           ephemeral ──────────────────────────────────────► durable

  container fs      emptyDir          hostPath         PV / PVC
  dies on           dies with         lives on         independent of
  restart           the POD           ONE node         pods AND nodes
```

---

## 1. `emptyDir`

An empty directory created when the Pod is assigned to a node, and **deleted when the Pod is
removed**. It survives a *container* restart, but not a *Pod* deletion.

```yaml
volumes:
  - name: scratch
    emptyDir: {}
```

Its real use is **sharing between containers in the same Pod** — both mount the same volume:

```console
$ kubectl exec vol-emptydir -c writer -- cat /shared/log.txt
line 1 from writer
...
line 5 from writer

$ kubectl logs vol-emptydir -c reader
--- reader sees ---
line 1 from writer
...
line 5 from writer
```

Two different containers, one shared directory. Delete the Pod and the directory goes with it.

**Use for:** scratch space, caches, a sidecar reading the main container's output (log shipping),
checkpointing during long computations.

**Tip:** `emptyDir: { medium: Memory }` backs it with tmpfs (RAM) instead of disk — fast, and
it counts against the container's memory limit.

---

## 2. `hostPath`

Mounts a file or directory **from the node's own filesystem** into the Pod.

```yaml
volumes:
  - name: nodedir
    hostPath:
      path: /tmp/k8s-hostpath-demo
      type: DirectoryOrCreate
```

The data genuinely lives on the node, outside any Pod:

```console
$ kubectl logs vol-hostpath
written by vol-hostpath at Wed Oct  7 13:30:19 UTC 2026

$ minikube ssh -- 'cat /tmp/k8s-hostpath-demo/proof.txt'
written by vol-hostpath at Wed Oct  7 13:30:19 UTC 2026

$ kubectl delete pod vol-hostpath
$ minikube ssh -- 'cat /tmp/k8s-hostpath-demo/proof.txt'
written by vol-hostpath at Wed Oct  7 13:30:19 UTC 2026    # still there
```

### Why you should usually avoid it

- **It pins the Pod to one node.** Reschedule onto another node and the data is simply not
  there — the Pod starts with an empty directory and no error.
- **It is a security hole.** `hostPath: /` mounted writable lets a Pod modify the node. Mounting
  `/var/run/docker.sock` is effectively root on the host.
- It makes the Pod non-portable: the behaviour depends on the node's filesystem layout.

**Legitimate uses** are all *about the node itself*, and nearly always in a DaemonSet: log
collectors reading `/var/log`, monitoring agents reading `/proc` and `/sys`, CNI plugins.

`type:` matters — `DirectoryOrCreate` creates it if missing; plain `Directory` fails the Pod if
it isn't already there, which is usually what you want for safety.

---

## 3. PersistentVolume (PV)

A **PV** is a piece of storage in the cluster — an actual NFS export, EBS volume, or host
directory. It is a **cluster-scoped** resource with its own lifecycle, completely independent
of any Pod.

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: manual-pv
spec:
  capacity:
    storage: 1Gi
  accessModes: [ReadWriteOnce]
  persistentVolumeReclaimPolicy: Retain
  storageClassName: manual
  hostPath:
    path: /mnt/data
```

Think of a PV as supply — created by an administrator, or automatically by a provisioner.

### Access modes

| Mode | Short | Meaning |
|---|---|---|
| `ReadWriteOnce` | RWO | Read-write by **one node**. Most block storage (EBS, hostPath). |
| `ReadOnlyMany` | ROX | Read-only by many nodes |
| `ReadWriteMany` | RWX | Read-write by **many nodes**. Needs a shared filesystem (NFS, EFS, CephFS). |
| `ReadWriteOncePod` | RWOP | Read-write by exactly **one Pod** |

RWO is per *node*, not per Pod — several Pods on the same node can share an RWO volume. This
catches people out when a Deployment with 3 replicas gets stuck: the second and third Pods land
on other nodes and cannot attach.

### Reclaim policy

| Policy | What happens when the PVC is deleted |
|---|---|
| `Delete` | The PV **and the underlying storage** are destroyed. Default for dynamic provisioning. |
| `Retain` | The PV is kept with its data, marked `Released`. An admin must clean it up manually. |
| `Recycle` | Deprecated. |

Production databases should use **`Retain`**, so deleting a PVC by accident doesn't delete the data.

---

## 4. PersistentVolumeClaim (PVC)

A **PVC** is a *request* for storage: "I need 500Mi, ReadWriteOnce". It is **namespaced**, and
it is what a Pod actually references.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: standard
  resources:
    requests:
      storage: 128Mi
```

```text
Pod ──mounts──► PVC ──bound to──► PV ──backed by──► real storage
     (namespaced, the app's view)   (cluster-scoped, the admin's view)
```

This separation is the design: **the application developer asks for storage without knowing
what provides it.** The same manifest works on minikube (hostPath) and on EKS (EBS) because
only the StorageClass differs.

### The data really does outlive the Pod

```console
$ kubectl logs pvc-writer
persisted by pvc-writer at Wed Oct  7 13:30:51 UTC 2026

$ kubectl delete pod pvc-writer
pod "pvc-writer" deleted

# a completely DIFFERENT pod mounts the SAME claim
$ kubectl logs pvc-reader
--- pvc-reader sees ---
persisted by pvc-writer at Wed Oct  7 13:30:51 UTC 2026
```

### PVC states

| Status | Meaning |
|---|---|
| `Pending` | No matching PV yet — provisioner is working, or nothing matches |
| `Bound` | Matched to a PV and usable |
| `Lost` | The PV it was bound to disappeared |

**`Pending` is the common failure.** `kubectl describe pvc` gives the reason: usually no default
StorageClass, a `storageClassName` typo, or a request larger than any available PV.

---

## 5. StorageClass

A **StorageClass** describes a *kind* of storage the cluster can create on demand. It names the
provisioner and its parameters.

```console
$ kubectl get storageclass
NAME                 PROVISIONER                RECLAIMPOLICY   VOLUMEBINDINGMODE   AGE
standard (default)   k8s.io/minikube-hostpath   Delete          Immediate           3m39s
```

| Field | Value here | Meaning |
|---|---|---|
| `provisioner` | `k8s.io/minikube-hostpath` | The plugin that creates volumes. On AWS: `ebs.csi.aws.com` |
| `reclaimPolicy` | `Delete` | PVs it creates are destroyed with the PVC |
| `volumeBindingMode` | `Immediate` | Bind as soon as the PVC is created |

`(default)` matters: a PVC that omits `storageClassName` gets the default class. With no default
class and no explicit name, the PVC sits in `Pending` forever.

### `volumeBindingMode`

- **`Immediate`** — the PV is created the moment the PVC appears, before any Pod is scheduled.
- **`WaitForFirstConsumer`** — provisioning waits until a Pod using the PVC is scheduled.

The second is important in multi-zone clusters: binding immediately might create the volume in
`us-east-1a` while the scheduler later wants to run the Pod in `us-east-1b`, where it cannot be
attached. Waiting lets the two decisions be made together.

---

## 6. Dynamic provisioning

Without it, an administrator has to pre-create every PV by hand. With it, the StorageClass
creates volumes **on demand**, and this is observable:

```console
# before: nothing exists
$ kubectl get pv
No resources found

# create only the CLAIM
$ kubectl apply -f 03-pvc.yaml
persistentvolumeclaim/data-pvc created

# a PV appeared on its own
$ kubectl get pvc -n s13
NAME       STATUS   VOLUME                                     CAPACITY   STORAGECLASS
data-pvc   Bound    pvc-99c004ac-0408-4f9c-b3ec-31a3877a1056   128Mi      standard

$ kubectl get pv
NAME                                       CAPACITY   RECLAIM POLICY   STATUS   CLAIM          STORAGECLASS
pvc-99c004ac-0408-4f9c-b3ec-31a3877a1056   128Mi      Delete           Bound    s13/data-pvc   standard
```

**I never wrote a PV.** The claim was enough; the provisioner saw it, created a matching volume,
and bound them. The `pvc-<uuid>` naming is the giveaway that it was machine-generated.

### Static vs dynamic

| | **Static** | **Dynamic** |
|---|---|---|
| Who creates the PV | An administrator, in advance | The provisioner, on demand |
| Needs a StorageClass | No | **Yes** |
| Scales to many teams | Poorly | Well |
| Control over the exact backing store | Total | Via StorageClass parameters |
| Typical use | Legacy NFS, pre-existing disks | Everything on a cloud |

---

## Summary

| Type | Lifetime | Scope | Survives pod delete? | Survives node change? | Typical use |
|---|---|---|---|---|---|
| `emptyDir` | The Pod | One Pod | ❌ | ❌ | Scratch, sidecar sharing |
| `hostPath` | The node | One node | ✅ | ❌ | Node agents, DaemonSets |
| PV + PVC | Independent | Cluster / namespace | ✅ | ✅ | Databases, uploads, any real state |

### Choosing

```text
Does the data need to survive the pod?
 ├─ no  → emptyDir
 └─ yes → Is it ABOUT the node (its logs, its metrics)?
            ├─ yes → hostPath (in a DaemonSet)
            └─ no  → PVC
                       ├─ cluster has a StorageClass → dynamic provisioning
                       └─ no StorageClass            → admin pre-creates a PV
```

### Lessons from the runs

1. **`emptyDir` is per-Pod, not per-container** — that is what makes sidecar patterns work.
2. **`hostPath` data survived the Pod but belongs to the node**, which is exactly why it breaks
   as soon as the Pod reschedules elsewhere.
3. **A PVC is a request, a PV is the supply**, and dynamic provisioning builds the supply
   automatically — I created a claim and a PV appeared with no action from me.
4. **The PVC is the durable thing from the app's point of view.** Two unrelated Pods, one claim,
   same data.
