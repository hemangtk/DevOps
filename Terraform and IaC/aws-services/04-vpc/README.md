# AWS VPC — Virtual Private Cloud

**Name:** Hemang · **Enrollment number:** 24bcs10209

## What is a VPC?

Your own logically isolated network inside AWS. You choose the IP range, carve it into subnets,
and control routing and firewalling. Nothing talks to anything unless the routing *and* the
security rules both allow it.

## CIDR

A VPC is defined by a CIDR block, e.g. `10.0.0.0/16`:

```text
10.0.0.0/16   = 65,536 addresses   (the whole VPC)
10.0.1.0/24   =     256 addresses  (one subnet)
```

The prefix is how many bits are fixed; the rest are host addresses. **AWS reserves 5 addresses
per subnet** (network, VPC router, DNS, future, broadcast), so a `/24` gives you 251 usable.

Pick non-overlapping ranges from RFC1918 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) —
overlapping CIDRs make VPC peering impossible later.

## Subnets

A slice of the VPC CIDR, pinned to **one Availability Zone**. Multi-AZ means at least one subnet
per AZ.

| | **Public subnet** | **Private subnet** |
|---|---|---|
| Route table has | A route to an **Internet Gateway** | No IGW route; usually a NAT route |
| Instances get | A public IP (optionally) | Private IPs only |
| Reachable from internet | Yes | No |
| Typical contents | ALB, NAT Gateway, bastion | App servers, databases |

**The only thing that makes a subnet "public" is an IGW route in its route table.** There is no
flag.

## Route tables

```text
Destination       Target
10.0.0.0/16       local            ← always present, cannot be removed
0.0.0.0/0         igw-xxxx         ← this line makes the subnet PUBLIC
```

Most specific prefix wins. The `local` route is what lets every subnet in the VPC talk to every
other by default.

## Internet Gateway (IGW)

Horizontally scaled, redundant, free. One per VPC. It does two things: provides a route to the
internet, and performs 1:1 NAT between a private IP and its public/Elastic IP.

An instance needs **all three** to be internet-reachable: a public IP, an IGW route, and
permissive security group rules.

## NAT Gateway

Lets instances in **private** subnets make **outbound** connections (package updates, API calls)
while remaining unreachable inbound.

- Lives in a **public** subnet, needs an Elastic IP.
- **Charged per hour and per GB** — often a surprising share of a bill.
- One per AZ for high availability (a single NAT is an AZ-level single point of failure).
- **VPC Endpoints** avoid NAT entirely for AWS services: a Gateway Endpoint for S3/DynamoDB is
  free and keeps traffic off the internet.

## Security Groups vs NACLs

| | **Security Group** | **NACL** |
|---|---|---|
| Level | Instance / ENI | Subnet |
| State | **Stateful** — replies auto-allowed | **Stateless** — need both directions |
| Rules | Allow only | Allow **and deny** |
| Evaluation | All rules together | Numbered, first match wins |
| Default | Deny in, allow out | Allow everything |

Use security groups for almost everything. Reach for NACLs to block a specific IP range at the
subnet edge — that is the one thing SGs cannot do.

## A standard three-tier layout

```text
VPC 10.0.0.0/16
├── AZ-a
│   ├── public  10.0.1.0/24   → ALB, NAT Gateway        → route 0.0.0.0/0 → IGW
│   ├── private 10.0.11.0/24  → app servers             → route 0.0.0.0/0 → NAT
│   └── private 10.0.21.0/24  → RDS                     → no internet route at all
└── AZ-b
    ├── public  10.0.2.0/24
    ├── private 10.0.12.0/24
    └── private 10.0.22.0/24
```

Security groups chained by reference: `alb-sg` → `app-sg` → `db-sg`, so each tier only accepts
traffic from the one above it. This is the same isolation idea demonstrated with Docker networks
in [Docker Networks](../../../Docker%20Networks/#task-1--container-networking) — the frontend
could not reach the database because they shared no network.
