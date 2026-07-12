# AGENTS.md

## Project status — Milestone 21 complete (Bundle Workspace, Institutional Publications, Validation Run)

### Exists and functional

```
backend/         FastAPI: identity model (User, Role, Capability,
                 ProjectMembership), capability-based policy, SQLAlchemy,
                 Alembic, config, Local Identity Provider auth,
                 CLI seed-admin/seed-demo/seed-terms, bundle store, worker execution,
                 Environment Builder subsystem, auth framework seeder,
                 user management API (create/list/get users), email validation,
                 terms of service model (TermsOfService, TermsAcceptance),
                 terms service (publish, accept, query), terms API routes,
                 platform terms enforcement (dependency-based),
                 dataset terms enforcement (resource attach, bundle submit),
                 audit event model (AuditEvent, AuditEventType), audit service,
                 audit query API,
                 ValidationRequest model, validation API, execution fingerprint,
                 representative dataset mounting
frontend/        Next.js + React + TypeScript: login, projects, admin pages,
                 user management UI, project members UI, audit log tab,
                 per-project and per-resource audit views,
                 platform terms interstitial (/terms), terms admin page,
                 dataset terms dialog during resource attach and bundle submit,
                 Bundle Workspace (bundle detail page with file management,
                 environment selection, resource declaration, validation run),
                 validation result display, bundle consistency indicators
execution-environments/      Execution Environment artefacts (base images, manifests)
examples/        Example analyses, bundle templates, environment definitions,
                 resource publication manifests
vm/              cloud-init.yaml, Caddyfile (HTTPS, HSTS, compression,
                 security headers, request size limits), runtime spec
scripts/         bootstrap.sh, install.sh, upgrade.sh, backup.sh, restore.sh, healthcheck.sh
docker-compose.yml  6 services + optional ollama (--profile ai),
                     internal + frontend + external networks
tests/           Unit (375), integration (identity validation, user management,
                 project membership, audit, terms governance, validation),
                 smoke,
                 e2e (canonical workflow, custom build workflow, validation workflow)
docs/            Architecture (current state), security, API, vision, AI assistance
```

### Still needs creating

```
shared/          Shared schemas and types (not started)
```

### Intended architecture (from docs/)

