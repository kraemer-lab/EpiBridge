# EpiBridge — Architecture Summary

## Vision

EpiBridge is a secure remote analysis platform for epidemiology and other sensitive research data.

The guiding principle is:

> Move the computation to the data, not the data to the computation.

Rather than giving researchers direct access to sensitive datasets, EpiBridge allows them to develop analyses locally using schema documentation and synthetic data, submit analysis bundles to the data owner, execute those jobs within a secure institutional environment, and receive approved outputs after governance review.

Sensitive data never leaves the institution.

---

## Trust Boundaries

EpiBridge defines three distinct trust boundaries, each with different privileges and responsibilities.

```
Host
  └── Trusted Runtime (VM)
        └── Analysis Container
```

### Host

The host machine owns the physical or networked storage containing sensitive institutional data. EpiBridge never knows host paths and never accesses host storage directly. The host is managed by institutional IT and is outside EpiBridge's operational scope.

### Trusted Runtime (VM)

The deployment runs inside a restricted Linux virtual machine. This is the EpiBridge platform boundary. The VM contains:

- All EpiBridge services (frontend, backend, database, worker)
- Docker Engine
- The Resource Registry (database index of registered data resources and execution environments)
- Institutional data resources exposed at a well-known location: `/read-only-data`

How resources arrive at `/read-only-data` (bind mount, NFS, cloud storage) is the deployment's responsibility — never EpiBridge's.

### Analysis Container

The analysis container is the least-privileged environment. It is intentionally isolated from the Trusted Runtime.

The container must never receive:

- `/read-only-data` — the full institutional data store
- Host storage paths
- The Resource Registry
- Deployment configuration

The container receives only:

| Path      | Purpose                              |
|-----------|--------------------------------------|
| `/work`   | Writable temporary storage           |
| `/data`   | Namespace of authorised resources    |
| `/output` | Writable results directory           |

#### /data — authorised namespace

Each authorised resource appears at:

```
/data/{alias}
```

The Executor constructs this mount point from the provider's `RuntimeConfig` and the resource's alias. The provider describes *what* to expose (source path, type); the Executor decides *where* (`/data/{alias}`).

#### Security boundary

> The analysis container must never receive access to `/read-only-data`.

The Executor enforces this by mounting only the authorised subset. A compromised container cannot enumerate or access unauthorised resources.

### Summary

| Boundary | Contents | Privilege |
|----------|----------|-----------|
| Host | Physical storage, institutional IT | Most privileged |
| Trusted Runtime (VM) | EpiBridge services, `/read-only-data`, Registry | Medium |
| Analysis Container | `/work`, `/data/{alias}`, `/output` | Least privileged |

This three-layer design ensures that even a fully compromised analysis container cannot access unauthorised data or infrastructure configuration.

---

## Security Constraints

- Researchers never get direct dataset access
- All analysis executes through the Worker in isolated Docker containers
- Datasets mounted read-only in containers
- Two-stage governance: execution approval then output approval
- Never bypass the approval workflow
- Use `Storage`, `Executor`, and `IdentityProvider` interfaces (not coupling directly to implementations)
- Only the optional AI service (Ollama) has outbound network access, and only for model downloads
- IdentityProvider abstraction for authentication; internal PostgreSQL for authorisation
- Capability-based authorisation: policy checks `require_capability()`, not roles
- Project Membership scoping: access requires membership + capability
- Audit trail required for all actions

---

## Deployment Model

Each institution runs its own EpiBridge instance inside a restricted Linux virtual machine.

```
Institution
└── Virtual Machine
        │
        ├── EpiBridge Platform
        ├── Local Sensitive Data
        └── Analysis Containers
```

The VM is the trust boundary.

The VM hosts:

- Next.js frontend
- FastAPI backend
- PostgreSQL
- Redis
- Worker service
- Docker Engine

No external system accesses the sensitive data directly.

---

## Platform Components

```
Internet
    │
    HTTPS
    │
Reverse Proxy
    │
────────────────────────────
EpiBridge
────────────────────────────
Frontend (Next.js)
↓
Backend API (FastAPI)
↓
PostgreSQL
Redis
↓
Worker
↓
Docker Engine
↓
Ephemeral Analysis Containers
↓
Local Sensitive Data
```

---

## Technology Stack

### Frontend

- Next.js
- React
- TypeScript

### Backend

- FastAPI
- SQLAlchemy
- Alembic

### Authentication

- Local Identity Provider (first implementation)
- Email/password with Argon2 hashing
- Server-side sessions backed by PostgreSQL
- HTTP-only secure cookies
- IdentityProvider abstraction for future providers

### Database

- PostgreSQL

### Queue

- Redis

### Execution

- Docker (via Executor abstraction)

### Deployment

- Docker Compose (initial)

---

## Identity Model

There are four independent concepts:

### User

A User represents an authenticated person. Users may belong to zero or more Projects via ProjectMembership. Users possess a `role` (metadata / seeding hint) and a list of `capabilities` (authoritative).

### Role

A Role is a descriptive label with a default capability template. Roles seed capabilities at user creation time. After that, capabilities become the source of truth — changing a role does **not** silently change existing users.

Four roles exist: `researcher`, `moderator`, `maintainer`, `admin`.

Roles and role–capability mappings are stored in the database (`roles`, `role_capabilities` tables) and seeded by `auth_framework_seeder.seed_auth_framework()`.

### Capability

Capabilities are authoritative. The policy layer authorises capabilities, not roles.

Capability vocabulary:

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

Role templates:

