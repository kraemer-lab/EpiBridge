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