```
frontend/    Next.js + React + TypeScript
backend/     FastAPI + SQLAlchemy + Alembic + PostgreSQL
worker/      Python job executor
shared/      Shared schemas and types across packages
execution-environments/  Execution Environment artefacts
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
- Execution containers run with: `cap_drop=["ALL"]`, read-only rootfs, `no-new-privileges`,
  tmpfs for `/tmp` and `/output`, disabled networking, and configurable resource limits
  (`execution_mem_limit`, `execution_cpu_limit`, `execution_pids_limit`, `max_output_size_mb`)
- All archives (bundle uploads, container outputs) are treated as untrusted:
  symlinks rejected, path traversal blocked, decompression size limited

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
| `terms.manage` | Publish and manage terms of service |
| `validation.run` | Run validation against representative datasets |
| `build.customize` | Use Custom Build strategy for analysis bundles |

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

#### Terms

Terms events record the publication of institutional governance documents and their acknowledgement by researchers. Publication events are not project-scoped.

- `platform_terms.published`
- `dataset_terms.published`
- `platform_terms.accepted`
- `dataset_terms.accepted`

#### Validation

Validation events record the outcome of operational verification runs against representative datasets. These are operational events only — validation does not participate in governance workflows.

- `validation.completed`
- `validation.failed`

### Policy layer

The policy layer (`app.auth.policy`) exposes three functions:

| Function | Purpose |
|----------|---------|
| `require_capability(user, capability)` | Raise `PolicyError` if user lacks the capability |
| `require_project_membership(db, user, project_id)` | Raise 404 if user is not a project member; returns the Project |
| `require_owner(user, resource)` | Raise `PolicyError` if user is not the resource owner/creator |

Policy is entirely capability-based. Roles are never consulted by the policy layer.

### Admin endpoint capability requirements (enforced server-side)

Every `/api/admin/*` endpoint enforces a capability check. The requirements are:

| Endpoint | Required Capability |
|---|---|
| `GET /admin/resources`, `GET /admin/resources/{id}` | `data.manage` |
| `GET /admin/execution-environments`, `GET /admin/execution-environments/{id}` | `environment.manage` |
| `GET /admin/bundles`, `GET /admin/bundles/{id}` | Tiered: `bundle.review` / `output.review` / `user.manage` |
| `GET /admin/execution-requests`, `GET /admin/execution-requests/{id}` | Tiered: `bundle.review` / `output.review` / `user.manage` |
| `GET /admin/output-sets`, `GET /admin/output-sets/{id}` | `output.review` |
| `GET /admin/execution-requests/{id}/outputs` | `output.review` |
| `GET /admin/outputs/{id}` | `output.review` |
| `GET /admin/users`, `GET /admin/users/{id}`, `POST /admin/users` | `user.manage` |
| `GET /admin/audit-events` | Tiered: `bundle.review` / `output.review` / `user.manage` |
| `POST /admin/terms/platform` | `terms.manage` |
| `POST /admin/resources/{id}/terms/publish` | `terms.manage` |
| `GET /admin/terms/status` | `terms.manage` |
| `POST /admin/bundles/{id}/approve`, `/reject` | `bundle.review` |
| `POST /admin/bundles/{id}/supersede` | `bundle.review` (unless owner) |
| `POST /admin/output-sets/{id}/approve`, `/reject` | `output.review` |
| `POST /admin/output-sets/{id}/release` | `output.release` |

All project-scoped endpoints additionally enforce `require_project_membership` and appropriate capabilities (`project.manage`, `bundle.create`, `bundle.submit`, `execution.run`, `project.members.manage`, `project.resources.manage`).

### Database Migrations (Alembic)

Alembic is the single authoritative mechanism for database schema management.

**Migration workflow:**

- **SQLAlchemy models remain the source of truth** — models define the schema, Alembic generates migrations from them.
- The initial migration (`alembic/versions/`) was generated via `alembic revision --autogenerate` and represents the current schema.
- All future schema changes require a new Alembic migration, never manual DDL or `create_all()`.

**Developer workflow for schema changes:**

1. Modify the SQLAlchemy model class.
2. Run `alembic revision --autogenerate -m "Description of change"` from `backend/`.
3. Review the generated migration file in `alembic/versions/`.
4. Run `alembic upgrade head` to apply it.
5. Verify with unit and integration tests.

**Startup behaviour:**

- On startup, the backend runs `alembic upgrade head` to ensure the database is at the current migration revision.
- If the database is empty, all migrations are applied (fresh install).
- If the database has tables but no `alembic_version` table (legacy `create_all`-generated schema), startup fails with a clear error. The operator must manually verify schema compatability and run `alembic stamp head`.

**Deployment expectations:**

- `upgrade.sh` and `restore.sh` run `alembic upgrade head` as part of their workflow.
- Docker Compose does not run migrations explicitly; the application handles them at startup via the lifespan.
- Always run `alembic upgrade head` before starting the application against a new database.

**Migration policy:**

During active development, the migration history is regularly squashed so that the repository contains a single migration representing the current schema.

Once a version is released, migrations become part of the supported upgrade path between released versions.

Migration history may be squashed again at a future major release when upgrades from earlier releases are no longer supported.

### Logging

Logging is configured centrally at startup via `app.core.logging.configure_logging()`.

- **Log level** is controlled by the `LOG_LEVEL` environment variable (default `INFO`). Valid values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.
- **Format**: `%(asctime)s [%(levelname)s] %(name)s: %(message)s` with UTC timestamps.
- **Output**: stderr via Python's `StreamHandler` (compatible with container logging).
- **Module loggers**: Alembic, `asyncio`, SQLAlchemy engine, Uvicorn, and Uvicorn access logs default to `WARN` to reduce noise.

### Exception Handling

Three global exception handlers provide a safety net for unhandled exceptions:

| Exception | HTTP Status | Response Body |
|---|---|---|
| `PolicyError` | 403 | `{"detail": "Forbidden"}` |
| `ValueError` | 422 | `{"detail": "Invalid request."}` (logged at WARNING) |
| `Exception` (fallback) | 500 | `{"detail": "Internal Server Error"}` (logged at ERROR) |

These are fallback handlers. Route-specific error handling (404s, 401s, 422s from service-layer `ValueError` catch blocks) takes precedence. The global `ValueError` handler returns a generic message to avoid leaking internal implementation details. The global `Exception` handler ensures no unhandled exception leaks internal details to the client.

### Terms Governance

Versioned institutional Terms of Service with backend-authoritative enforcement.

#### Platform Terms

- Versioned Terms of Service governing platform access.
- Published by administrators via `POST /api/admin/terms/platform` (requires `terms.manage`).
- Presented immediately after authentication when the current version has not been accepted.
- Acceptance is mandatory before platform access is granted.
- Refusal or dismissal logs the user out.
- Acceptance is permanently recorded in `terms_acceptance` and audited as `platform_terms.accepted`.
- The publishing administrator is automatically recorded as having accepted (act of publication implies institutional understanding).

#### Dataset Terms

Each Data Resource may define its own versioned Terms of Service.

- Published by administrators via `POST /api/admin/resources/{id}/terms/publish` (requires `terms.manage`).
- Researchers must accept the latest version before: attaching the resource to a Project, or submitting an Analysis Bundle referencing that resource.
- Enforcement occurs at the API layer — resource attachment and bundle submission endpoints check acceptance before proceeding.
- If Dataset Terms are updated (new version published), researchers must accept the latest version before further use.

#### Models

`TermsOfService` (`terms_of_service` table): Immutable institutional artefact. Each row is a specific published version for a specific scope.

`TermsAcceptance` (`terms_acceptance` table): Immutable append-only record of a user accepting a specific terms version. Acceptance state is always derived from these records — never from mutable boolean flags.

#### Enforcement

- Platform terms: `require_platform_terms_accepted()` FastAPI dependency, applied at the router level on `projects`, `admin`, `environments` routers. No-op when no terms are published (upgrade-safe).
- Dataset terms: checked inline in `post_project_resources()` and `post_submit_bundle()` route handlers.

#### Audit Events

| Event | Trigger |
|---|---|
| `platform_terms.published` | Platform terms published |
| `dataset_terms.published` | Data resource terms published |
| `platform_terms.accepted` | User accepts platform terms |
| `dataset_terms.accepted` | User accepts dataset terms |

#### User-Facing API

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/terms/platform/current` | Current platform terms |
| `POST` | `/api/terms/platform/accept` | Accept platform terms |
| `GET` | `/api/terms/resources/{id}/current` | Current resource terms |
| `POST` | `/api/terms/resources/{id}/accept` | Accept resource terms |
| `GET` | `/api/terms/status` | All terms acceptance status |
| `GET` | `/api/terms/check?resource_ids=...` | Check specific resources |

#### Seeding

`epibridge seed-terms` publishes default platform terms (Markdown) for development environments. Idempotent — skips if terms already exist.

### Health Check

`GET /api/health` returns platform operational status:

```json
{"status": "ok", "database": "connected", "redis": "connected"}
```

- **`status`**: `"ok"` when all dependencies are healthy, `"degraded"` otherwise.
- **`database`**: `"connected"` or `"disconnected"` based on a live `SELECT 1` query.
- **`redis`**: `"connected"` or `"disconnected"` based on a `PING` command.
- No authentication required. No internal implementation details exposed.

### Request Logging

An HTTP middleware logs each request after completion:

- Method, path, response status code, and duration in milliseconds.
- Request bodies and query parameters are never logged (sensitive data).
- Logged at `INFO` level via the `epibridge` logger.

### Domain model boundary

- **Institutional assets** (Data Resources, Execution Environments) are registered automatically via lifespan startup from YAML manifests.
- **Researcher artefacts** (Projects, Analysis Bundles, Execution Requests) are created by users through the application. Projects have members (ProjectMembership) in addition to the owner/creator.
- **Internal system artefacts** (AIBundleReview, BuildRequest, ExecutionImage, OutputSet) are created by background tasks and workers during platform operation.
- **Environment Builder subsystem** transforms Analysis Bundle dependency specifications into reusable Execution Images via curated Dockerfile templates. Builds are driven by `BuildRequest` work items processed by the worker alongside execution requests. `ExecutionImage` records serve as a content-addressable cache keyed by `(execution_environment_id, dependency_hash)`.
- **Auth framework** (capabilities, roles, role–capability mappings) is seeded by `auth_framework_seeder.seed_auth_framework()` on first use (idempotent).
- **Demo workspace** (optional) can be created by `seed-demo` CLI command — a development tool, not application startup logic.
- **Manifest directories** (`RESOURCE_MANIFEST_DIR`, `ENVIRONMENT_MANIFEST_DIR`) are deployment configuration, not application defaults. Docker Compose sets them for development; production points them elsewhere.

### Seeded development accounts

The following personas are seeded during `bootstrap.sh` and are available for
manual validation:

| Persona | Email | Password | Role |
|---------|-------|----------|------|
| Administrator | `admin@epibridge.local` | From `ADMIN_PASSWORD` in `.env` (generated) | admin |
| Maintainer | `maintainer@epibridge.local` | `maintainer` | maintainer |
| Researcher | `researcher@epibridge.local` | `researcher` | researcher |

All three are created idempotently — re-running bootstrap does not duplicate them.

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
- `uvicorn app.main:app --reload` — dev server (applies pending Alembic migrations on startup)
- `python -m app.cli seed-admin` — seed admin user
- `python -m app.cli seed-maintainer` — seed maintainer user
- `python -m app.cli seed-researcher` — seed researcher user
- `python -m app.cli seed-terms` — seed default platform terms (dev debugging tool)
- `python -m app.cli seed-demo` — seed demo workspace (dev debugging tool)
- `alembic upgrade head` — apply pending migrations
- `alembic revision --autogenerate -m "description"` — generate a new migration from model changes

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
- `make dev-test` — run full suite inside the container via SSH (recommended developer workflow; requires OrbStack VM + Docker stack)
- `make test` — run unit, integration, and smoke test suites natively (requires PostgreSQL + Redis on localhost; the `epibridge_test` database must exist)
- `make playwright` — run canonical workflow e2e test (requires full stack running)
- `make playwright CMD=e2e/custom-build-workflow.spec.ts` — run custom build workflow e2e test
- `make playwright CMD=e2e/validation-workflow.spec.ts` — run validation workflow e2e test
- `python -m pytest backend/tests/unit -v` — unit tests only (no database required)
- `python -m pytest backend/tests/integration -v` — integration tests (requires PostgreSQL + Redis on localhost + `epibridge_test` database)
- `python -m pytest backend/tests/smoke -v` — smoke tests (requires full stack running)

Integration tests use a dedicated `epibridge_test` PostgreSQL database for isolation.

### Authentication configuration

Key settings for deployment:

| Setting | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | (required) | Must be at least 32 characters. Generate with `openssl rand -base64 32`. |
| `session_ttl_seconds` | 86400 (24h) | Per-session time-to-live. |
| `max_session_ttl_seconds` | 604800 (7d) | Absolute maximum session lifetime (hard upper bound). |
| `secure_cookie` | False | Set `true` when deploying behind TLS. |
| `rate_limit_max_attempts` | 10 | Login attempts per window before rate limiting. |
| `rate_limit_window_seconds` | 300 (5min) | Rate limit window. |
The bootstrap process (`bootstrap.sh`) creates this database automatically.
For local native runs, create it manually:
```
createdb epibridge_test
```

**CI** (from repo root, requires Docker):
- `make ci` — bootstrap full stack (build, start, seed), same as `make bootstrap`
- `make ci-clean` — tear down all Docker resources and remove `.env`
- `make playwright` — run canonical workflow e2e test (must be run after `make ci`)
- `make playwright CMD=e2e/custom-build-workflow.spec.ts` — run custom build workflow e2e test
- `make playwright CMD=e2e/validation-workflow.spec.ts` — run validation workflow e2e test

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
3. Publishing platform terms via the admin API
4. Creating a project
5. Attaching a data resource to the project
6. Creating an analysis and uploading a bundle
7. Submitting the bundle (DRAFT → SUBMITTED)
8. Approving the bundle (SUBMITTED → APPROVED_FOR_EXECUTION)
9. Running the analysis
10. Waiting for PENDING → RUNNING → COMPLETED status transition
11. Approving the Output Set (PENDING_REVIEW → APPROVED)
12. Releasing the Output Set (APPROVED → RELEASED), creating the Release Package ZIP
13. Downloading the Release Package
14. Verifying the ZIP contains the expected output file (`summary.csv`) and execution metadata (`execution_metadata.json`)
15. Verifying audit events are visible in the admin Audit Log for each governance action

This is a system test — not UI, not API — covering frontend, backend, database, worker, Docker executor, provider abstraction, runtime contract, output registration, download endpoint, and audit ledger.

### Validation Workflow (end-to-end)

The validation workflow is a separate Playwright e2e test that proves the researcher validation capability.

```bash
make dev           # bootstrap the full stack (OrbStack VM)
make playwright CMD=e2e/validation-workflow.spec.ts
```

The test (in `frontend/e2e/validation-workflow.spec.ts`) validates:
1. Browsing institutional publications (environments, resources)
2. Creating a project
3. Attaching a data resource
4. Creating a draft analysis bundle
5. Uploading analysis code that reads representative data
6. Running validation (PENDING → RUNNING → COMPLETED)
7. Viewing validation logs and output files
8. Verifying the "Validated" bundle consistency indicator
9. Modifying the bundle and verifying "Bundle has changed since validation"
10. Re-running validation to restore the "Validated" state
11. Submitting for review

### Deployment user

Platform services (backend, worker) run as the non-root `epibridge` user. The reference
deployment provisions matching ownership: `cloud-init.yaml` creates `/var/lib/epibridge/`
owned by UID 1000, and `scripts/bootstrap.sh` applies the same ownership at setup time.
The container's `epibridge` user uses a matching UID (1000) so that volume-mounted storage
directories are writable without runtime permission workarounds or world-writable fallbacks.

### Worker resilience

The worker (`worker/worker/main.py`) runs as a single-threaded infinite polling loop. Three resilience mechanisms are built in:

- **Database connection backoff**: On connection failure, the worker retries with exponential backoff (1s, 2s, 4s, ..., max 60s). Backoff resets to 1s on successful connection.
- **Outer catch-all**: Any unexpected exception during polling is logged with a full traceback; the loop continues.
- **Graceful shutdown**: `SIGTERM` and `SIGINT` are handled. The current iteration completes (including any in-flight build or execution), then the loop exits. In-flight containers are left for Docker to manage.

The worker polls `ValidationRequest` (PENDING) first, then `BuildRequest` (PENDING), then `ExecutionRequest` (PENDING), within each poll cycle.

### Future refactoring — Authentication flow

The frontend `request()` helper currently combines transport responsibilities
(HTTP requests, timeout handling, response parsing) with application navigation
(session-expiry redirect).

A future refactoring should move session-expiry handling into the authentication
layer (e.g. `AuthProvider` or a central authentication/session manager), leaving
`request()` responsible only for transport concerns.

At that point the API helper would report authentication failures, while the
authentication layer would decide whether to redirect, re-authenticate or present
an appropriate user experience. This would eliminate the need for route-specific
guards such as the current `/login` pathname check.

### Stack dependencies

Backend requires Python 3.11+. No other language runtimes or build tools have been installed. Stand up each package independently before wiring integration tests.
