# AWS EC2 — Elastic Compute Cloud

**Name:** Hemang · **Enrollment number:** 24bcs10209

## What is EC2?

Virtual machines on demand. You choose the image, the size and the network, and pay per second
while it runs. It is the most "lift-and-shift" of AWS compute — full OS control, and full
responsibility for patching it.

## AMI — Amazon Machine Image

The template an instance boots from: OS, pre-installed software, and the block device mapping.
Sources: AWS-provided (Amazon Linux, Ubuntu), Marketplace, or your own — typically **baked with
Packer** so every instance starts identical. An AMI is **region-specific**; copy it to use
elsewhere.

## Instance types

Named `family.generation.size`, e.g. `t3.micro`, `m6i.large`:

| Family | Optimised for | Example use |
|---|---|---|
| **T** | Burstable, cheap | Dev boxes, low-traffic sites |
| **M** | Balanced | General app servers |
| **C** | Compute | Batch, encoding, game servers |
| **R / X** | Memory | Databases, in-memory caches |
| **I / D** | Storage I/O | NoSQL, data warehouses |
| **G / P** | GPU | ML training, inference |

T-family instances earn **CPU credits** when idle and spend them when busy — a sustained-load
workload on a `t3` will throttle once credits run out, which surprises people.

### Purchasing options

| Option | Discount | Trade-off |
|---|---|---|
| On-Demand | — | Most flexible, most expensive |
| Savings Plans / Reserved | up to ~72% | 1–3 year commitment |
| **Spot** | up to ~90% | Can be reclaimed with a 2-minute warning |
| Dedicated Host | premium | Compliance / licensing |

## Key pairs

SSH public/private keys. AWS stores the **public** half and injects it into the instance; you
keep the private half — **AWS cannot recover it**. Lose it and you must detach the root volume
or use EC2 Instance Connect / SSM Session Manager.

> Better practice: **SSM Session Manager** instead of SSH. No key pairs, no port 22 open, no
> bastion — and every session is logged to CloudTrail.

## Security Groups

A **stateful** virtual firewall at the instance (ENI) level.

- **Allow rules only** — you cannot write a deny rule.
- **Stateful**: allow traffic in and the reply is automatically permitted out.
- Default: all inbound denied, all outbound allowed.
- A rule's source can be **another security group**, which is the clean way to say "only the web
  tier may reach the database tier" without hardcoding IPs.

Contrast with **NACLs**, which are stateless, subnet-level, and support deny rules.

## EBS — Elastic Block Store

Network-attached block storage that persists independently of the instance.

| Type | Use |
|---|---|
| `gp3` | General purpose SSD — the default; IOPS tunable independently of size |
| `io2` | High-IOPS SSD for demanding databases |
| `st1` / `sc1` | Throughput / cold HDD for big sequential data |

- **Snapshots** are incremental, stored in S3, and are how you back up and clone volumes.
- **Encrypt by default** — it is free and transparent.
- An EBS volume lives in **one AZ**; moving it means snapshot → restore.
- **Instance store** is different: physically attached, very fast, and **wiped on stop**.

## Public vs private IP

| | Public IP | Private IP | Elastic IP |
|---|---|---|---|
| Reachable from internet | Yes | No | Yes |
| Survives a stop/start | **No — it changes** | Yes | **Yes** |
| Cost | Free while attached | Free | Charged when *not* in use |

An instance in a private subnet reaches the internet outbound through a **NAT Gateway** while
remaining unreachable inbound — the standard pattern for application and database tiers.

## Instance lifecycle

```text
pending → running ⇄ stopping/stopped → shutting-down → terminated
```

- **Stop**: EBS-backed only. Compute billing stops; EBS still charged; **public IP is lost**.
- **Hibernate**: RAM is written to the root volume and restored on start.
- **Terminate**: gone. Root volume deleted unless `DeleteOnTermination=false`.

**Termination protection** is worth enabling on anything that matters.

## Common use cases

Web/app servers behind an ALB in an Auto Scaling Group · batch processing on Spot · legacy
software that needs a full OS · bastion hosts (or better, SSM) · GPU training jobs.
