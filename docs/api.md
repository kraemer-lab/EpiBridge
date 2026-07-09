# API Overview

## Authentication

Authentication uses the **Local Identity Provider** with email/password login and
server-side sessions backed by PostgreSQL.

Sessions are maintained via HTTP-only secure cookies.

- `POST /api/auth/login` — authenticate with email and password
- `POST /api/auth/logout` — destroy the current session
- `GET /api/auth/session` — verify the current session and return user info

Session configuration (TTL, rate limiting) is managed through environment
variables documented in `.env.example`.

---

## Core Resources

### Users

- `POST /api/admin/users` — create a user (requires `user.manage`)
- `GET /api/admin/users` — list all users (requires `user.manage`)
- `GET /api/admin/users/{id}` — get user details (requires `user.manage`)

### Projects

- `POST /api/projects` — create a project
- `GET /api/projects` — list projects for the current user
- `GET /api/projects/{project_id}` — get project details
- `PATCH /api/projects/{project_id}` — update project metadata

#### Project Members

- `GET /api/projects/{project_id}/members` — list members
- `POST /api/projects/{project_id}/members` — add a member
- `DELETE /api/projects/{project_id}/members/{user_id}` — remove a member

#### Project Resources

- `GET /api/projects/{project_id}/resources` — list allocated resources
- `POST /api/projects/{project_id}/resources` — allocate a resource
- `DELETE /api/projects/{project_id}/resources/{resource_id}` — deallocate

### Analysis Bundles

- `POST /api/projects/{project_id}/bundles` — create a bundle within a project
- `POST /api/projects/{project_id}/bundles/upload` — upload and register a bundle ZIP archive
- `GET /api/projects/{project_id}/bundles` — list bundles in a project
- `GET /api/projects/{project_id}/bundles/{id}` — get bundle details (includes `ai_review` if AI assistance is configured)
- `PUT /api/projects/{project_id}/bundles/{id}` — update a bundle
- `POST /api/projects/{project_id}/bundles/{id}/ai-review` — trigger, retry, or refresh an AI analysis summary

### Execution Requests

- `POST /api/projects/{project_id}/execution-requests` — create an execution request within a project
- `GET /api/projects/{project_id}/execution-requests` — list execution requests in a project
- `GET /api/projects/{project_id}/execution-requests/{id}` — get execution request details
- `GET /api/admin/execution-requests` — list all execution requests (admin)
- `GET /api/admin/execution-requests/{id}` — get execution request details (admin)
- `GET /api/admin/execution-requests/{id}/outputs` — get Output Set for an execution (admin)

### Output Sets

Outputs are governed as a collection (Output Set), not individually. The Output Set lifecycle is `PENDING_REVIEW → APPROVED → RELEASED`. Release creates a ZIP Release Package.

- `GET /api/projects/{project_id}/execution-requests/{id}/outputs` — get the released Output Set (researcher-facing)
- `GET /api/projects/{project_id}/execution-requests/{id}/outputs/download` — download the Release Package ZIP (researcher-facing, only if RELEASED)
- `GET /api/admin/output-sets` — list all Output Sets (admin, all statuses)
- `GET /api/admin/output-sets/{id}` — get Output Set with member files (admin)
- `POST /api/admin/output-sets/{id}/approve` — approve (PENDING_REVIEW → APPROVED)
- `POST /api/admin/output-sets/{id}/reject` — reject (PENDING_REVIEW → REJECTED)
- `POST /api/admin/output-sets/{id}/release` — release (APPROVED → RELEASED), creates ZIP
- `GET /api/admin/outputs/{id}` — inspect individual output artefact (admin)

### Data Resources

- `GET /api/admin/resources` — list all data resources (admin)
- `GET /api/admin/resources/{id}` — get data resource details (admin)

### Execution Environments

- `GET /api/execution-environments` — list available execution environments (researcher-facing, active only)
- `GET /api/admin/execution-environments` — list all execution environments (admin)
- `GET /api/admin/execution-environments/{id}` — get execution environment details (admin)

### Administration

- `POST /api/admin/bundles/{id}/approve` — approve a bundle for execution
- `POST /api/admin/bundles/{id}/reject` — reject a bundle
- `POST /api/admin/bundles/{id}/supersede` — supersede a bundle
- `GET /api/admin/bundles` — list all bundles (admin)
- `GET /api/admin/bundles/{id}` — get bundle details (admin)
- `POST /api/admin/output-sets/{id}/approve` — approve output set
- `POST /api/admin/output-sets/{id}/reject` — reject output set
- `POST /api/admin/output-sets/{id}/release` — release output set
- `GET /api/admin/audit-events` — query the audit ledger
- `GET /api/admin/users` — list all users
- `GET /api/admin/users/{id}` — get user details
- `POST /api/admin/users` — create a user

### Health

- `GET /api/health` — platform operational status (unauthenticated)

---

## Job Lifecycle

```
DRAFT → SUBMITTED → APPROVED_FOR_EXECUTION
                                   ↓
Execution Request → PENDING → RUNNING → COMPLETED / FAILED
                                   ↓
                           Output Set → PENDING_REVIEW → APPROVED → RELEASED
```

---

## Design Principles

- All endpoints are RESTful.
- Business logic lives in services, not controllers.
- API endpoints remain thin — they coordinate validation, authorisation, and service calls.
- Authorisation is capability-based, checked via `app.auth.policy`.
- All governance actions are recorded in the audit ledger.
