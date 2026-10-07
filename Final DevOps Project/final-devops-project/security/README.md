# Security controls in this project

**Name:** Hemang · **Enrollment number:** 24bcs10209

| Control | Where | What it does |
|---|---|---|
| **SAST** (bandit) | CI | Scans our Python for insecure patterns |
| **SCA** (pip-audit) | CI | Known CVEs in dependencies |
| **Secret scanning** (gitleaks) | CI | Credentials in git history |
| **Image scanning** (Trivy) | CI | CVEs in the image's OS packages |
| **Security gate** | CI | Deploy cannot run unless all of the above pass |
| `runAsNonRoot` / `runAsUser: 10001` | `kubernetes/04-app.yaml` | No root inside the container |
| `readOnlyRootFilesystem: true` | same | Attacker cannot write a binary |
| `capabilities.drop: ["ALL"]` | same | No Linux capability escalation |
| `allowPrivilegeEscalation: false` | same | No setuid escalation |
| `seccompProfile: RuntimeDefault` | same | Restricts syscalls |
| **NetworkPolicy** | `kubernetes/07-networkpolicy.yaml` | Only app pods may reach Postgres:5432 |
| **Secret, not ConfigMap** | `kubernetes/02-secret.yaml` | DB credentials separated from plain config |
| Non-root user in the image | `docker/Dockerfile` | `useradd --uid 10001`, `USER 10001` |
| Multi-stage build | `docker/Dockerfile` | Build wheels discarded from the runtime image |

## Known gap, stated honestly

`kubernetes/02-secret.yaml` is **committed to git**, which the
[DevSecOps topic](../../../DevSecOps/#3-secret-scanning--gitleaks) explicitly warns against. It
holds obviously fake demo values and is allowlisted in the gitleaks config. In production this
file would be replaced by **Sealed Secrets**, the **External Secrets Operator**, or a cloud
secret store, so no credential — real or otherwise — lives in the repository.
