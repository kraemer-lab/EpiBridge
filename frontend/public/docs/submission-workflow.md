## Submission Workflow

The submission workflow ensures every analysis is reviewed before execution and every output is reviewed before release.

### Step 1 — Create a Project

Create a Project from the [Projects](/projects) page. This is your team's collaborative workspace.

### Step 2 — Attach Data Resources

Attach the [Data Resources](/resources) you need for your analysis.

Dataset [Terms of Service](/terms) must be accepted before attaching.

### Step 3 — Create a Draft Bundle

Create a new Draft Bundle from the Project's Analysis tab.

Configure:

- [Execution Environment](/environments)
- Entrypoint script
- Referenced Data Resources
- Build strategy

### Step 4 — Upload Your Code

Upload your Analysis Bundle ZIP. You can also manage individual files within the workspace.

### Step 5 — Submit for Review

Submit your draft. A reviewer with the appropriate capability will review your bundle.

The reviewer may:

- **Approve** the bundle for execution.
- **Reject** the bundle with feedback.
- **Supersede** an approved bundle (replacing it with an updated version).

### Step 6 — Request Execution

An authorised user requests execution of the approved bundle.

### Step 7 — Execution

The Worker builds the execution image and runs your analysis in an isolated container with:

- No network access
- Read-only data mounts
- Resource limits (CPU, memory, PIDs)

### Step 8 — Output Review

Execution outputs are collected into an Output Set. A reviewer approves or rejects the outputs.

### Step 9 — Release and Download

Approved outputs are released. You can download a release package containing your results and execution metadata.

### Audit Trail

Every governance action is recorded in the [Audit Log](/admin/audit) for institutional accountability.
