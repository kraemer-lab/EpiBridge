# EpiBridge
[![EpiBridge](https://github.com/kraemer-lab/EpiBridge/actions/workflows/EpiBridge.yml/badge.svg)](https://github.com/kraemer-lab/EpiBridge/actions/workflows/EpiBridge.yml)

Secure remote analysis for sensitive epidemiological data.

EpiBridge is a platform that allows researchers to analyse sensitive datasets without the data ever leaving the host institution.

Researchers develop analyses locally using schema documentation and synthetic datasets, submit analysis bundles to EpiBridge, and receive approved outputs after execution within a secure environment.

**Move the computation to the data, not the data to the computation.**

---

## Quick Start

**Requirements**: Git, OrbStack, Make.

No other host dependencies are required. Python, Node.js, and PostgreSQL all run inside the platform.

### Installation

```bash
git clone https://github.com/kraemer-lab/EpiBridge.git

cd EpiBridge

make install
```

This creates an OrbStack VM (if needed), installs EpiBridge, creates the administrator account, publishes institutional assets, and leaves the platform running.

On the first installation, `.env` is created automatically with secure defaults. The administrator password is stored as `ADMIN_PASSWORD` in this file and is never displayed in the terminal. Subsequent installations reuse the existing configuration.

To install into a different target:

```bash
make install TARGET=native    # native Docker (no VM)
```

### Evaluation

```bash
make demo
```

This creates evaluation accounts (researcher, moderator, maintainer) and prints a welcome message with credentials and next steps.

Once evaluation accounts are ready, follow the guided tutorial:

```
docs/quickstart.md
```

---

## Configuration

The only user-facing configuration file is `.env`, created automatically by `make install`. It contains installation-specific settings:

- `ADMIN_PASSWORD` — the administrator account password (generated)
- `POSTGRES_PASSWORD` and `REDIS_PASSWORD` — database credentials (generated)
- `SECRET_KEY` — application signing key (generated)
- `DOMAIN` — deployment domain (default: `localhost`)
- Optional SMTP configuration for email notifications

To regenerate all secrets, delete `.env` and run `make install` again.

---

## Public lifecycle

| Command | Purpose |
|---------|---------|
| `make install` | Install EpiBridge (default: OrbStack VM; use `TARGET=native` for native Docker) |
| `make demo` | Prepare an evaluation environment |
| `make dev` | Daily development workflow |
| `make uninstall` | Remove the local EpiBridge installation |

`make uninstall` stops the platform, deletes the OrbStack VM (or Docker resources), and preserves the repository and `.env`. To fully reset, delete `.env` and the OrbStack VM manually before reinstalling.

---

## Development

After installation, `make dev` is the normal edit–build–run workflow for contributors. It rebuilds and restarts application services without reseeding users or institutional state.

```bash
make dev
```

See `vm/runtime.md` for the development environment reference.

---

## Where next?

| Document | Purpose |
|----------|---------|
| `docs/quickstart.md` | Guided tutorial through the institutional workflow |
| `docs/architecture.md` | System architecture and trust boundaries |
| `docs/security.md` | Security model and threat analysis |
| `docs/api.md` | API reference |
| `docs/testing.md` | Testing strategy and test runner reference |
| `vm/runtime.md` | Deployment runtime specification |

---

## Features

* Secure user authentication
* Project-based access control
* Analysis job submission
* Human approval before execution
* Isolated container execution
* Human approval before output release
* Complete audit trail
* Cloud-ready architecture

## Technology

* Frontend: Next.js + React + TypeScript
* Backend: FastAPI
* Database: PostgreSQL
* Queue: Redis
* Worker: Python
* Execution: Docker
* Authentication: Local Identity Provider (Argon2, server-side sessions)

## Repository Structure

```
frontend/    Next.js application
backend/     FastAPI application
worker/      Python job executor
execution-environments/  Base images and execution contracts
scripts/     Orchestration scripts
docs/        Architecture, security, API, and testing documentation
examples/    Synthetic datasets, analysis templates, and environment definitions
vm/          Cloud-init configuration and runtime specification
resources/   Institutional resource publications
```
