# DevOps Coursework

**Name:** Hemang
**Enrollment number:** 24bcs10209

Homework and practicals for the DevOps module, one folder per topic. Every command in these
notes was actually run on this machine and the output pasted in unedited, with screenshots
alongside.

| Folder | Topic | Homework covered |
|---|---|---|
| [`Linux Fundamentals/`](Linux%20Fundamentals/) | Hard vs soft links, `useradd` vs `adduser`, `journalctl`, command cheat sheet | Tasks 1–4 |
| [`Shell Scripting/`](Shell%20Scripting/) | `sysinfo.sh` — variables, `read -p`, `mkdir`/`touch`, `>` redirection | System Information Script |
| [`Networking Fundamentals/`](Networking%20Fundamentals/) | `ping`, `ip a`, `ip route`, `ss`, `netstat`, `nc`, `curl`, `wget`, `nslookup`/`dig`, `traceroute`, `hostname` | Tasks 1–2 |
| [`Git and Github/`](Git%20and%20Github/) | `git commit -a -m` vs `-m`, `git cherry-pick` | Tasks 1–2 |
| [`Docker Fundamentals/`](Docker%20Fundamentals/) | Six Hello World containers: Node.js, Python, Java, Apache, React, Nginx | Hello World Applications |
| [`DockerFiles and Images/`](DockerFiles%20and%20Images/) | Multi-stage Go build — 467 MB toolchain down to a 6.98 MB image, on port 8080 | Tasks 1–3 |
| [`Docker Networks/`](Docker%20Networks/) | Three-tier networks, host network, bind mounts, overlay networks | Tasks 1–4 |

Each folder has its own README with the commands, the real output, an explanation of what the
output means, and screenshots.

---

## Highlights

- **Six containerised Hello World apps**, each in its own folder with its own Dockerfile, all
  built, run and verified in a browser — [`Docker Fundamentals/`](Docker%20Fundamentals/)
- **A multi-stage build that takes the same Go app from 467 MB to 6.98 MB**, a 67× reduction,
  with `docker history` and a missing `/bin/sh` proving what was left out —
  [`DockerFiles and Images/`](DockerFiles%20and%20Images/)
- **A three-tier network where the frontend genuinely cannot reach the database**, shown with a
  real MySQL query from the backend and an `NXDOMAIN` from the frontend —
  [`Docker Networks/`](Docker%20Networks/)
- **A live overlay network** created in swarm mode, with a two-replica service behind one
  virtual IP — [`Docker Networks/`](Docker%20Networks/#task-4--overlay-network)

---

## Environment

- macOS (Apple Silicon), Docker Desktop **29.5.2**
- Linux-only commands (`useradd`, `adduser`, `journalctl`, `ip`, `ss`) were run in **Ubuntu
  24.04** containers. The `journalctl` task needs a live `systemd`, so it used a container
  booted with `/sbin/init` as PID 1 — see
  [`Linux Fundamentals/Dockerfile.systemd`](Linux%20Fundamentals/Dockerfile.systemd).
- `traceroute` was run on the macOS host, because Docker Desktop's VM drops the probes and
  every hop past the gateway returns `* * *`.

### Ports used

| App | Host port | Container port |
|---|---|---|
| Node.js | 3100 | 3000 |
| React | 3001 | 80 |
| Python / Flask | 5100 | 5000 |
| Java | 8000 | 8000 |
| Go multi-stage | 8080 | 8080 |
| Apache | 8081 | 80 |
| Nginx | 8082 | 80 |
| Nginx (bind mount) | 8090 | 80 |

Node and Python use host ports 3100 and 5100 because 3000 and 5000 were already taken on this
machine.

---

## Reference

Structure and topic breakdown follow the course reference repository
[Jils31/DevOps](https://github.com/Jils31/DevOps). All code, commands, output and screenshots
here are my own runs.