| Role | Capabilities |
|------|-------------|
| researcher | `project.manage`, `bundle.create`, `bundle.submit`, `execution.run`, `validation.run` |
| moderator | All researcher + `project.members.manage`, `project.resources.manage`, `bundle.review`, `output.review` |
| maintainer | All moderator + `output.release`, `environment.manage`, `data.manage`, `build.customize`, `validation.run` |
| admin | All capabilities |

### Project Membership

ProjectMembership answers one question only: does this User participate in this Project?

- Membership is **scope**, not authorisation.
- No roles, capabilities, or permissions are stored on membership.
- The project creator becomes the first member automatically.
- Access requires: (1) membership in the project, (2) the required capability.

### User Administration

Users are created through the API by users possessing the `user.manage` capability (administrators). The primary workflow is:

```
POST /api/admin/users  { email, display_name, password, role }
```

The CLI (`python -m app.cli create-user`) remains available for scripting but is secondary.

### Identity Validation

The capability model is validated through integration tests (`test_identity_api.py`) that verify each role's capability boundaries:

- Researcher can create projects and bundles, submit for review, request execution. Cannot review/release outputs or manage users.
- Moderator can review bundles and output sets. Cannot release outputs or manage users.
- Maintainer can release outputs. Cannot manage users.
- Administrator can perform every capability.

---

## Policy Layer

The policy layer (`app.auth.policy`) exposes three functions:

| Function | Purpose |
|----------|---------|
| `require_capability(user, capability)` | Raise `PolicyError` if user lacks the capability |
| `require_project_membership(db, user, project_id)` | Raise 404 if user is not a project member; returns the Project |
| `require_owner(user, resource)` | Raise `PolicyError` if user is not the resource owner/creator |

Policy is entirely capability-based. Roles are never consulted by the policy layer.

---

## Institutional Infrastructure vs. Researcher Artefacts

EpiBridge makes a clear distinction between two categories of entities.

### Institutional Infrastructure — Publications (curated by the institution)

The institution publishes authoritative guidance and infrastructure through **repository-backed publications**:

- **Data Resources** — registered institutional data assets. The institution owns and manages the underlying data; EpiBridge provides the catalogue and access control. Each publication includes schemas, documentation, and representative datasets.
- **Execution Environments** — approved runtimes in which analyses execute. The institution curates the available environments and their contents, publishing base images, Dockerfiles, and local development guidance.
- **Example Analyses** — demonstration bundles showing how to structure analyses against specific resources.
- **Bundle Templates** — reusable bundle structures that researchers can download and adapt.

These are published from YAML manifests on startup. The filesystem is the source of truth; the database is a runtime index. Researchers do not create or modify institutional infrastructure during normal workflows.

### Researcher Artefacts (created by researchers)

- **Projects** — permission boundaries for analysing specific Data Resources.
- **Analysis Bundles** — descriptions of analyses, referencing approved Data Resources and Execution Environments.

Researchers work exclusively with researcher artefacts. They select from available institutional infrastructure but do not define it.

### Domain Model Boundary

- **Institutional assets** (Data Resources, Execution Environments) are registered automatically via lifespan startup from YAML manifests.
- **Researcher artefacts** (Projects, Analysis Bundles, Execution Requests) are created by users through the application. Projects have members (ProjectMembership) in addition to the owner/creator.
- **Internal system artefacts** (AIBundleReview, BuildRequest, ExecutionImage, OutputSet) are created by background tasks and workers during platform operation.
- **Auth framework** (capabilities, roles, role–capability mappings) is seeded by `auth_framework_seeder.seed_auth_framework()` on first use (idempotent).
- **Demo workspace** (optional) can be created by `seed-demo` CLI command — a development tool, not application startup logic.
- **Manifest directories** (`RESOURCE_MANIFEST_DIR`, `ENVIRONMENT_MANIFEST_DIR`) are deployment configuration, not application defaults. Docker Compose sets them for development; production points them elsewhere.

---

## Institutional Publications

The institution publishes authoritative guidance to researchers through **repository-backed publications**. These are read-only from the repository; the database indexes them for researcher discovery.

### Publication Types

| Publication | Location | Content |
|-------------|----------|---------|
| Execution Environments | `execution-environments/{identifier}/` | Base image Dockerfile, manifest, documentation |
| Data Resources | `resources/{identifier}/` | Manifest, schemas, documentation, representative datasets |
| Example Analyses | `examples/analyses/{identifier}/` | Demonstration bundle code, manifest, README |
| Bundle Templates | `examples/templates/{identifier}/` | Reusable bundle structure, manifest |

### Operational State vs. Institutional Knowledge

> **Operational state** belongs in PostgreSQL.
> **Institutional knowledge** belongs in the repository.

Operational state (users, projects, bundles, execution requests, validation requests, output sets, sessions, audit events, terms acceptances) is created and managed through the application at runtime. The database is the authoritative store.

Institutional knowledge (execution environment definitions, data resource publications, example analyses, bundle templates, schemas, documentation) is maintained in the repository and published to the database as a runtime index. The filesystem is the source of truth.

The database is never the source of truth for institutional knowledge. If the repository and database diverge, the repository wins on the next startup reconciliation.

### Publication Artefacts

Each publication directory may contain:

- `manifest.yaml` — registration metadata (identifier, name, description)
- Artefact files (Dockerfiles, analysis code, schemas)
- `README.md`, `DOCUMENTATION.md`, `SCHEMA.md` — researcher guidance
- `representative/` — representative datasets for validation runs

Publications are served to researchers through dedicated API endpoints (e.g., `/api/environments`, `/api/resources`, `/api/examples`, `/api/templates`) and are visible in the application UI.

---

## Researcher Lifecycle

The completed researcher journey proceeds through the following stages:

