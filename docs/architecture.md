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
* Dataset
* Job
* JobFile
* Output
* Approval
* AuditLog

⸻

## Analysis Submission

Researchers should submit an analysis bundle rather than arbitrary scripts.

Example:

analysis.zip
manifest.yaml
run.py
requirements.txt
README.md

This improves reproducibility.

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

Create a storage abstraction.

storage.save()
storage.load()
storage.delete()

Initially backed by the local filesystem.

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

# Design Principles

1. Move computation to the data.
2. Never expose database access.
3. Every analysis executes inside an isolated container.
4. Human approval before execution.
5. Human approval before outputs leave the environment.
6. Complete audit trail.
7. Portable deployment.
8. Cloud-ready but cloud-independent.
9. Modular services.
10. Reproducible execution.

⸻
# MVP Scope

* Authentication
* Database
* User management
* Projects

* Job submission
* Dashboard

* Approval workflow

* Worker
* Docker execution

* Output approval
* Downloads
* Audit logging

This provides a complete end-to-end proof of concept while leaving advanced features (notifications, quotas, federation, Kubernetes, multiple execution backends, statistical disclosure control automation) for later iterations.
