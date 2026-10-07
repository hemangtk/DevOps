# AWS Database Services — DynamoDB and RDS

**Name:** Hemang · **Enrollment number:** 24bcs10209

Two managed database services that solve different problems. The choice is mostly about whether
your access patterns are known in advance.

---

# DynamoDB

## NoSQL

A fully managed key-value and document store. No servers, no version upgrades, single-digit
millisecond latency at any scale. The trade-off: **you design the table around your queries**,
not around the data.

| | Relational | DynamoDB |
|---|---|---|
| Schema | Fixed, defined up front | Schema-less beyond the key |
| Joins | Yes | **No** — you denormalise instead |
| Scaling | Mostly vertical | Horizontal, automatic |
| Query flexibility | Any query via SQL | Only by key, or via an index |

## Tables, items, attributes

```text
Table: Orders
├── Item  { OrderId: "A-1001", CustomerId: "C-42", Total: 250, Status: "shipped" }
└── Item  { OrderId: "A-1002", CustomerId: "C-42", Total: 90,  Gift: true }
```

- **Table** — a collection of items
- **Item** — one row, up to 400 KB
- **Attribute** — one field. Items in the same table need not share attributes (note `Gift`
  exists on only one item above).

## Partition key and sort key

The **primary key** is either:

| | Composition | Behaviour |
|---|---|---|
| **Simple** | Partition key only | Must be unique; one item per key |
| **Composite** | Partition key + **sort key** | Many items per partition, sorted and range-queryable |

The **partition key** is hashed to choose a physical partition — so it must have **high
cardinality and even access**. A partition key of `Status` with three values creates a *hot
partition* and throttles.

A composite key `(CustomerId, OrderDate)` lets you ask "all orders for customer C-42 in March"
efficiently — one partition, a range scan on the sort key.

**Indexes** when the base key isn't enough:
- **LSI** — same partition key, different sort key. Must be created with the table.
- **GSI** — completely different key. Can be added later; eventually consistent.

**Scan is the enemy**: it reads every item. Design so you always `Query` by key.

## Capacity

- **On-demand** — pay per request, no planning. Best for spiky or unknown load.
- **Provisioned** — cheaper at steady load, with auto-scaling.

## Use cases

Session stores · shopping carts · IoT telemetry · leaderboards · event sourcing ·
**Terraform state locking** alongside an S3 backend.

---

# RDS

## Relational database, managed

AWS runs the engine: provisioning, patching, backups, failover, replicas. You still own schema
design and query performance.

**Engines:** PostgreSQL · MySQL · MariaDB · Oracle · SQL Server · Aurora (AWS's own
MySQL/PostgreSQL-compatible engine, faster and more scalable, with Serverless v2 for variable
load).

## DB instances

Sized like EC2 (`db.t3.micro`, `db.r6g.large`) with an EBS volume underneath. Scaling up means
changing the instance class — usually with a short failover window.

## Security

- Put it in a **private subnet** with no internet route.
- A **security group** that only accepts 5432/3306 **from the application's security group** —
  never from `0.0.0.0/0`.
- **Encryption at rest** (KMS) must be chosen at creation; you cannot enable it later without a
  snapshot-restore.
- TLS in transit; **IAM database authentication** or **Secrets Manager** with automatic rotation
  instead of a password in a config file.

## Backups

| Mechanism | Nature |
|---|---|
| **Automated backups** | Daily snapshot + transaction logs → **point-in-time recovery**, up to 35 days |
| **Manual snapshots** | Kept until you delete them |

PITR lets you restore to any second in the window — which is what saves you from a bad
`DELETE` at 3am. Restores always create a **new instance**.

## Multi-AZ

A **synchronous standby in another AZ**. Not a performance feature — the standby serves no
traffic. On failure AWS fails over automatically (~60–120s) by repointing the DNS endpoint.
This is why applications should connect to the **endpoint name**, never an IP.

## Read replicas

**Asynchronous** copies that *do* serve read traffic. Up to 15, cross-region possible, and
promotable to standalone.

| | Multi-AZ | Read replica |
|---|---|---|
| Purpose | **Availability** | **Read scaling** |
| Replication | Synchronous | Asynchronous |
| Serves traffic | No | Yes, reads only |
| Failover | Automatic | Manual promotion |

They are complementary: Multi-AZ for survival, replicas for load.

## Use cases

Traditional applications needing joins and transactions · reporting · anything with an existing
SQL schema · ecommerce and finance where ACID matters.

---

# Choosing

```text
Do you need joins, transactions, ad-hoc SQL?
 ├── yes → RDS (Aurora if you want the scaling headroom)
 └── no  → Are access patterns known and key-based?
             ├── yes, and scale/latency matter → DynamoDB
             └── no, queries will change       → RDS
```

The honest rule: **DynamoDB is excellent when you know your queries up front and brutal when you
don't.** Adding an unanticipated query pattern to a relational database is a new `SELECT`; in
DynamoDB it can mean a new GSI or a table redesign.