```
Institutional Publications
         │
         ▼
   Bundle Workspace
         │
         ▼
   Validation Run  (advisory)
         │
         ▼
   Submit for Review
         │
         ▼
   Institutional Governance
         │
         ▼
   Institutional Execution
         │
         ▼
       Outputs
```

### Stage 1: Discovery

Researchers browse institutional publications to understand what environments and data resources are available, review example analyses, and download bundle templates. All publication content is read-only and repository-backed.

### Stage 2: Preparation

Researchers create an Analysis Bundle within the Bundle Workspace. They select an execution environment, declare data resources, upload analysis code, and configure the entrypoint, interpreter, and arguments. The bundle remains in DRAFT status throughout preparation.

### Stage 3: Validation (Advisory)

Before submitting for review, researchers may run an operational validation. The bundle is executed against representative datasets only — governed data resources are never accessed. Validation outputs are transient and researcher-visible. Results include execution logs and output files. A "Validated" indicator confirms the bundle state at the time of validation. If the bundle changes after validation, the indicator warns "Bundle has changed since validation."

Validation is never a submission gate. Researchers may always submit without validating.

### Stage 4: Submission

The researcher submits the bundle for institutional review. The bundle transitions from DRAFT to SUBMITTED status. No further edits are permitted.

### Stage 5: Governance

Institutional reviewers approve, reject, or supersede the bundle. If approved, the bundle transitions to APPROVED_FOR_EXECUTION and becomes eligible for institutional execution against governed data.

### Stage 6: Execution

Approved bundles are executed against governed data resources within isolated Docker containers. The worker processes execution requests sequentially.

### Stage 7: Output Release

Execution outputs undergo a two-stage approval process (output review then output release) before being made available to the researcher as a Release Package ZIP.

---

## Data Resources

EpiBridge does not own, store, or manage scientific data.

A **Data Resource** represents an existing institutional data asset that has been registered for analysis. The institution owns and manages the underlying data; EpiBridge provides a catalogue of available resources, access control, and secure execution.

### Resource Providers

A **Resource Provider** is an abstraction that knows how to make a particular type of data resource available for analysis. Implementations include:

- **CsvProvider** — a CSV file available at a known path
- **DuckDBProvider** — a DuckDB database
- **PostgresProvider** — a PostgreSQL database
- **ExcelProvider** — an Excel workbook
- **ParquetProvider** — a directory of Parquet files

The provider has two responsibilities:

1. **`validate_endpoint(endpoint)`** — is the endpoint configuration well-formed?
2. **`prepare_runtime(endpoint)`** — what mount points and environment variables are needed to expose this resource inside an analysis container?

Providers describe runtime requirements in platform-agnostic terms (`Mount`, `RuntimeConfig`). An Executor (Docker, Kubernetes, Slurm, etc.) translates these into the corresponding infrastructure.

### Resource Identifiers

Every Data Resource has three identifiers with distinct responsibilities:

| Field | Purpose | Stability |
|-------|---------|-----------|
| `id` | Internal database UUID. Auto-generated. | Never changes |
| `identifier` | Stable institutional identity used for registration and reconciliation. Defined in the manifest. | Stable once set |
| `alias` | Stable runtime namespace used inside analysis containers (`/data/{alias}`). Defined in the manifest. | Stable once set |

The analysis always uses the alias. Display names (`name`) can be improved without breaking existing analyses because the runtime contract references `/data/{alias}`, not `/data/{name}`.

The registration service reconciles resources using `identifier` — it is the canonical key for matching manifest entries to database records.

### Registration Process

Data Resources are registered from YAML manifests. The database is a runtime index; the manifest is the source of truth.

```
Load all manifests
  ↓
Validate all manifests (required fields, provider type, endpoint shape)
  ↓
If any manifest is invalid → abort startup
  ↓
Begin transaction
  ↓
For each entry:
  Lookup DataResource by identifier
    ├── Found → update name, alias, endpoint, version, status
    └── Not found → create new record
  ↓
Commit (atomic — all or nothing)
```

### Project Resource Allocation

A **Project** represents permission to analyse one or more Data Resources. Projects do not own resources — the relationship is managed through `ProjectResourceAllocation`, a first-class domain object that records the institutional provisioning decision. Each allocation captures who authorised it (`created_by_id`), when it was created (`created_at`), and optionally when and by whom it was revoked (`revoked_by_id`, `revoked_at`). An allocation is active when `revoked_at IS NULL`.

---

## Execution Environments

An **Execution Environment** is an institutional asset representing an approved runtime in which an analysis may execute. Like Data Resources, they are curated by the institution — researchers select from available environments rather than specifying arbitrary runtime strings.

Execution Environments define the **institutional execution contract** — they guarantee a specific runtime, filesystem layout, and set of conventions required for governed execution:

- `/analysis` — bundle injection target
- `/data` — resource mount namespace
- `/output` — writable results directory
- `/work` — temporary storage
- `nobody` user — least-privilege execution identity

An Execution Environment is more than a language runtime. It represents an institutional commitment that analyses targeting that environment will execute correctly and securely.

### Execution Environment Artefacts

Each Execution Environment is defined by a directory of artefacts in the `execution-environments/` directory:

```text
execution-environments/
├── python-3.13/
│   ├── Dockerfile           # Base image definition
│   ├── manifest.yaml        # Registration manifest
│   └── ...                  # Supporting artefacts
├── python-3.14/
│   └── ...
└── conda/
    └── ...
```

The **filesystem is the authoritative source of truth** for execution environments. The database indexes and caches this information for runtime use, but the artefacts directory is the canonical record. Registration reconciles the database against the filesystem on startup — not the reverse.

Researchers do not create execution environments. They select from the institutional catalogue.

### Researcher Discovery

Researchers can discover available execution environments through the application UI:

