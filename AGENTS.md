# AGENTS.md

## Project status — Milestone 17 complete (Audit & Provenance)

### Exists and functional

```
backend/         FastAPI: identity model (User, Role, Capability,
                 ProjectMembership), capability-based policy, SQLAlchemy,
                 Alembic-ready, config, Local Identity Provider auth,
                 CLI seed-admin/seed-demo, bundle store, worker execution,
                 Environment Builder subsystem, auth framework seeder,
                 user management API (create/list/get users), email validation,
                 audit event model (AuditEvent, AuditEventType), audit service,
                 audit query API
frontend/        Next.js + React + TypeScript: login, projects, admin pages,
                 user management UI, project members UI, audit log tab,
                 per-project and per-resource audit views
containers/      Base analysis Docker images (python-3.13, python-3.14)
vm/              cloud-init.yaml, Caddyfile (HTTPS, HSTS, compression,
                 security headers, request size limits), runtime spec
scripts/         bootstrap.sh, install.sh, upgrade.sh, backup.sh, restore.sh, healthcheck.sh
docker-compose.yml  6 services + optional ollama (--profile ai),
                    internal + frontend + external networks
tests/           Unit (256), integration (identity validation, user management,
                 project membership, audit), smoke, e2e (canonical workflow)
docs/            Architecture (current state), security, API, vision, AI assistance
```

### Still needs creating

