# EpiBridge - Architecture Summary

## Vision

EpiBridge is a secure remote analysis platform for epidemiology and other sensitive research data.

The guiding principle is:

Move the computation to the data, not the data to the computation.

Rather than giving researchers direct access to sensitive datasets, EpiBridge allows them to develop analyses locally using schema documentation and synthetic/sample data, submit analysis jobs to the data owner, execute those jobs within a secure institutional environment, and receive approved outputs after review.

⸻

## High-level Workflow

Researcher
    │
    ▼
Develop analysis locally
(schema + synthetic data)
    │
    ▼
Submit analysis bundle
    │
    ▼
Administrator approves execution
    │
    ▼
Analysis runs inside secure environment
    │
    ▼
Outputs generated
    │
    ▼
Administrator approves outputs
    │
    ▼
Researcher downloads approved results

Sensitive data never leaves the institution.

⸻

## Deployment Model

Each institution runs its own EpiBridge instance inside a restricted Linux virtual machine.

Institution
└── Virtual Machine
        │
        ├── EpiBridge Platform
        ├── Local Sensitive Data
        └── Analysis Containers

The VM is the trust boundary.

The VM hosts:

* Next.js frontend
* FastAPI backend
* PostgreSQL
* Redis
* Worker service
* Audit logs
* Docker Engine

No external system accesses the sensitive data directly.

⸻

## Execution Model

The platform itself never executes user code.

Instead:

User submits job
        │
        ▼
Worker service
        │
        ▼
Launch ephemeral Docker container
        │
        ▼
Container reads dataset
        │
        ▼
Produces outputs
        │
        ▼
Container destroyed

Each analysis executes inside an isolated container.

Container security should include:

* no internet access
* non-root user
* read-only dataset mount
* temporary writable workspace
* CPU limits
* memory limits
* execution timeout
* automatic cleanup after completion

⸻

## Platform Components

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

⸻

## Technology Stack

### Frontend

* Next.js
* React
* TypeScript

### Backend

* FastAPI
* SQLAlchemy
* Alembic

## Authentication

* Firebase Authentication
* Email/password
* Google
* Microsoft

Application permissions are managed within PostgreSQL.

## Database

* PostgreSQL

## Queue

* Redis
* Celery or Dramatiq

## Execution

* Docker

## Deployment

* Docker Compose initially
* Kubernetes later

⸻

## Authentication and Authorisation

Authentication is handled by Firebase.

Authorisation is handled internally.

Example roles:

* Researcher
* Project Admin
* Data Steward
* System Administrator

Permissions are stored in PostgreSQL.

The application should never depend directly on Firebase beyond validating JWT tokens.

⸻

## Repository Structure

epibridge/
frontend/
    Next.js
backend/
    FastAPI
worker/
    Job execution service
shared/
    Shared schemas/types
containers/
    Base analysis images
examples/
    Synthetic datasets
    Analysis templates
docs/
scripts/

Single monorepo.

⸻
## Backend Structure

backend/app/
api/
services/
models/
schemas/
db/
auth/
core/

Business logic should live in the service layer rather than API endpoints.

⸻

## Frontend Pages

### Researchers

* Login
* Dashboard
* Projects
* Submit Job
* Job Status
* Outputs
* Settings

### Administrators

* Pending Jobs
* Pending Outputs
* Projects
* Users
* Audit Logs

⸻

## Database Entities

Core entities:

* User
* Project
* Membership
* DataResource — institutional asset available for analysis (not owned by EpiBridge)
* AnalysisBundle — researcher-created artefact describing an analysis and its requirements
* ResourceProvider — validates resource endpoints and describes runtime requirements
* Job
* JobFile
* Output
* Approval
* AuditLog

⸻

## Data Resources

EpiBridge does not own, store, or manage scientific data.

A **Data Resource** represents an existing institutional data asset that has been
registered for analysis. The institution owns and manages the underlying data;
EpiBridge provides a catalogue of available resources, access control, and secure
execution.

### Resource Providers

A **Resource Provider** is an abstraction that knows how to make a particular type
of data resource available for analysis. Implementations include:

* **CsvProvider** — a CSV file available at a known path
* **DuckDBProvider** — a DuckDB database
* **PostgresProvider** — a PostgreSQL database
* **ExcelProvider** — an Excel workbook
* **ParquetProvider** — a directory of Parquet files

The provider has two responsibilities:

1. **`validate_endpoint(endpoint)`** — is the endpoint configuration well-formed?
2. **`prepare_runtime(endpoint)`** — what mount points and environment variables are
   needed to expose this resource inside an analysis container?

