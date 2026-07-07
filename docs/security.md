# Security Model

## Trust Boundary

Each institution deploys EpiBridge inside a restricted Linux virtual machine.

The VM contains:

* frontend
* backend
* database
* worker
* audit logs
* Docker Engine
* local datasets

Sensitive data never leaves this environment except through approved outputs.

⸻

## Execution

Each submitted analysis executes inside an ephemeral Docker container.

Containers should:

* run as non-root
* have no external network access
* use read-only dataset mounts
* use temporary writable storage
* enforce CPU and memory limits
* enforce execution timeouts
* be destroyed after completion

⸻

## Authentication

Authentication uses the IdentityProvider abstraction (LocalIdentityProvider with Argon2 password hashing).

Sessions are managed server-side with HTTP-only cookies and stored in PostgreSQL.

Application permissions are stored locally.

⸻

## Authorisation

Role-based access control.

Typical roles include:

* Researcher
* Project Administrator
* Data Steward
* System Administrator

⸻

## Approval Workflow

Execution approval

Researcher

↓

Submit Job

↓

Administrator Approves

↓

Execution

Output approval

Execution

↓

Outputs Generated

↓

Administrator Reviews

↓

Approved Download

⸻

## Audit

All actions should be recorded.

Examples include:

* login
* job submission
* approvals
* execution
* downloads

Audit records should be immutable.