- **List page** — all active environments with runtime, description, and image reference
- **Detail page** — full environment details including the curated Dockerfile, local development commands, and published artefact downloads
- **During bundle creation** — environment selector with display names and linked detail pages

This enables researchers to prepare their analysis locally against the institutional runtime before uploading a bundle. The environment detail page provides concrete guidance:

```
docker pull {image_reference}
docker run --rm -it {image_reference} /bin/bash
```

### Currently Supported Environments

| Name | Runtime | Base Image |
|------|---------|------------|
| Python 3.13 | `python-3.13` | `python:3.13-slim` (NumPy, Pandas) |
| Python 3.14 | `python-3.14` | `python:3.14-slim` (NumPy, Pandas) |
| Conda | `conda` | `mambaorg/micromamba:2.8.1` |

### Environment Model

```
ExecutionEnvironment
├── id              (UUID, auto-generated)
├── identifier      (stable institutional identity)
├── name            (human-readable display name)
├── runtime         ("python-3.13", "conda", etc.)
├── description     (curated package summary)
├── status          ("active", "deprecated")
├── image_reference (Docker image tag)
├── definition_path (path to artefact directory, for debugging)
├── created_at
└── updated_at
```

### Registration

Execution Environments are seeded from YAML manifests on startup, following the same pattern as Data Resources. Registration is idempotent — the manifest directory is rescanned on each startup and new or updated environments are reconciled automatically.

---

## Projects

A **Project** is a collaboration space and permission boundary. Researchers create Projects to group related analyses and data resources.

- Projects have a name, description, and owner (creator).
- The owner is automatically added as the first member.
- Members are added by users with the `project.members.manage` capability.
- Project membership is **scope only** — no roles or capabilities are stored on the membership record.
- Data Resources are attached to Projects via `ProjectResourceAllocation`.
- Access to a Project requires: (1) membership in the Project, (2) the relevant capability for the action.

---

## Analysis Bundles

An **Analysis Bundle** is a researcher-created artefact that describes an analysis and its requirements. Researchers do not submit arbitrary scripts to the platform — they submit Analysis Bundles. The bundle captures:

- the analysis metadata (name, version, description)
- a reference to an approved **Execution Environment** (selected from the curated catalogue)
- the entry point script and interpreter
- the Data Resources the analysis expects (declared by institutional identifier)
- CLI arguments
- the expected outputs
- optional configuration parameters
- an explicit **Build Strategy** (institutional or custom)

The bundle is a **researcher artefact**, created within a Project and owned by the researcher who created it.

### Bundle Workspace

Researchers prepare Analysis Bundles in a **Bundle Workspace** — a mutable environment within the application where bundles are created, edited, and configured before submission. The workspace supports:

- **File management**: upload ZIP archives, import files into existing bundles, upload individual files, delete files, clear all contents
- **Execution configuration**: select environment, set entrypoint, interpreter, CLI arguments, version, build strategy
- **Resource declaration**: select data resources allocated to the project
- **AI Review**: generate an optional AI analysis summary (when enabled)
- **Validation Run**: execute the bundle against representative datasets before submission

The workspace is the single source of truth while the bundle is in DRAFT status. Changes are persisted via explicit save actions, and the workspace also saves pending changes automatically before submitting or validating.

### Bundle Model

```
AnalysisBundle
├── id                      (UUID, auto-generated)
├── project_id              (FK → Project)
├── created_by_id           (FK → User)
├── execution_environment_id (FK → ExecutionEnvironment, nullable)
├── name
├── version
├── entrypoint
├── interpreter             ("python" | "shell" | "r")
├── arguments               (CLI arguments string)
├── description
├── source_path             (bundle store path, set after upload)
├── outputs                 (JSON list of expected paths)
├── parameters              (JSON, reserved for future use)
├── resource_identifiers    (declared via data_resources relationship)
├── build_strategy          ("institutional" | "custom")
├── build_status            (environment_not_built | building | ready | failed)
├── build_error             (error message if build failed)
├── execution_image_id      (FK → ExecutionImage, set after successful build)
├── created_at
└── updated_at
```

### Build Strategy

Every Analysis Bundle declares an explicit **Build Strategy**. This is a researcher decision, not an inference from bundle contents. The platform never inspects bundle files to determine how the image should be built — the strategy is part of the bundle's metadata and becomes part of its immutable provenance.

Two strategies are currently supported:

| Strategy | Behaviour |
|----------|-----------|
| **Institutional Build** | Uses the curated builder template for the selected Execution Environment. The standard, default path. |
| **Custom Build** | Uses a `Dockerfile` provided in the root of the Analysis Bundle. Required for this strategy; ignored in Institutional Build. |

The strategy is enforced at submission time:

- **Custom Build**: the bundle **must** contain a `Dockerfile` at its root.
- **Institutional Build**: any root-level `Dockerfile` is ignored. The execution mode determines behaviour — not file presence.

The `build_strategy` metadata field is the single source of truth. Bundle contents are not inspected for institutional builds.

#### Custom Build Convention

Custom Build extends the institutional Execution Environment. The supported pattern is:

```dockerfile
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
```

`BASE_IMAGE` is the image reference of the selected Execution Environment. A researcher using Custom Build is expected to extend this image. Technically, the Dockerfile could ignore `BASE_IMAGE` and start from any base, but doing so breaks the execution contract — the resulting image may lack required directories (`/analysis`, `/data`, `/output`), the `nobody` user, and other runtime assumptions. Execution failures from this are self-correcting: the researcher updates their Dockerfile to match the contract.

The platform does not parse or validate Dockerfile content. The execution contract is enforced through natural execution failure, not static analysis.

#### Capability