Providers describe runtime requirements in platform-agnostic terms (`Mount`,
`RuntimeConfig`). An Executor (Docker, Kubernetes, Slurm, etc.) translates these into
the corresponding infrastructure.

### Resource Identifiers

Every Data Resource has three identifiers with distinct responsibilities:

| Field | Purpose | Stability |
|-------|---------|-----------|
| `id` | Internal database UUID. Auto-generated. | Never changes |
| `identifier` | Stable institutional identity used for registration and reconciliation. Defined in the manifest. | Stable once set |
| `alias` | Stable runtime namespace used inside analysis containers (`/data/{alias}`). Defined in the manifest. | Stable once set |

The analysis always uses the alias. Display names (`name`) can be improved
without breaking existing analyses because the runtime contract references
`/data/{alias}`, not `/data/{name}`.

The registration service reconciles resources using `identifier` — it is the
canonical key for matching manifest entries to database records. A resource
may change its `alias` (via a manifest update) without becoming a different
institutional resource, because `identifier` remains the stable identity.

### Registration Process

Data Resources are registered from YAML manifests. The database is a runtime
index; the manifest is the source of truth.

The registration workflow:

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

Validation includes:
- Required fields present: `identifier`, `name`, `alias`, `provider`, `endpoint`
- Provider type exists in the registry
- Provider's `validate_endpoint()` accepts the endpoint configuration
- No duplicate identifiers across manifests

Validation does NOT check that the underlying data resource currently exists.
That remains the deployment's responsibility.

### Development Startup

During development, when `auto_register_resources=True` (default), the
application automatically loads manifests from `examples/resources/` on
startup. This means `make dev` presents a small catalogue of available
Data Resources without requiring manual setup.

The registration process is idempotent: running it multiple times produces
the same result. Resources are identified by `identifier`, so manifest
updates are applied in-place rather than creating duplicates.

### Resource Manifests

### Project Association

A **Project** represents permission to analyse one or more Data Resources.
Projects do not own resources — they reference them through a many-to-many
relationship (`ProjectDataResource`). A single Data Resource may be associated
with multiple projects over time.

⸻

## Execution Environments

An **Execution Environment** is an institutional asset representing an approved
runtime in which an analysis may execute. Like Data Resources, they are curated
by the institution — researchers select from available environments rather than
specifying arbitrary runtime strings.

Execution Environments are not merely language versions. They represent curated
environments with specific packages and tooling:

* Python 3.13 Scientific (NumPy, SciPy, Pandas, scikit-learn)
* Python 3.13 Machine Learning (PyTorch, TensorFlow, XGBoost)
* R 4.5 Tidyverse (dplyr, ggplot2, tidyr)
* R 4.5 Spatial (sf, terra, sp)
* R 4.5 Bioconductor (DESeq2, limma, edgeR)

### Environment Model

```
ExecutionEnvironment
├── id              (UUID, auto-generated)
├── identifier      (stable institutional identity)
├── name            (human-readable display name)
├── runtime         ("python-3.13", "r-4.5", etc.)
├── description     (curated package summary)
├── status          ("active", "deprecated")
├── image_reference (Docker image tag, for future execution)
├── created_at
└── updated_at
```

### Registration

Execution Environments are seeded from YAML manifests on startup, following
the same pattern as Data Resources. The manifest is the source of truth; the
database is a runtime index.

```yaml
environments:
  - identifier: python-3.13-scientific
    name: Python 3.13 Scientific
    runtime: python-3.13
    description: "NumPy, SciPy, Pandas, Matplotlib, scikit-learn"
    status: active
    image_reference: "epibridge/python-3.13-scientific:latest"
```

Registration is idempotent — running it multiple times produces the same
result. Environments are identified by `identifier`, so manifest updates
are applied in-place.

### Future direction

Eventually trusted users will submit Dockerfiles that build new Execution
Environments. The `image_reference` field exists so this can be added
without schema changes. Dockerfile upload and image building are not
implemented in the current milestone.

⸻

## Analysis Bundles

An **Analysis Bundle** is a researcher-created artefact that describes an
analysis and its requirements. Researchers do not submit arbitrary scripts
to the platform — they submit Analysis Bundles. The bundle captures:

* the analysis metadata (name, version, description)
* a reference to an approved **Execution Environment** (the researcher selects
  from the curated catalogue; they do not type a runtime string)
* the entry point script
* the Data Resources the analysis expects (declared by institutional identifier)
* the expected outputs
* optional configuration parameters (thresholds, model options, etc.)

The bundle is a **researcher artefact**, not an infrastructure asset. It is
created within a Project and owned by the researcher who created it.

### Bundle Model

