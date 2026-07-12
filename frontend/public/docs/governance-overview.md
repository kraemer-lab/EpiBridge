## Governance Overview

EpiBridge enforces institutional governance through capability-based access control, approval workflows, and a complete audit trail.

### Capability-Based Access

Every action in the platform requires a specific capability:

| Capability | Purpose |
|---|---|
| `bundle.create` | Create and edit Analysis Bundles |
| `bundle.submit` | Submit bundles for review |
| `bundle.review` | Approve or reject submitted bundles |
| `execution.run` | Request execution of approved bundles |
| `output.review` | Approve or reject output sets |
| `output.release` | Release approved outputs |

Researchers typically have `bundle.create` and `bundle.submit`.

### Two-Stage Approval

All analyses pass through two independent approval stages:

1. **Bundle Approval** — A reviewer checks the analysis code before it can run.
2. **Output Approval** — A reviewer checks the results before they can be released.

This ensures no code executes and no data leaves without human oversight.

### Terms of Service

The institution publishes:

- **Platform Terms** — governing overall platform access.
- **Dataset Terms** — governing use of specific data resources.

You must accept the latest version of each before use.

### Audit Trail

Every governance action generates an audit event. Events are:

- Immutable and append-only
- Attributable to the authenticated user
- Project-scoped for privacy
- Visible in the Audit Log

### Institutional Publications

The institution publishes:

- [Execution Environments](/environments) — approved runtimes
- [Data Resources](/resources) — curated datasets
- [Example Analyses](/examples) — educational analysis code
- [Bundle Templates](/templates) — downloadable starting points

These publications are authoritative and maintained by the institution.
