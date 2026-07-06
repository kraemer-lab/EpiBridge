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

### Jobs

* Submit analysis
* View status
* View logs

### Outputs

* List outputs
* Download approved outputs

### Analysis Bundles

* `POST /projects/{project_id}/bundles` — create a bundle within a project
* `GET /projects/{project_id}/bundles` — list bundles in a project
* `GET /projects/{project_id}/bundles/{id}` — get bundle details
* `PUT /projects/{project_id}/bundles/{id}` — update a bundle
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

* Pending jobs
* Pending outputs
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
