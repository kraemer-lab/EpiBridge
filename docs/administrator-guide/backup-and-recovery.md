# Backup & Recovery

Backing up and restoring EpiBridge institutional state.

## What constitutes an EpiBridge installation

An EpiBridge installation consists of several categories of state, each with different backup requirements:

| Category | Example | Can be recreated? | Must be backed up? |
|----------|---------|-------------------|--------------------|
| Source code | Repository contents | Yes — from Git | No |
| Configuration | `.env` | Partially — secrets are unique | **Yes** |
| Database | Users, projects, bundles, audit events | No | **Yes** |
| Release packages | Delivered output ZIPs | Possibly — from source + data | **Yes** (compliance) |
| Bundle archives | Uploaded analysis files | Yes — re-uploaded by researchers | Optional |
| Execution images | Cached build artefacts | Yes — rebuilt on demand | No |
| Host data resources | Institutional datasets | N/A — managed by institution | Handled separately |
| Platform binary state | Redis queue, Docker build cache | Yes — ephemeral | No |

The overall message is:

> The execution environment is disposable. Institutional state is not.

## What must be backed up

### 1. Configuration (`.env`)

The `.env` file contains secrets (database passwords, signing key, SMTP credentials) that are generated during installation. If lost, these cannot be recovered.

**Backup**: Copy `.env` to a secure location outside the installation.

```bash
cp .env /backup/epibridge/env/$(date +%Y%m%d).env
```

**Restore**: Place the backed-up `.env` in the repository root before re-installing.

### 2. Database (PostgreSQL)

The database is the authoritative store for:
- User accounts and capabilities
- Projects and project membership
- Analysis bundles and their metadata
- Execution requests and validation requests
- Output sets and release package metadata
- Audit events
- Terms of service and acceptance records

This data **cannot be recreated** from any other source.

**Backup**:

```bash
./scripts/backup.sh
```

This creates a compressed archive containing:
- A full PostgreSQL dump (`pg_dump`)
- Application data files
- Timestamped for recovery point identification

**Restore**:

```bash
./scripts/restore.sh /path/to/backup/file
```

The restore script:
1. Stops the EpiBridge services to prevent data modification during restore.
2. Restores the PostgreSQL database from the dump.
3. Restores application data files.
4. Verifies the restored state.
5. Restarts services.

### 3. Release packages (compliance)

Release packages are the delivered research outputs. They should be archived to long-term storage outside the platform for compliance and reproducibility.

These are stored at `/var/lib/epibridge/releases/` inside the platform. Copy them to an external archive:

```bash
# From the host, if volumes are mapped
cp -r /path/to/releases/ /archive/epibridge-outputs/$(date +%Y%m%d)/
```

## What can be recreated

### Source code

The repository is cloned from Git. Re-installing pulls the latest version.

### Bundle archives

Uploaded analysis files can be re-uploaded by researchers. If the platform is restored from backup, the bundles are restored as part of the database — but the actual uploaded archive files (stored in the bundle store) must be backed up if researchers cannot re-upload them.

### Execution images

Cached Docker images are rebuilt automatically on demand. They are a performance optimisation, not authoritative state.

## Restoring onto a new installation

To restore EpiBridge onto a new server:

1. Set up a new installation following the [Deployment Guide](deployment.md). Do not start the platform yet.
2. Place the backed-up `.env` into the repository root.
3. Configure institutional data resource mounts (see [Data Resources](data-resources.md)).
4. Run the restore script with the database backup.
5. Verify: log in as the administrator, check that projects and users are present, confirm audit events are intact.

The new installation must use the same `SECRET_KEY` from the backed-up `.env` so that existing sessions can be validated (sessions will expire naturally within their TTL).

## Host-managed resources

Institutional data resources live **outside** EpiBridge (see [Data Resources](data-resources.md)). They are backed up through the institution's existing storage infrastructure. EpiBridge's backup script does not include them.

When restoring onto a new installation, ensure the host-managed data directories are mounted at the same paths expected by the deployment configuration.

## Recovery checklist

After any recovery operation:

- [ ] Administrator can log in
- [ ] All expected users are present
- [ ] Projects and their memberships are intact
- [ ] Analysis bundles are visible with correct status
- [ ] Audit events are present and correctly attributed
- [ ] Release packages are accessible for download
- [ ] Terms of service records are present
- [ ] Data resources are registered and active
- [ ] Execution environments are registered

## Next steps

- [Deployment](deployment.md) — production setup
- [Configuration](configuration.md) — environment settings
- [Data Resources](data-resources.md) — understanding the data boundary
