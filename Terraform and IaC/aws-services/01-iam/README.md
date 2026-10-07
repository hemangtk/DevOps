# AWS IAM — Identity and Access Management

**Name:** Hemang · **Enrollment number:** 24bcs10209

## What is IAM?

IAM controls **who** can do **what** to **which** AWS resources. It is global (not regional),
free, and every single AWS API call is authorised through it. Get IAM wrong and nothing else
matters.

Four building blocks:

| Object | What it is |
|---|---|
| **User** | A long-lived identity for a person or legacy app. Has a password and/or access keys. |
| **Group** | A bucket of users. Policies attach here, not to individuals. Groups cannot nest. |
| **Role** | An identity with **no permanent credentials**, *assumed* temporarily. The modern default. |
| **Policy** | A JSON document granting or denying permissions. Attached to users, groups or roles. |

## Policy anatomy

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "ReadCourseworkBucket",
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:ListBucket"],
    "Resource": [
      "arn:aws:s3:::devops-coursework-24bcs10209",
      "arn:aws:s3:::devops-coursework-24bcs10209/*"
    ],
    "Condition": { "IpAddress": { "aws:SourceIp": "203.0.113.0/24" } }
  }]
}
```

- **Effect** — `Allow` or `Deny`
- **Action** — the API calls, wildcards allowed (`s3:Get*`)
- **Resource** — ARNs. Note a bucket and its *objects* are two different ARNs — forgetting the
  `/*` is the classic S3 policy bug.
- **Condition** — optional extra constraints (source IP, MFA present, tag match)

### Evaluation logic

```text
Explicit DENY anywhere  ─────────────► DENIED   (always wins, nothing overrides it)
       │ no
Explicit ALLOW present? ──no────────► DENIED   (implicit deny is the default)
       │ yes
                                      ALLOWED
```

## Permissions boundaries, SCPs and the policy types

| Type | Purpose |
|---|---|
| **Identity-based** | Attached to a user/group/role — "this identity can do X" |
| **Resource-based** | Attached to the resource (S3 bucket policy) — "these principals can use me" |
| **Permissions boundary** | A ceiling: the maximum an identity *could* be granted |
| **SCP** (Organizations) | An account-wide ceiling across every identity in the account |

## Least privilege

Grant only what is needed, then widen on evidence:

1. Start from a managed policy that is close, or from nothing.
2. Run the workload; read **CloudTrail** / IAM Access Analyzer for what it actually called.
3. Narrow `Action` and `Resource` to that set.
4. Re-check periodically — IAM Access Analyzer flags unused permissions.

## Best practices

- **Never use the root account** for daily work. Enable MFA on it, lock the keys away.
- **Prefer roles over users.** An EC2 instance role or an EKS IRSA role gets rotating temporary
  credentials; a user's access key is a permanent secret waiting to be leaked.
- **No long-lived access keys in CI.** Use OIDC — GitHub Actions can assume a role directly, with
  no stored secret. This is the same reasoning as the OIDC note in
  [DevSecOps](../../../DevSecOps/#7-secrets).
- **Attach policies to groups**, not individuals.
- **MFA everywhere**, and condition sensitive actions on `aws:MultiFactorAuthPresent`.
- **Rotate and audit**: credential report, Access Analyzer, CloudTrail.

## Common use cases

| Need | Solution |
|---|---|
| An app on EC2 reads S3 | **Instance profile role** — no keys on disk |
| A Lambda writes to DynamoDB | **Execution role** |
| CI deploys to AWS | **OIDC federated role**, no stored secret |
| Cross-account access | A role in account B with account A as trusted principal |
| A contractor needs read-only for 2 weeks | Role with a session duration + a permissions boundary |
