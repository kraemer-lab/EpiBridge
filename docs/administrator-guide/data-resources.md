# Data Resources

Managing institutional data resources in EpiBridge.

## What is a Data Resource?

A **Data Resource** represents an existing institutional data asset that has been registered for analysis. The institution owns and manages the underlying data files; EpiBridge provides a catalogue of available resources, access control, and secure execution.

EpiBridge does **not** own, store, or manage scientific data. It never copies data into its own storage. Instead, it describes where data lives, who may access it, and how to mount it securely into analysis containers.

This separation is fundamental: the platform manages **metadata and access control**, not the data itself.

## Runtime Access Contract

When a Data Resource is allocated to a project and used in an analysis execution, it is mounted inside the analysis container at a predictable location:

```
/data/{alias}
```

The `alias` is defined in the manifest at resource creation time and is **stable for the lifetime of the resource**. Changing the alias is a breaking change — any analysis code that references the old path will fail.

Analysis code always uses this path regardless of:
- the provider type (CSV, DuckDB, Parquet, etc.);
- the deployment model (OrbStack, native Docker);
- whether the execution is validation (representative data) or governed (production data).

```python
import pandas as pd
df = pd.read_csv("/data/demo-surveillance/demo.csv")
```

The alias and identifier often use the same value. This is the recommended convention. They may differ when an institution has a specific reason to separate the institutional label (`identifier`) from the runtime mount name (`alias`).

## How data resources work

### Environment-agnostic model

From the platform's perspective, a Data Resource is:

- A **manifest** that describes the resource in YAML: its identifier, name, provider type, endpoint configuration, and status.
- A **registration** process that loads manifests into the database on startup.
- A **publication** mechanism that makes resources discoverable to researchers through the catalogue.
- An **allocation** model that authorises projects to use specific resources.

These concepts are independent of deployment technology.

#### Manifests

Data Resources are defined in YAML manifests. The manifest describes the resource in deployment-agnostic terms:

```yaml
identifier: "uk-biobank-serum"
alias: "uk-biobank-serum"
name: "UK Biobank Serum Biomarker Data"
provider: "csv"
endpoint:
  path: "uk_biobank/serum.csv"
status: "active"
```

The `endpoint` describes *what* the resource is, not *where* it lives on disk. How paths resolve to physical storage is the deployment's responsibility.

The manifest directory (`RESOURCE_MANIFEST_DIR`) is scanned on every startup. The filesystem is the source of truth; the database is a runtime index. Registration is idempotent — new manifests create new records, updated manifests update existing records, and the database is reconciled automatically.

Each manifest may also include:
- **Documentation** — schemas, READMEs, and usage guidance for researchers
- **Representative datasets** — structurally identical subsets for operational validation (see [Validation in the Researcher Guide](../user-guides/researcher.md#validation))

#### Registration

Registration happens automatically at startup:

1. Load all manifests from the manifest directory.
2. Validate each manifest (required fields, provider type, endpoint shape).
3. If any manifest is invalid, startup **aborts** — an invalid manifest is a configuration error.
4. Atomically reconcile all valid manifests against the database:
   - New resources are created.
   - Existing resources are updated (name, alias, endpoint, version, status).
   - Resources removed from manifests are **not** deleted from the database (they retain their records for audit purposes).

#### Publication

Once registered, resources appear in the researcher-facing catalogue. Researchers can browse available resources, view schemas and documentation, and discover which resources are relevant to their work.

Resources may optionally have **Dataset Terms of Service** published against them. When dataset terms are published, researchers must accept them before attaching the resource to a project or submitting a bundle that references it.

#### Project allocation

Resources are attached to projects through **ProjectResourceAllocation** records. Each allocation captures:
- Who authorised it
- When it was created
- Which project and resource it connects

An allocation is active until explicitly revoked. Revocation records who and when, for audit purposes.

Allocation is an institutional provisioning decision — it says "this project is authorised to use this resource." It does not move or copy data.

### Environment-aware model

In an institutional deployment, the above concepts map to physical infrastructure.

#### Recommended: host-managed storage

The recommended deployment pattern keeps authoritative datasets **outside** the EpiBridge execution environment. Institutional storage is managed directly by the institution and mounted read-only into the platform.

```
Host filesystem
  └── /data/institutional/uk-biobank/serum.csv  (managed by IT)
        │
        ▼ (bind mount, read-only)
  Platform VM / container
  └── /read-only-data/uk-biobank/serum.csv
        │
        ▼ (provider resolution during execution)
  Analysis container
  └── /data/uk-biobank/serum.csv  (read-only)
```

**Why this is recommended:**

1. **Data never enters the platform's storage.** The platform does not copy, ingest, or transform the data. It only mounts the authorised subset into analysis containers.
2. **The VM is disposable.** If the VM is lost (crash, rebuild, migration), the data survives in its original location. Recovery requires only updating the mount path.
3. **Backup is the institution's responsibility.** Institutional backup policies apply directly to the authoritative storage. EpiBridge never needs to restore data — only its own metadata (which is backed up separately).
4. **Access control is layered.** The host filesystem permissions protect data at rest. EpiBridge adds project-scoped authorisation at runtime. Both must be satisfied.

#### Read-only mounts

Data resources are mounted **read-only** inside analysis containers. The analysis code can read data but cannot modify it. This is enforced at the container level by Docker bind mount permissions and at the executor level by the platform.

#### VM disposability

Because authoritative data lives outside the EpiBridge VM, the VM is fully disposable. You can:

- Destroy and recreate the VM without data loss.
- Migrate to a new VM by updating mount paths.
- Run multiple VM instances (staging, production) from the same data store.

The only state the VM owns is:
- PostgreSQL database (users, projects, bundles, audit events)
- Redis data (work queue — ephemeral)
- Uploaded bundle archives (can be re-uploaded)
- Release packages (archived outputs — should be backed up)

#### Backup implications

Because data lives outside EpiBridge:

- **Institutional data** is backed up by the institution's existing storage infrastructure. EpiBridge has no role in this.
- **Platform database** (users, projects, bundles, audit events) must be backed up via `backup.sh`. This is the only EpiBridge-owned state that cannot be recreated.
- **Release packages** (delivered outputs) should be archived to long-term storage outside the platform for compliance reasons.
- **Configuration** (`.env`) must be backed up separately as it contains secrets.

## Provider types

EpiBridge supports multiple data backends through a **Provider** abstraction. Each provider knows how to make a specific type of data available inside an analysis container:

| Provider | Data type | Use case |
|----------|-----------|----------|
| CSV | Single CSV file | Simple tabular data |
| DuckDB | DuckDB database file | Analytical queries |
| PostgreSQL | PostgreSQL database | Managed relational data |
| Excel | Excel workbook | Spreadsheet data |
| Parquet | Directory of Parquet files | Columnar storage |

The provider describes *what* to expose (source path, type) and *how* to expose it (mount points, environment variables). An Executor (Docker, Kubernetes, etc.) translates these into the corresponding infrastructure.

For the stable runtime path where resources appear inside analysis containers, see [Runtime Access Contract](#runtime-access-contract).

## See also

- [Execution Environments](execution-environments.md) — how resources are mounted during execution
- [Terms](terms.md) — dataset terms of service
- [Backup & Recovery](backup-and-recovery.md) — protecting platform state
- [Architecture](../architecture-and-reference/architecture.md) — data resource design and provider model
