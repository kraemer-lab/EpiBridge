# AGENTS.md

## Project status — backend scaffolded, rest is stubs

### Exists and functional

```
backend/         FastAPI scaffold (app entrypoint, health endpoint, SQLAlchemy,
                 Alembic, config, Local Identity Provider auth, CLI seed-admin,
                 bundle store, worker execution, Environment Builder subsystem)
containers/      Base analysis Docker images (python-3.13, python-3.14)
vm/              cloud-init.yaml, Caddyfile (HTTPS, HSTS, compression,
                 security headers, request size limits), runtime spec
scripts/         bootstrap.sh, install.sh, upgrade.sh, backup.sh, restore.sh, healthcheck.sh
docker-compose.yml  6 services + optional ollama (--profile ai),
                    internal + frontend + external networks
docs/            Architecture, security, API, vision, AI assistance docs
```

### Still needs creating

```
frontend/        Next.js + React + TypeScript (game in progress)
shared/          Shared schemas and types (not started)
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
- Only the optional AI service (Ollama) has outbound network access, and only for model downloads
- IdentityProvider abstraction for auth, internal PostgreSQL for authorisation
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

### Domain model boundary

- **Institutional assets** (Data Resources, Execution Environments) are registered automatically via lifespan startup from YAML manifests.
- **Researcher artefacts** (Projects, Analysis Bundles, Execution Requests) are created by users through the application.
- **Internal system artefacts** (AIBundleReview, BuildRequest, ExecutionImage) are created by background tasks and workers during platform operation.
- **Environment Builder subsystem** transforms Analysis Bundle dependency specifications into reusable Execution Images via curated Dockerfile templates. Builds are driven by `BuildRequest` work items processed by the worker alongside execution requests. `ExecutionImage` records serve as a content-addressable cache keyed by `(execution_environment_id, dependency_hash)`.
- **Demo workspace** (optional) can be created by `seed-demo` CLI command — a development tool, not application startup logic.
- **Manifest directories** (`RESOURCE_MANIFEST_DIR`, `ENVIRONMENT_MANIFEST_DIR`) are deployment configuration, not application defaults. Docker Compose sets them for development; production points them elsewhere.

### Developer commands

The standard development workflow:

```bash
make dev          # bootstrap the full stack (OrbStack VM)
# During development
make format       # auto-format code
make lint         # static analysis
make test         # run tests
```

**Backend** (from `backend/`):
- `pip install -e ".[dev]"` — install dependencies (including dev tools)
- `uvicorn app.main:app --reload` — dev server (auto-creates schema on startup)
- `python -m app.cli seed-admin` — seed admin user
- `python -m app.cli seed-demo` — seed demo workspace (dev debugging tool)

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
- `make playwright` — run canonical workflow e2e test (requires full stack running)
- `python -m pytest backend/tests/unit -v` — unit tests only
- `python -m pytest backend/tests/integration -v` — integration tests (requires DB + Redis running)
- `python -m pytest backend/tests/smoke -v` — smoke tests (requires full stack running)

**CI** (from repo root, requires Docker):
- `make ci` — bootstrap full stack (build, start, seed), same as `make bootstrap`
- `make ci-clean` — tear down all Docker resources and remove `.env`
- `make playwright` — run canonical workflow e2e test (must be run after `make ci`)

**Shared bootstrap** (from repo root, requires Docker):
- `make bootstrap` — idempotent bootstrap used by both development and CI.
  Generates `.env` if missing, builds images, starts services, seeds admin.
  Safe to run multiple times.

**Makefile dev targets** (OrbStack-specific, uses `scripts/orbstack.sh` under the hood):
- `make dev` — one-command: create VM, mount repo, install, start, verify
- `make dev-ai` — start the optional Ollama service on an already-running stack
- `make dev-install` — install with `--dev` flag (individual step)
- `make dev-up` — start services (individual step)
- `make dev-down` — stop services (individual step)
- `make dev-shell` — interactive VM shell (individual step)
- `make dev-logs` — tail container logs (individual step)
- `make clean` — factory reset (remove containers, volumes, VM, .env)
- `make clean-db` — reset database (all researcher artefacts dropped, schema recreated on next startup)
- `make dev-build SVC=frontend` — rebuild and restart a single service (fastest iteration)

**VM / Dev environment** (see `vm/runtime.md`):
- `scripts/orbstack.sh` — OrbStack-specific helpers (create, mount, ssh, ip)

### Canonical Workflow (end-to-end)

The canonical workflow is a single Playwright e2e test that proves the entire platform works from a researcher's perspective.

```bash
make dev           # bootstrap the full stack (OrbStack VM)
make playwright    # run the canonical workflow e2e test
```

The test (in `frontend/e2e/canonical-workflow.spec.ts`) validates:
1. Opening EpiBridge
2. Login with admin credentials
3. Creating a project
4. Attaching a data resource to the project
5. Creating an analysis and uploading a bundle
6. Running the analysis
7. Waiting for PENDING → RUNNING → COMPLETED status transition
8. Opening the Outputs tab
9. Downloading `summary.csv`
10. Verifying the file exists and is non-empty

This is a system test — not UI, not API — covering frontend, backend, database, worker, Docker executor, provider abstraction, runtime contract, output registration, and download endpoint.

### Stack dependencies

Backend requires Python 3.11+. No other language runtimes or build tools have been installed. Stand up each package independently before wiring integration tests.
