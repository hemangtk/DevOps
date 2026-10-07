# Troubleshooting exercises

**Name:** Hemang · **Enrollment number:** 24bcs10209

Two deliberately broken manifests. Apply one, diagnose it, fix it, verify.

| File | Symptom | Where the answer is |
|---|---|---|
| [`broken-image.yaml`](broken-image.yaml) | `ImagePullBackOff` | `kubectl describe pod` → Events |
| [`broken-service.yaml`](broken-service.yaml) | Service resolves but nothing answers | `kubectl get endpoints` → `<none>` |

The method, and nine worked examples, are in
[the Kubernetes Troubleshooting topic](../../../Kubernetes%20Troubleshooting/).

## The rule that matters most

**Pod status tells you which tool to reach for.** If the container never
started, `kubectl logs` has nothing — the answer is in `describe`:

| STATUS | Container started? | Look at |
|---|---|---|
| `Pending` | No | `describe` → scheduler Events |
| `ImagePullBackOff` | No | `describe` → pull Events |
| `CreateContainerConfigError` | No | `describe` → waiting message |
| `CrashLoopBackOff` | **Yes**, then died | `logs --previous` |
| `Running` but `0/1` | Yes | `describe` → readiness probe Events |
