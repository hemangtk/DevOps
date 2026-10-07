# AWS S3 — Simple Storage Service

**Name:** Hemang · **Enrollment number:** 24bcs10209

Everything here maps to the bucket actually built in
[`../../terraform-s3-demo/`](../../terraform-s3-demo/).

## What is S3?

Object storage: you `PUT` and `GET` whole objects by key over HTTP. It is **not** a filesystem —
there is no partial write, no rename, no real directories. In exchange you get effectively
unlimited capacity and 99.999999999% (11 nines) durability.

## Buckets

- **Globally unique name** across all of AWS — hence the `-24bcs10209` suffix on mine.
- Lives in **one region**; data does not leave it unless you replicate.
- Naming: lowercase, 3–63 chars, no underscores. The Terraform project enforces this with a
  `validation` block:

```hcl
validation {
  condition     = can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.bucket_name))
  error_message = "Bucket names must be lowercase, 3-63 chars, and start/end alphanumeric."
}
```

## Objects

Key + value + metadata. Up to 5 TB each (multipart upload above 5 GB).

**There are no folders.** `hello/README.txt` is a *key containing a slash*; the console renders
it as a folder. This matters when writing IAM policies and lifecycle prefixes.

## Storage classes

| Class | Retrieval | Use |
|---|---|---|
| **Standard** | instant | Hot data |
| **Intelligent-Tiering** | instant | Unpredictable access — moves objects automatically |
| **Standard-IA** | instant, per-GB fee | Backups, older logs |
| **One Zone-IA** | instant | Re-creatable data; cheaper, one AZ |
| **Glacier Instant** | instant | Archives needing occasional immediate access |
| **Glacier Flexible** | minutes–hours | Long-term archive |
| **Glacier Deep Archive** | ~12 hours | Compliance, 7-year retention |

IA classes have a **minimum billable duration** (30 days) — churning small objects through them
costs *more* than Standard.

## Versioning

```hcl
resource "aws_s3_bucket_versioning" "coursework" {
  versioning_configuration { status = "Enabled" }
}
```

```console
$ aws s3api get-bucket-versioning --bucket devops-coursework-24bcs10209
{ "Status": "Enabled" }
```

Every overwrite keeps the old version; a delete writes a **delete marker** rather than removing
data. This is the main defence against accidental deletion and ransomware. Once enabled it can
only be *suspended*, never turned off — and old versions keep costing money, which is what
lifecycle rules are for.

## Lifecycle policies

```hcl
rule {
  id     = "expire-noncurrent-versions"
  status = "Enabled"
  noncurrent_version_expiration { noncurrent_days = 30 }
}
```

```console
$ aws s3api get-bucket-lifecycle-configuration --bucket devops-coursework-24bcs10209
{ "Rules": [{ "ID": "expire-noncurrent-versions", "Status": "Enabled",
              "NoncurrentVersionExpiration": { "NoncurrentDays": 30 } }] }
```

Rules can transition between storage classes, expire current or non-current versions, and clean
up incomplete multipart uploads — the last one is a common source of invisible cost.

## Encryption

```hcl
rule {
  apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
}
```

```console
$ aws s3api get-bucket-encryption --bucket devops-coursework-24bcs10209
"ApplyServerSideEncryptionByDefault": { "SSEAlgorithm": "AES256" }
```

| Mode | Key management |
|---|---|
| **SSE-S3** (`AES256`) | AWS-managed. Free, on by default. |
| **SSE-KMS** | Your KMS key — adds an audit trail and per-key access control |
| **SSE-C** | You supply the key on every request |
| Client-side | Encrypt before upload |

Enforce **in transit** too with a bucket policy denying `aws:SecureTransport = false`.

## Bucket policies and public access

```hcl
resource "aws_s3_bucket_public_access_block" "coursework" {
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

```console
$ aws s3api get-public-access-block --bucket devops-coursework-24bcs10209
"BlockPublicAcls": true, "IgnorePublicAcls": true,
"BlockPublicPolicy": true, "RestrictPublicBuckets": true
```

**This is the single most important S3 setting.** Public buckets are the most common cause of
cloud data breaches. Block it at the bucket *and* account level, and serve public content through
**CloudFront with an Origin Access Control** instead.

For temporary access, use a **pre-signed URL** — a time-limited signed link — never a public ACL.

## Common use cases

Static website hosting (behind CloudFront) · backups and archives · data lake storage for
Athena/Glue · application uploads · **Terraform remote state** (with DynamoDB for locking) ·
log destination for CloudTrail, ALB and VPC flow logs.