```
AnalysisBundle
├── id                      (UUID, auto-generated)
├── project_id              (FK → Project)
├── created_by_id           (FK → User)
├── execution_environment_id (FK → ExecutionEnvironment)
├── name
├── version
├── entrypoint
├── description
├── outputs                 (JSON list of expected paths)
├── parameters              (JSON, reserved for future use)
├── created_at
└── updated_at
```

The `runtime` field is resolved from the referenced ExecutionEnvironment at
read time — it is not stored on the bundle. This ensures researchers only
select approved environments and cannot specify arbitrary runtime strings.

### Relationship to Data Resources

A bundle declares which Data Resources it expects through a many-to-many
join table:

```
AnalysisBundle
    ↓
AnalysisBundleDataResource
    ↓
DataResource
```

The bundle references Data Resources by their institutional `identifier`.
At bundle creation time, the service validates that all declared resources
exist in the system. This gives referential integrity and provides a natural
place to extend access permissions in the future.

### Relationship to future Jobs

Jobs (next milestone) will bind an Analysis Bundle to a specific execution
request against authorised Data Resources. The relationship will be:

```
Project
    ↓
AnalysisBundle        DataResource
    ↓                       ↓
    └── Job ────────────────┘
          ↓
        Execution
          ↓
        Outputs
```

The bundle provides the executable description; the Job provides the
execution context (which resources, which parameters, which user).

⸻

## Trust Boundaries

EpiBridge defines three distinct trust boundaries, each with different
privileges and responsibilities.

```
Host
  └── Trusted Runtime (VM)
        └── Analysis Container
```

### Host

The host machine owns the physical or networked storage containing sensitive
institutional data (e.g. `/srv/data/`). EpiBridge never knows host paths and
never accesses host storage directly. The host is managed by institutional IT
and is outside EpiBridge's operational scope.

### Trusted Runtime (VM)

The deployment runs inside a restricted Linux virtual machine. This is the
EpiBridge platform boundary. The VM contains:

* All EpiBridge services (frontend, backend, database, worker)
* Docker Engine
* The Resource Registry (database index of registered data resources and
  execution environments)
* Institutional data resources exposed at a well-known location:
  `/read-only-data`

How resources arrive at `/read-only-data` (bind mount, NFS, cloud storage)
is the deployment's responsibility — never EpiBridge's.

### Analysis Container

The analysis container is the least-privileged environment. It is intentionally
isolated from the Trusted Runtime.

The container must never receive:

* `/read-only-data` — the full institutional data store
* Host storage paths
* The Resource Registry
* Deployment configuration

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

The Executor constructs this mount point from the provider's `RuntimeConfig`
and the resource's alias. The provider describes *what* to expose (source path,
type); the Executor decides *where* (`/data/{alias}`).

#### Security boundary

> The analysis container must never receive access to `/read-only-data`.

The Executor enforces this by mounting only the authorised subset. A compromised
container cannot enumerate or access unauthorised resources.

### Summary

| Boundary | Contents | Privilege |
|----------|----------|-----------|
| Host | Physical storage, institutional IT | Most privileged |
| Trusted Runtime (VM) | EpiBridge services, `/read-only-data`, Registry | Medium |
| Analysis Container | `/work`, `/data/{alias}`, `/output` | Least privileged |

This three-layer design ensures that even a fully compromised analysis container
cannot access unauthorised data or infrastructure configuration.

⸻

## Institutional Infrastructure vs. Researcher Artefacts

EpiBridge makes a clear distinction between two categories of entities.

### Institutional Infrastructure (curated by the institution)

* **Data Resources** — registered institutional data assets. The institution
  owns and manages the underlying data; EpiBridge provides the catalogue and
  access control.
* **Execution Environments** — approved runtimes in which analyses execute.
  The institution curates the available environments and their contents.

These are seeded from YAML manifests on startup. The manifest is the source of
truth; the database is a runtime index. Researchers do not create or modify
institutional infrastructure during normal workflows.

### Researcher Artefacts (created by researchers)

* **Projects** — permission boundaries for analysing specific Data Resources.
* **Analysis Bundles** — descriptions of analyses, referencing approved
  Data Resources and Execution Environments.

Researchers work exclusively with researcher artefacts. They select from
available institutional infrastructure but do not define it.

### Why this matters

This separation of concerns means:

1. Researchers never need to know where data physically resides or how it is
   mounted.
2. Researchers never need to know which container image is used or how the
   runtime is constructed.
3. The institution retains full control over what data is available and what
   execution environments are approved.
4. Security reviews focus on the infrastructure boundary, not individual
   analyses.

⸻

## Resource Manifests

Data Resources are ultimately declared using YAML manifests. The administration
UI is an operational convenience over this model, not the source of truth.

