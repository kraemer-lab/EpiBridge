# AGENTS.md

## Project status — backend scaffolded, rest is stubs

### Exists and functional

```
backend/         FastAPI scaffold (app entrypoint, health endpoint, SQLAlchemy,
                 Alembic, config, Firebase auth stub, CLI seed-admin stub)
vm/              cloud-init.yaml, Caddyfile (HTTPS, HSTS, compression,
                 security headers, request size limits), runtime spec
scripts/         bootstrap.sh, install.sh, upgrade.sh, backup.sh, restore.sh, healthcheck.sh
docker-compose.yml  6 services (postgres, redis, backend, worker, frontend,
                    reverse-proxy), internal + frontend networks
docs/            Architecture, security, API, vision docs
```

### Still needs creating

```
frontend/        Next.js + React + TypeScript (nginx stub serving static HTML)
worker/          Python job executor (stub — sleeps)
shared/          Shared schemas and types (not started)
containers/      Base analysis Docker images (not started)
examples/        Synthetic datasets + analysis templates (not started)
```

### Intended architecture (from docs/)

```
frontend/    Next.js + React + TypeScript
backend/     FastAPI + SQLAlchemy + Alembic + PostgreSQL
worker/      Python job executor
shared/      Shared schemas and types across packages
containers/  Base analysis Docker images
examples/    Synthetic datasets and analysis templates
docs/        Architecture, security, API, roadmap, vision
```

Single monorepo. Do not add top-level directories without justification.

### Foreseen conventions (documented, not yet enforced)

- Backend: FastAPI dependency injection, business logic in `services/`, thin endpoints, SQLAlchemy ORM, Pydantic models
- Frontend: App Router, TypeScript, server components where appropriate, functional components

### Security constraints (must preserve in implementation)

- Researchers never get direct dataset access
- All analysis executes through the Worker in isolated Docker containers
- Datasets mounted read-only in containers
- Two-stage approval: execution approval then output approval
- Never bypass the approval workflow
- Use `Storage` and `Executor` interfaces (not coupling directly to Docker)
- Firebase Auth for auth, internal PostgreSQL for authorisation
- Audit trail required for all actions

### Temporary development policy (domain model iteration phase)

While the core domain schema is still being discovered (Projects, Jobs, Outputs, etc.):

- **SQLAlchemy models are the source of truth** for the database schema.
- **No Alembic migrations are maintained.** Migration files are not generated or committed.
- **Schema is auto-created** on backend startup via `Base.metadata.create_all()` when `AUTO_CREATE_SCHEMA=true` (default).
- **Development databases are disposable.** Drop and recreate freely.

Once the core schema stabilises, Alembic will be reintroduced as a dedicated milestone:
- A single initial migration will be generated from the stable schema.
- All future schema changes will use Alembic migrations.
- `AUTO_CREATE_SCHEMA` will be set to `false` in production-like environments.

### Developer commands

The standard development workflow:

```bash
make dev          # bootstrap the full stack
# During development
make format       # auto-format code
make lint         # static analysis
make test         # run tests
```

**Backend** (from `backend/`):
- `pip install -e ".[dev]"` — install dependencies (including dev tools)
- `uvicorn app.main:app --reload` — dev server (auto-creates schema on startup)
- `python -m app.cli seed-admin` — seed admin user

**Infrastructure** (from repo root):
- `./scripts/bootstrap.sh` — single entry point (clone → install → verify)
- `./scripts/install.sh` — first-time install
- `./scripts/upgrade.sh` — application upgrade
- `./scripts/backup.sh` — database + data backup
- `./scripts/restore.sh <file>` — restore from backup
- `./scripts/healthcheck.sh` — verify services

**Makefile targets** (portable, assumes SSH access to an Ubuntu VM):
- `make install` — run install.sh
- `make up` — docker compose up -d
- `make down` — docker compose down
- `make upgrade` — run upgrade.sh
- `make backup` — run backup.sh
- `make restore FILE=<file>` — restore from backup

**Code quality** (from repo root):
- `make format` — auto-format code (ruff for Python)
- `make lint` — static analysis (ruff check)
- `make fix` — auto-fix all fixable issues (run this most often)

**Testing** (from repo root):
- `make test` — run unit, integration, and smoke test suites (CI compatible)
- `make dev-test` — run full suite inside the container via SSH (requires dev stack)
- `python -m pytest backend/tests/unit -v` — unit tests only
- `python -m pytest backend/tests/integration -v` — integration tests (requires DB + Redis running)
- `python -m pytest backend/tests/smoke -v` — smoke tests (requires full stack running)

**Makefile dev targets** (OrbStack-specific, uses `scripts/orbstack.sh` under the hood):
- `make dev` — one-command: create VM, mount repo, install, start, verify
- `make dev-install` — install with `--dev` flag (individual step)
- `make dev-up` — start services (individual step)
- `make dev-down` — stop services (individual step)
- `make dev-shell` — interactive VM shell (individual step)
- `make dev-logs` — tail container logs (individual step)
- `make clean` — factory reset (remove containers, volumes, VM, .env)
- `make dev-build SVC=frontend` — rebuild and restart a single service (fastest iteration)

**VM / Dev environment** (see `vm/runtime.md`):
- `scripts/orbstack.sh` — OrbStack-specific helpers (create, mount, ssh, ip)

### Stack dependencies

Backend requires Python 3.11+. No other language runtimes or build tools have been installed. Stand up each package independently before wiring integration tests.