Custom Build requires the `build.customize` capability. This is granted to trusted roles (maintainer, admin) and can be assigned to individual users through the admin user management interface. Researchers without this capability see only "Institutional Build" as an option.

### Governance Lifecycle

Analysis Bundles follow a governed lifecycle:

```
DRAFT
  │ (bundle.submit)
  ▼
SUBMITTED
  │ (bundle.review)
  ├──→ APPROVED_FOR_EXECUTION
  └──→ REJECTED

APPROVED_FOR_EXECUTION
  │ (bundle.review — versioning)
  └──→ SUPERSEDED
```

- **DRAFT** — The bundle is being created/edited. Only the owner can modify it. Strategy may be changed and bundle contents may not yet be consistent with the strategy.
- **SUBMITTED** — The owner has submitted the bundle for review. Strategy and contents are validated for consistency at this transition point. No further edits allowed.
- **APPROVED_FOR_EXECUTION** — A reviewer (moderator or above) has approved the bundle. Execution requests can now reference it.
- **REJECTED** — A reviewer has rejected the bundle.
- **SUPERSEDED** — A previously approved bundle has been replaced by a newer version.

Transitions are enforced by `backend/app/workflow/bundle.py`.

Only bundles in `APPROVED_FOR_EXECUTION` status can be used to create Execution Requests.

### AI Analysis Summaries

After a bundle is uploaded, an optional **AI review** may be generated asynchronously. The review provides a natural-language summary of what the uploaded analysis appears to do. This is a non-blocking, advisory feature:

- The review runs as a **background task** immediately after upload.
- Execution never depends on the review succeeding.
- Reviews are **cached per bundle** and reused until explicitly refreshed.

AI assistance is disabled by default (`AI_ASSIST_ENABLED=false`).

---

## Validation Run

A **Validation Run** is an advisory operational check that executes an Analysis Bundle against representative datasets before submission. It verifies operational correctness — whether the analysis code executes successfully — not scientific correctness.

### Architectural Principles

- Validation uses the **same execution pipeline** as institutional execution (worker, Docker executor, image build, logging, timeout handling)
- Validation mounts **representative datasets only** — governed data resources are never accessed
- Representative datasets are **repository-backed publication artefacts**, located at `{RESOURCE_MANIFEST_DIR}/{resource_identifier}/representative/`
- Representative data uses the **same directory structure and filenames** as governed data — analysis code does not change between validation and production
- Validation outputs are **transient** — stored as metadata on the ValidationRequest, not as OutputSet records
- Validation is **never a submission gate** — researchers may always submit without validating
- Validation is **researcher-visible only** — outputs are not visible to other project members or administrators

### ValidationRequest Model

ValidationRequest is independent of ExecutionRequest, OutputSet, and governance:

```
ValidationRequest
├── id                      (UUID, auto-generated)
├── project_id              (FK → Project)
├── analysis_bundle_id      (FK → AnalysisBundle)
├── name                    (human-readable label)
├── timeout_seconds         (default 3600, minimum 60)
├── parameter_overrides     (JSON dict)
├── status                  (enum: pending, running, completed, failed, cancelled)
├── log                     (execution log text)
├── output_files            (JSON list of {filename, size})
├── bundle_content_hash     (execution fingerprint — SHA-256 of files + config)
├── requested_by_id         (FK → User)
├── created_at
└── updated_at
```

### Bundle Consistency

An **execution fingerprint** is computed at validation request creation time, covering everything that affects execution:

- uploaded file contents
- execution environment identifier
- entrypoint
- interpreter
- arguments
- resource identifiers (sorted deterministically)
- build strategy

The fingerprint is recomputed when checking bundle status. If the current fingerprint differs from the stored one, the bundle has changed since validation. The UI surfaces this as:

| Condition | Display |
|-----------|---------|
| No validation run exists | *(no indicator)* |
| Bundle matches last validation | ✅ **Validated** |
| Bundle changed since validation | ⚠️ **Bundle has changed since validation** |

### Execution Flow

```
Researcher clicks "Run Validation"
         │
         ▼
Save pending bundle changes
         │
         ▼
Create ValidationRequest (status: PENDING)
         │
         ▼
Worker polls PENDING → RUNNING
         │
         ▼
DockerExecutor launches container with representative data mounts
         │
         ▼
Analysis executes against representative data
         │
         ▼
Worker captures outputs (transient, no OutputSet)
         │
         ▼
ValidationRequest → COMPLETED (or FAILED)
```

---

## Execution Requests

An **Execution Request** represents the intention to run an approved Analysis Bundle. It is the researcher-facing object, created within a Project by selecting an existing approved bundle.

### Distinction from Analysis Bundles

| Concept | Role |
|---------|------|
| Analysis Bundle | *What* to run — the analysis description, script, and declared data needs |
| Execution Request | *When* to run — an intent to execute a specific bundle with specific parameters |

A single Analysis Bundle may be used to create many Execution Requests.

### Request Model

```
ExecutionRequest
├── id                      (UUID, auto-generated)
├── project_id              (FK → Project)
├── analysis_bundle_id      (FK → AnalysisBundle)
├── name                    (human-readable label)
├── timeout_seconds         (default 3600, minimum 60)
├── parameter_overrides     (JSON dict, reserved for future parameter overrides)
├── status                  (enum: pending, running, completed, failed, cancelled)
├── log                     (execution log text)
├── requested_by_id         (FK → User)
├── created_at
└── updated_at
```

### Status Lifecycle

```
PENDING
  ↓
RUNNING   ←── (worker poll)
  ↓
COMPLETED
 or
FAILED
 or
CANCELLED
```

### Relationship Diagram