```
shared/          Shared schemas and types (not started)
examples/        Synthetic datasets and analysis templates (not started)
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

### Security constraints (must preserve in implementation)

- Researchers never get direct dataset access
- All analysis executes through the Worker in isolated Docker containers
- Datasets mounted read-only in containers
- Two-stage approval: execution approval then output approval
- Never bypass the approval workflow
- Use `Storage` and `Executor` interfaces (not coupling directly to Docker)
- Only the optional AI service (Ollama) has outbound network access, and only for model downloads
- IdentityProvider abstraction for auth, internal PostgreSQL for authorisation
- **Capability-based authorisation**: policy checks `require_capability()`, not roles
- **Project Membership scoping**: access requires membership + capability
- Audit trail required for all actions

### Identity model

There are four independent concepts:

#### User

A User represents an authenticated person. Users may belong to zero or more Projects via ProjectMembership. Users possess a `role` (metadata / seeding hint) and a list of `capabilities` (authoritative).

#### Role

A Role is a descriptive label with a default capability template. Roles seed capabilities at user creation time. After that, capabilities become the source of truth — changing a role does **not** silently change existing users.

Four roles exist: `researcher`, `moderator`, `maintainer`, `admin`.

Roles and role–capability mappings are stored in the database (`roles`, `role_capabilities` tables) and seeded by `auth_framework_seeder.seed_auth_framework()`.

#### Capability

Capabilities are authoritative. The policy layer authorises capabilities, not roles.

Capability vocabulary (defined in `app.models.capability.Capability` enum):

| Capability | Purpose |
|------------|---------|
| `project.manage` | Create and manage projects |
| `project.members.manage` | Add/remove project members |
| `project.resources.manage` | Attach/detach data resources |
| `bundle.create` | Create and edit analysis bundles |
| `bundle.submit` | Submit bundles for review |
| `bundle.review` | Approve/reject/supersede bundles |
| `execution.run` | Request execution of approved bundles |
| `output.review` | Approve/reject output sets |
| `output.release` | Release output sets to researchers |
| `environment.manage` | Manage execution environments |
| `data.manage` | Manage data resources |
| `user.manage` | Manage user accounts |

The `capabilities` table is materialised from the enum during seeding (the enum is authoritative). `UserCapability` records are copied from role templates at user creation and become independent thereafter.

#### Project Membership

ProjectMembership answers one question only: does this User participate in this Project?

- Membership is **scope**, not authorisation.
- No roles, capabilities, or permissions are stored on membership.
- The project creator becomes the first member automatically.
- Access requires: (1) membership in the project, (2) the required capability.

### Audit Event Model

Audit Events record institutional decisions and governance-significant outcomes.

- Immutable and append-only
- Attributable to an actor (authenticated user or seeded system user)
- Associated with a Project and a governed resource
- Accompanied by structured metadata

The model and service are defined in `app.models.audit_event` and `app.services.audit_service`.

### System Actors

Autonomous platform components are represented by seeded `User` records with well-known UUIDs.

These accounts have no password (`password_hash=""`) and cannot authenticate through the API. They exist solely as accountable actors referenced by Audit Events.

| Actor | UUID | Email | Role |
|---|---|---|---|
| System | `00000000-0000-0000-0000-000000000001` | `system@epibridge.internal` | `maintainer` |
| Execution Worker | `00000000-0000-0000-0000-000000000002` | `execution_worker@epibridge.internal` | `maintainer` |

A `role` value is required by the schema; `maintainer` is used as the closest semantic match to a platform operator. No capabilities are assigned — these are audit identities, not RBAC participants.

System users are seeded idempotently by `seed_auth_framework()` (`auth_framework_seeder._seed_system_users()`).

### Audit Query API

The audit ledger is exposed through a single read-only query endpoint:

```
GET /api/admin/audit-events
```

Supports filtering by: `project_id`, `actor_id`, `resource_type`, `resource_id`, `event_type`, `date_from`, `date_to`.

Supports pagination via `limit` (max 200) and `offset`, and ordering via `order` (`asc`/`desc`, default `desc`).

Returns actor details (display name, email) alongside each event via a join to the `users` table.

Access requires one of: `bundle.review`, `output.review`, or `user.manage` capability.

Defined in `app.api.routes.admin` and `app.services.audit_service`.

### Audit Event Taxonomy

The canonical audit vocabulary for Milestone 17.

Audit Events record either:

- institutional decisions; or
- externally significant outcomes.

#### Project

Project events record the creation, membership, and resource allocation lifecycle. These are deliberate governance actions that establish the institutional scope of research.

- `project.created`
- `project.member.added`
- `project.member.removed`
- `project.resource.allocated`
- `project.resource.deallocated`

#### Bundle

Bundle events record the two-stage approval workflow for analysis code. Every transition is an institutional choice about what analysis is permitted to run.

- `bundle.created`
- `bundle.submitted`
- `bundle.approved`
- `bundle.rejected`
- `bundle.superseded`

#### Execution

Execution events record the externally significant outcomes of running approved analysis. The start, completion, and failure of an execution are visible consequences of earlier governance decisions — a human acts on these outcomes.

- `execution.requested`
- `execution.started`
- `execution.completed`
- `execution.failed`
- `execution.cancelled`

#### Output

Output events record the governance lifecycle of execution results, mirroring the two-stage approval pattern. The release of an output set is the terminal governance decision that makes results available to researchers.

- `output_set.created`
- `output_set.approved`
- `output_set.rejected`
- `output_set.released`

#### User Administration

User creation is an institutional act with security implications. User administration events are not project-scoped.

- `user.created`

### Policy layer

The policy layer (`app.auth.policy`) exposes three functions:

| Function | Purpose |
|----------|---------|
| `require_capability(user, capability)` | Raise `PolicyError` if user lacks the capability |
| `require_project_membership(db, user, project_id)` | Raise 404 if user is not a project member; returns the Project |
| `require_owner(user, resource)` | Raise `PolicyError` if user is not the resource owner/creator |

Policy is entirely capability-based. Roles are never consulted by the policy layer.

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
- **Researcher artefacts** (Projects, Analysis Bundles, Execution Requests) are created by users through the application. Projects have members (ProjectMembership) in addition to the owner/creator.
- **Internal system artefacts** (AIBundleReview, BuildRequest, ExecutionImage, OutputSet) are created by background tasks and workers during platform operation.
- **Environment Builder subsystem** transforms Analysis Bundle dependency specifications into reusable Execution Images via curated Dockerfile templates. Builds are driven by `BuildRequest` work items processed by the worker alongside execution requests. `ExecutionImage` records serve as a content-addressable cache keyed by `(execution_environment_id, dependency_hash)`.
- **Auth framework** (capabilities, roles, role–capability mappings) is seeded by `auth_framework_seeder.seed_auth_framework()` on first use (idempotent).
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
6. Submitting the bundle (DRAFT → SUBMITTED)
7. Approving the bundle (SUBMITTED → APPROVED_FOR_EXECUTION)
8. Running the analysis
9. Waiting for PENDING → RUNNING → COMPLETED status transition
10. Approving the Output Set (PENDING_REVIEW → APPROVED)
11. Releasing the Output Set (APPROVED → RELEASED), creating the Release Package ZIP
12. Downloading the Release Package
13. Verifying the ZIP contains the expected output file (`summary.csv`) and execution metadata (`execution_metadata.json`)
14. Verifying audit events are visible in the admin Audit Log for each governance action

This is a system test — not UI, not API — covering frontend, backend, database, worker, Docker executor, provider abstraction, runtime contract, output registration, download endpoint, and audit ledger.

### Stack dependencies

Backend requires Python 3.11+. No other language runtimes or build tools have been installed. Stand up each package independently before wiring integration tests.
