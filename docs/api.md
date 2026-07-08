# API Overview

## Authentication

Authentication is performed using Firebase JWT tokens.

The backend validates the token and maps it to an internal user.

⸻

## Core Resources

### Users

* Login
* Profile

### Projects

* List projects
* Project details
* Members

### Execution Requests

* `POST /projects/{project_id}/execution-requests` — create an execution request
* `GET /projects/{project_id}/execution-requests` — list execution requests in a project
* `GET /projects/{project_id}/execution-requests/{id}` — get execution request details
* `GET /admin/execution-requests` — list all execution requests (admin)
* `GET /admin/execution-requests/{id}` — get execution request details (admin)

### Output Sets

Outputs are governed as a collection (Output Set), not individually. The Output Set lifecycle is `PENDING_REVIEW → APPROVED → RELEASED`. Release creates a ZIP Release Package.

* `GET /projects/{project_id}/execution-requests/{id}/outputs` — get the released Output Set (researcher-facing, includes member file listing)
* `GET /projects/{project_id}/execution-requests/{id}/outputs/download` — download the Release Package ZIP (researcher-facing, only if RELEASED)
* `GET /admin/output-sets` — list all Output Sets (admin, all statuses)
* `GET /admin/output-sets/{id}` — get Output Set with member files (admin)
* `POST /admin/output-sets/{id}/approve` — approve (PENDING_REVIEW → APPROVED)
* `POST /admin/output-sets/{id}/reject` — reject (PENDING_REVIEW → REJECTED)
* `POST /admin/output-sets/{id}/release` — release (APPROVED → RELEASED), creates ZIP
* `GET /admin/execution-requests/{id}/outputs` — get Output Set for an execution (admin)
* `GET /admin/outputs/{id}` — inspect individual output artefact (admin)

### Analysis Bundles

* `POST /projects/{project_id}/bundles` — create a bundle within a project
* `POST /projects/{project_id}/bundles/upload` — upload and register a bundle ZIP archive
* `GET /projects/{project_id}/bundles` — list bundles in a project
* `GET /projects/{project_id}/bundles/{id}` — get bundle details (includes `ai_review` if AI assistance is configured)
* `PUT /projects/{project_id}/bundles/{id}` — update a bundle
* `POST /projects/{project_id}/bundles/{id}/ai-review` — trigger, retry, or refresh an AI analysis summary
* `GET /admin/bundles` — list all bundles (admin)
* `GET /admin/bundles/{id}` — get bundle details (admin)

### Execution Environments

* `GET /execution-environments` — list available execution environments (researcher-facing, active only)
* `GET /admin/execution-environments` — list all execution environments (admin)
* `GET /admin/execution-environments/{id}` — get execution environment details (admin)

### Execution Requests

* `POST /projects/{project_id}/execution-requests` — create an execution request within a project
* `GET /projects/{project_id}/execution-requests` — list execution requests in a project
* `GET /projects/{project_id}/execution-requests/{id}` — get execution request details
* `GET /admin/execution-requests` — list all execution requests (admin)
* `GET /admin/execution-requests/{id}` — get execution request details (admin)

### Data Resources

* `GET /admin/resources` — list all data resources (admin)
* `GET /admin/resources/{id}` — get data resource details (admin)

### Administration

* Pending bundles (for execution approval), Output Sets pending review (for output approval)
* User management
* Audit logs

⸻

## Job Lifecycle

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

Released

⸻

All endpoints should be RESTful.

Business logic belongs in services rather than controllers.

API endpoints should remain thin and primarily coordinate validation, authorization, and service calls.