```
Project
    ├── AnalysisBundle ──── ExecutionEnvironment
    │         │                    │
    │         └── DataResources    │
    │                              │
    └── ExecutionRequest ──────────┘
              │
              └── OutputSet
                    ├── Output files
                    └── Release Package
```

---

## Output Set Governance

Execution outputs are governed as a collection — the **Output Set** — not as individual files. The governed object is "the result of an execution", and its lifecycle is separate from both the execution request lifecycle and the file metadata.

### Governing Model

```
Execution Request
        │
        ▼
Output Set  (governed artefact)
        │
        ├── Output files (individual artefacts, no lifecycle)
        ├── Execution metadata
        └── Release Package (ZIP, created on Release)
```

### Output Set Lifecycle

```
PENDING_REVIEW
      │ (output.review)
      ▼
APPROVED     ← Moderator review complete, safe to release
      │ (output.release)
      ▼
RELEASED     ← Release Package created and published
```

Rejection path:

```
PENDING_REVIEW
      │ (output.review)
      ▼
REJECTED
```

- **PENDING_REVIEW** — Execution completed. Moderators inspect all artefacts. Researchers cannot access any outputs.
- **APPROVED** — Moderator has determined the Output Set is safe. Authorises the platform to construct the Release Package, but does not yet expose outputs to researchers.
- **RELEASED** — The Release Package (ZIP) has been created and is available for researcher download. Only released Output Sets are visible to researchers.

Transitions are enforced by `backend/app/workflow/output_set.py`.

### Output Set Model

```
OutputSet
├── id                          (UUID, auto-generated)
├── execution_request_id        (FK → ExecutionRequest, unique, 1:1)
├── status                      (pending_review | approved | rejected | released)
├── release_package_path        (path to ZIP archive, set on Release)
├── release_package_size        (size in bytes, set on Release)
├── created_at
└── updated_at
```

### Output Model (individual artefacts)

Individual `Output` records are pure file metadata — they carry no lifecycle state:

```
Output
├── id                  (UUID, auto-generated)
├── output_set_id       (FK → OutputSet)
├── filename            ("summary.csv")
├── size                (bytes)
└── created_at
```

### Release Package

When an Output Set is **Released**, the platform creates a ZIP archive containing:

- All output files (preserving directory structure)
- `execution_metadata.json` (execution request details, file listing)

The Release Package is the sole delivery mechanism to researchers. Individual output files are never downloaded separately. Moderators retain the ability to inspect individual artefacts via the admin interface.

The working artefacts on disk (produced by the executor) and the Release Package (the researcher-facing distribution) are kept distinct.

### Storage

Output files are written to the execution container's local `/output` directory during analysis. After execution completes, the worker:

1. Retrieves them via the Docker API (`get_archive`) — a **pull** operation from inside the container (trust boundary preserved)
2. Persists them to a shared filesystem volume at `/outputs/{execution_request_id}/{filename}`
3. Creates an `OutputSet` record and registers each file as an `Output` record linked to that set
4. Release Packages are written to `/var/lib/epibridge/releases/` during the Release transition

---

## Execution Model

The platform itself never executes user code.

```
Researcher creates Execution Request (Pending)
        │
        ▼
Worker polls Pending → Running
        │
        ▼
DockerExecutor launches ephemeral container
        │
        ├── /analysis  (analysis bundle, via put_archive)
        ├── /data      (authorised resources, read-only bind mounts)
        ├── /work      (temporary writable storage)
        └── /output    (writable, container-local)
        │
        ▼
Container executes analysis
        │
        ▼
Worker captures outputs
        │
        ▼
Container destroyed
        │
        ▼
Worker registers Output records
        │
        ▼
Request → Completed or Failed
```

Each analysis executes inside an isolated container with:

- no internet access
- non-root user
- read-only dataset mounts
- temporary writable workspace
- configurable execution timeout (default 3600s, minimum 60s)
- automatic cleanup after completion

---

## Worker Architecture

The **Worker** is a standalone service that polls for Pending requests and processes them sequentially in priority order: ValidationRequests first (fast feedback for researchers), then BuildRequests (image construction), then ExecutionRequests (institutional execution).

### Polling

```
Worker Poll Loop
  │
  ├── 1. Poll: db → Pending ValidationRequest
  │         process_validation(request)
  │
  ├── 2. Poll: db → Pending BuildRequest
  │         process_build(request)
  │
  └── 3. Poll: db → Pending ExecutionRequest
            execute_request(request)
```

### Institutional Execution

For governed execution against production data resources:

```
Worker
  │
  ├── Resolve: bundle → analysis_dir, entrypoint, data_resources, env
  │
  ├── For each DataResource:
  │     provider.prepare_runtime(endpoint) → Mount + env vars
  │     combine with resource alias → /data/{alias}
  │
  ├── Create container (network_disabled, non-root, no-host-paths)
  │     put_archive(analysis_dir → /analysis)
  │     bind mounts for data resources
  │
  ├── Run with timeout
  │     ↓
  ├── Retrieve /output from container (get_archive)
  │     ↓
  ├── Register OutputSet and Output records
  │     ↓
  ├── Transition to Completed
  │
  └── Failure: capture stderr → Failed
```

### Validation Execution

For validation runs against representative datasets, the worker follows the same execution pipeline but:

- **Mounts representative data** from `{RESOURCE_MANIFEST_DIR}/{resource_identifier}/representative/` to `/data/{alias}/` instead of mounting governed data through the provider system
- **Outputs are transient** — stored as file metadata on the ValidationRequest record, not as OutputSet records
- **No governance** — no OutputSet, no review, no release package
- **Audit events** are operational only (`validation.completed`, `validation.failed`)

### Unified Mount Resolution