```yaml
resources:
  - name: Mexico Dengue Surveillance 2026
    provider: csv
    endpoint:
      path: mexico_dengue_2026/dengue.csv

  - name: UK Biobank Phenotypes
    provider: duckdb
    endpoint:
      path: ukbb/phenotypes.duckdb
```

Manifests will be introduced in a dedicated milestone once registration
workflows are designed.

⸻

## Standard Interfaces

Analyses use standard language interfaces. There is no EpiBridge runtime SDK
and the analysis should not need to know that EpiBridge exists.

```python
# CSV — standard pandas
pd.read_csv("/data/mexico_dengue_2026/dengue.csv")

# DuckDB — standard duckdb
duckdb.connect("/data/ukbb/phenotypes.duckdb")

# PostgreSQL — standard sqlalchemy
sqlalchemy.create_engine("postgresql://host/db")
```

The analysis receives references through well-known environment variables
(such as `PGHOST`, `PGDATABASE`) or through the file paths under `/data/{alias}`.

⸻

⸻

### Job Lifecycle

Draft
↓
Submitted
↓
Pending Approval
↓
Approved
↓
Running
↓
Completed
↓
Output Review
↓
Approved
↓
Downloaded

⸻

### Audit Trail

Everything should be recorded.

Examples:

* User logged in
* Job submitted
* Job approved
* Job rejected
* Job started
* Job completed
* Outputs approved
* Outputs downloaded

Audit logs should be immutable.

⸻
## Storage

Create a storage abstraction for *job files and outputs*.

storage.save()
storage.load()
storage.delete()

Data resources are never ingested or stored by EpiBridge — they remain under
institutional control and are exposed through the runtime contract (/read-only-data).

The storage abstraction is initially backed by the local filesystem.

Later replace with:

* S3
* MinIO
* Azure Blob

No application code should need changing.

⸻

# Execution Abstraction

The Worker never manages containers directly.

It delegates to an executor interface:

```
Worker
  └── Executor (interface)
        └── run(job) → Result

Implementations:
  ├── DockerExecutor      ← communicates with Docker Engine
  ├── KubernetesExecutor  ← creates Kubernetes Jobs
  └── SlurmExecutor       ← submits Slurm batch jobs
```

The platform must not depend on any specific execution backend.

Only the `DockerExecutor` talks to Docker Engine. The Worker holds a reference to whatever `Executor` implementation is configured at startup — it never imports or calls the Docker SDK directly.

This means:
- The Docker socket is a private implementation detail of `DockerExecutor`, not a platform concern
- Replacing Docker with Kubernetes or Slurm requires zero changes outside the Worker

```
Worker
  └── Executor (interface)
        └── DockerExecutor
              └── Docker Engine (via socket)
                    └── Ephemeral analysis container
                          ├── datasets (read-only)
                          ├── workspace (temporary)
                          └── output directory (writable)
```

The executor is responsible for:
- pulling the analysis image (if not present)
- creating the container with resource limits, read-only dataset mounts, and no network
- streaming logs to the audit trail
- collecting the exit code and output files
- destroying the container after completion

⸻

# Cloud Migration

Initial deployment:

Single Ubuntu VM
Docker Compose

Future:

Kubernetes
API Pods
Worker Pods
PostgreSQL
Redis
Ingress

Very little application code should change.

⸻

# Federation

Long-term architecture:

Oxford
    EpiBridge
        │
    Local Data
Imperial
    EpiBridge
        │
    Local Data
LSHTM
    EpiBridge
        │
    Local Data

Researchers submit analyses independently to each institution.

Sensitive datasets remain local.

Only approved outputs are returned.

⸻

# Architectural Principles

1. EpiBridge does not own scientific data.
2. Data Resources represent institutional assets.
3. Projects represent permission to analyse one or more institutional assets.
4. Providers validate endpoints and prepare execution views.
5. The deployment owns physical storage.
6. EpiBridge owns the catalogue and execution model.
7. The runtime contract is `/read-only-data`, `/work`, `/data`, and `/output`.
8. Analysis containers receive only authorised resources.
9. Analyses use standard language interfaces rather than an EpiBridge SDK.
10. Analysis Bundles are researcher artefacts, not infrastructure. They are created within Projects and owned by their authors.

⸻
# MVP Scope

* Authentication
* Database
* User management
* Projects

* Data Resource model
* Resource Provider abstraction

* Job submission
* Dashboard

* Approval workflow

* Worker
* Docker execution

* Output approval
* Downloads
* Audit logging

This provides a complete end-to-end proof of concept while leaving advanced features (notifications, quotas, federation, Kubernetes, multiple execution backends, statistical disclosure control automation) for later iterations.