The worker uses a single `resolve_mounts(bundle, db, representative=False)` function that parameterises source path resolution. When `representative=True`, it resolves from the resource manifest directory. When `representative=False`, it resolves through the provider system. Both mount at the same target path (`/data/{alias}`), ensuring the same analysis code works against both governed and representative data.

### Executor Abstraction

The Worker delegates container management to an Executor interface:

```
Worker
  └── Executor (interface)
        └── run(image, analysis_dir, command, mounts, output_dir, timeout, env) → Result

Implementation:
  └── DockerExecutor (docker-py)
        ├── put_archive for analysis files
        ├── bind mounts for data resources
        ├── network_disabled
        ├── non-root user
        └── timeout enforcement
```

The executor is domain-agnostic. It knows nothing about bundles, resources, or environments — it only knows how to run a container.

### Analysis Delivery

Analysis Bundle files are delivered into the container via Docker's `put_archive` API. The worker copies the bundle's source directory into `/analysis` inside the container.

### Data Delivery

Data Resources use the Provider abstraction. The worker calls `provider.prepare_runtime(endpoint)` for each resource to obtain mount configurations and environment variables. These are passed to the Executor as bind mounts.

---

## Environment Builder

The **Environment Builder** subsystem transforms an Analysis Bundle (its dependency specification and, optionally, a custom build definition) into a reusable Docker image (Execution Image). This separates environment construction from analysis execution.

### Architectural relationship

The Builder is one stage in a pipeline that connects researcher intent to governed execution:

```
Execution Environment        ← institutional runtime contract
        +
Build Strategy               ← researcher decision (explicit metadata)
        +
Analysis Bundle              ← researcher artefact (immutable on submit)
        ↓
Execution Image               ← built artefact (cached by dependency hash)
        ↓
Governed Execution            ← isolated container, least privilege
        ↓
Output Set → Release          ← governed results delivery
```

Each stage is independently governed. The Execution Environment is an institutional asset. The Build Strategy and Analysis Bundle are researcher artefacts. The Execution Image is a system artefact produced by the builder and cached for reuse. Governed Execution and Release are institutional oversight functions.

### Builder abstraction

The builder is a policy-free execution engine. It receives a Dockerfile path and dependency files, builds the image, and returns the result. The builder never decides which Dockerfile to use or whether to apply a custom build — that responsibility belongs to the orchestration layer.

```python
class EnvironmentBuilder(ABC):
    def identifier(self) -> str: ...
    def dependency_hash(self, bundle_path: Path) -> str: ...
    def default_dependency_filename(self) -> str: ...
    @classmethod
    def get_template_dockerfile(cls) -> Path: ...
    def build(self, *, bundle_path, dockerfile, base_image, image_tag) -> BuildResult: ...
```

The orchestration layer (in the worker) selects the Dockerfile:

```
bundle.build_strategy == "custom"
    → dockerfile = bundle_path / "Dockerfile"
bundle.build_strategy == "institutional"
    → dockerfile = builder.get_template_dockerfile()
```

### Curated Dockerfile templates

Institutional templates live in `backend/builder_templates/{builder_type}/Dockerfile`. These are used only when the Build Strategy is Institutional.

### Build pipeline

```
Execution Environment
        +
Build Strategy
        +
Analysis Bundle (dependency + optional Dockerfile)
     ↓
Environment Builder selection (by runtime prefix)
     ↓
Compute dependency hash:
  Institutional → hash(dependency_file)
  Custom       → hash(dependency_file + Dockerfile)
     ↓
Cache lookup: (execution_environment_id, dependency_hash)
     ├── HIT → nothing to do
     └── MISS → Create BuildRequest(status=PENDING)
                   ↓
            Worker polls PENDING → BUILDING
                   ↓
            Orchestration layer selects Dockerfile
              by build_strategy
                   ↓
            builder.build(
                bundle_path=bundle_path,
                dockerfile=dockerfile,   ← explicit, not inferred
                base_image=env.image_reference,
                image_tag=tag,
            )
                   ↓
            ExecutionImage record created (cache)
                   ↓
            BuildRequest → COMPLETED
```

### Two distinct models

| Model | Role |
|-------|------|
| `BuildRequest` | Work item. Status: PENDING → BUILDING → COMPLETED / FAILED. |
| `ExecutionImage` | Cached artefact. Keyed by `(execution_environment_id, dependency_hash)`. |

### Provenance

The Build Strategy is recorded on the Analysis Bundle as explicit metadata (`build_strategy`). The dependency hash captures the content of both the dependency file and (for Custom Build) the custom Dockerfile. The `ExecutionImage` record captures the build outcome. Together, these provide a complete provenance chain for every execution image, regardless of strategy.

---

## Researcher Workflows

EpiBridge validates three distinct researcher workflows through Playwright e2e tests:

### 1. Canonical Governed Research Workflow

```
1.  User authenticates (login)
2.  Create a Project
3.  Attach a Data Resource to the Project
4.  Create an Analysis Bundle (define metadata, select environment, declare resources)
5.  Upload bundle ZIP (source code, entrypoint)
6.  Submit bundle (DRAFT → SUBMITTED)
7.  Review and approve bundle (SUBMITTED → APPROVED_FOR_EXECUTION)
8.  Create Execution Request (references the approved bundle)
9.  Worker executes analysis (PENDING → RUNNING → COMPLETED)
10. Output Set enters PENDING_REVIEW
11. Review and approve Output Set (PENDING_REVIEW → APPROVED)
12. Release Output Set (APPROVED → RELEASED) — Release Package ZIP created
13. Download Release Package (contains outputs + execution metadata)
```

The canonical workflow is validated by `frontend/e2e/canonical-workflow.spec.ts`.

### 2. Custom Environment Workflow

```
1.  User authenticates (maintainer)
2.  Create a Project
3.  Create a Draft Bundle with Custom Build strategy
4.  Upload bundle ZIP containing a root-level Dockerfile
5.  Submit for review
6.  Approve the bundle
7.  Request execution
8.  Worker builds from the custom Dockerfile
9.  Worker executes against governed data
10. Verify the custom Dockerfile was genuinely used (provenance marker)
```

The custom build workflow is validated by `frontend/e2e/custom-build-workflow.spec.ts`.

### 3. Validation Workflow

```
1.  User authenticates
2.  Browse institutional publications (environments, resources)
3.  Create a Project
4.  Attach a Data Resource to the Project
5.  Create a Draft Bundle
6.  Upload analysis code that reads representative data
7.  Run Validation (PENDING → RUNNING → COMPLETED)
8.  View validation logs and output files
9.  Verify "Validated" bundle consistency indicator
10. Modify the bundle and verify "Bundle has changed since validation"
11. Re-run validation to restore "Validated" state
12. Submit for Review
```

The validation workflow is validated by `frontend/e2e/validation-workflow.spec.ts`. It proves that researchers can verify operational correctness against representative datasets before submitting for institutional governance.

---

## Operational Behaviour

### Logging

Logging is configured centrally at startup by `configure_logging()` in `app.core.logging`. The configuration uses Python's `logging.config.dictConfig`:

- **Output**: stderr via `StreamHandler` (compatible with container log aggregation).
- **Format**: `%(asctime)s [%(levelname)s] %(name)s: %(message)s` with UTC timestamps.
- **Level**: Controlled by `LOG_LEVEL` environment variable (default `INFO`).
- **Noise suppression**: `alembic`, `asyncio`, `sqlalchemy.engine`, `uvicorn`, and `uvicorn.access` loggers default to `WARN` to reduce framework noise.

No request bodies, response bodies, authentication tokens, session identifiers, or researcher data are logged.

### Health Checks

`GET /api/health` is an unauthenticated endpoint that verifies platform dependencies:

- **PostgreSQL**: Executes `SELECT 1` via a live database session.
- **Redis**: Connects and issues `PING` with a 3-second socket timeout.

If all dependencies respond, `status` is `"ok"`. If any dependency is unreachable, `status` is `"degraded"` and the affected field is reported as `"disconnected"`. No internal implementation details are exposed.

### Exception Handling

Three global exception handlers provide a safety net for unexpected failures:

| Exception | HTTP Status | Response Body | Logged At |
|-----------|-------------|---------------|-----------|
| `PolicyError` | 403 | `{"detail": "Forbidden"}` | — |
| `ValueError` | 422 | `{"detail": "Invalid request."}` | WARNING |
| `Exception` (fallback) | 500 | `{"detail": "Internal Server Error"}` | ERROR (with traceback) |

Route-specific error handling takes precedence. The global handlers only fire when exceptions escape route-level catch blocks.

### Worker Resilience

The worker runs as a single-threaded polling loop that processes `ValidationRequest`, `BuildRequest`, and `ExecutionRequest` items in priority order. Three resilience mechanisms prevent the worker from crashing or leaking work:

1. **Database connection backoff**: If the database is unreachable, the worker retries with exponential backoff (1s, 2s, 4s, ..., max 60s). Backoff resets on successful connection.
2. **Outer catch-all**: Any unexpected exception during a poll cycle is logged with a full traceback. The loop continues to the next cycle.
3. **Graceful shutdown**: `SIGTERM` and `SIGINT` cause the worker to complete its current iteration (including any in-flight build or execution) before exiting. Running containers are left for Docker to manage.

Items that fail during processing are transitioned to `FAILED` status in the database. They remain visible to operators through the admin API and are not silently retried.

Identity validation (capability boundaries for each role) is maintained as separate integration tests.

---

## Architectural Principles

1. EpiBridge does not own scientific data.
2. Data Resources represent institutional assets, registered from manifests.
3. Projects represent permission to analyse one or more institutional assets.
4. Providers validate endpoints and prepare execution views.
5. The deployment owns physical storage. EpiBridge owns the catalogue and execution model.
6. The runtime contract is `/read-only-data`, `/work`, `/data`, and `/output`.
7. Analysis containers receive only authorised resources.
8. Analyses use standard language interfaces rather than an EpiBridge SDK.
9. Analysis Bundles are researcher artefacts, created within Projects and owned by their authors.
10. Authorisation is capability-based, not role-based.
11. Project Membership is scope only — no roles or capabilities on membership.
12. Two-stage governance: execution approval (bundle review) then output approval (output set review and release).
13. The Release Package is the sole delivery mechanism for research outputs.
14. The Environment Builder is a separate subsystem — execution does not depend on build.
15. **Build Strategy is explicit researcher metadata on the Analysis Bundle. The platform never infers build behaviour from bundle contents.**
16. **The Execution Environment defines the institutional execution contract. Custom Build extends it; it does not create new execution environments.**
17. **Capability enforcement happens at creation and submission, not during approval. The reviewer evaluates the immutable artefact, not the entitlement.**
18. **Operational state belongs in PostgreSQL. Institutional knowledge belongs in the repository.**
19. **Validation Run is advisory operational verification. It never replaces or bypasses institutional governance.**
20. **Representative datasets are repository-backed publication artefacts. They are not DataResource records.**
21. **Validation mounts the same paths as production execution. Analysis code does not change between validation and production.**

---

## Future Direction

### Post-MVP

- Pagination on list endpoints
- Role and capability management UI (read-only currently available)
- OIDC / enterprise IAM integration
- Statistical disclosure control automation
- Kubernetes execution backend
- Federation (cross-institution analysis)
- Notifications, quotas, multiple execution backends
