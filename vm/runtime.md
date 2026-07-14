# EpiBridge Runtime Specification

## Version

**EpiBridge Runtime**

## Target Operating System

- Ubuntu Server 24.04 LTS

## Container Runtime

- Docker Engine (CE)
- Docker Compose (plugin)

## Minimum Hardware

| Resource | Minimum |
|----------|---------|
| vCPUs    | 4       |
| RAM      | 8 GB    |
| Storage  | 100 GB  |

## Filesystem Layout

```
/opt/epibridge              # application repository
/var/lib/epibridge/data     # persistent database volume
/var/lib/epibridge/outputs  # job output storage
/var/log/epibridge          # audit and application logs
```

The deployment also places institutional data resources at a location of its
choosing. EpiBridge accesses them through the runtime contract (see below)
and never knows the physical host path.

## Host Dependencies

Only these must be installed on the host:

- Docker Engine
- Docker Compose plugin
- Git
- curl

Everything else runs in containers. The host never runs Python, Node.js, or PostgreSQL directly.

## Three Environments

The system consists of three distinct environments, each with a different view of the data.

```
Host
  └── Trusted Runtime (VM)
        └── Analysis Container
```

### Host

The host owns the physical data — for example, `/srv/data/`. EpiBridge never
knows host paths. The host is outside the trust boundary.

### Trusted Runtime

The deployment environment guarantees that institutional data resources are
available beneath a well-known location:

```
/read-only-data
```

This is the **runtime contract**. How resources arrive there (host directory
mount, NFS share, cloud storage, database connection, etc.) is entirely the
responsibility of the deployment — never EpiBridge.

EpiBridge only understands:

- **Data Resources** — registered metadata about an available asset
- **Resource Providers** — abstractions that validate endpoints and describe
  runtime requirements
- **Runtime Endpoints** — provider-specific configuration
  (e.g. `{"path": "study123/data.csv"}`)

The `ResourceProvider` translates endpoint configuration into platform-agnostic
mount and environment requirements (`RuntimeConfig`). The provider returns the
source path but never decides the target inside the analysis container.

### Analysis Container

The analysis container never receives access to the runtime's complete
`/read-only-data`. It receives a minimal execution view containing only the
resources authorised for that job.

The standard container contract:

| Path      | Purpose                              |
|-----------|--------------------------------------|
| `/work`   | Writable temporary storage           |
| `/data`   | Namespace of authorised resources    |
| `/output` | Writable directory for results       |

#### `/data` — authorised resource namespace

Each authorised resource appears beneath `/data/` at a path determined by its
**runtime alias**:

```
/data
  /{alias_1}
  /{alias_2}
```

The runtime alias is a filesystem-safe identifier. It may be a slugified
version of the display name or a dedicated alias field (future). The analysis
always refers to the alias, never the display name, so display names can be
improved without breaking analyses.

Examples:

```
/data
  /demo-surveillance
  /weather
```

If a resource resolves to a single file, it appears directly:

```
/data/dataset.csv
```

If a resource resolves to a directory, all files within are available:

```
/data/weather/2024/temperature.csv
/data/weather/2025/temperature.csv
```

#### `/work`

Writable temporary working directory for the analysis. Empty at container
start. The analysis may use this for intermediate files, extracted archives,
or any other scratch data. Discarded after the container is destroyed.

#### `/output`

The analysis writes its results here. After the container exits, the Executor
collects the contents and registers them as job outputs.

### Security boundary

The most important security property:

> The analysis container must never receive access to `/read-only-data`.

The Executor is responsible for mounting only the authorised subset.

This means:
- `/data` contains only what the job is authorised to access
- The analysis cannot enumerate available resources
- Compromised analysis code cannot exfiltrate unauthorised data

This is a fundamental security boundary enforced by the execution environment.

### Development

In development, `docker-compose.yml` mounts `./resources/` at
`/read-only-data`. This exercises the exact same provider abstraction used in
production.

### Production

In production, the system administrator ensures the institution's data
resources are placed at `/read-only-data` or otherwise reachable through the
configured provider endpoints.

## Standard Ports

| Port | Service       |
|------|---------------|
| 22   | SSH           |
| 80   | HTTP          |
| 443  | HTTPS         |

All application traffic goes through the reverse proxy on ports 80/443. Internal services are not exposed.

## Infrastructure vs Application

Two separate phases:

### 1. Infrastructure — `cloud-init.yaml`

Prepares the OS only:

- installs Docker Engine, Compose, Git, curl
- creates the `epibridge` user
- configures UFW firewall
- creates standard directories
- enables unattended security updates

Never clones repositories, builds images, or runs application code.

### 2. Application — `install.sh`

Assumes infrastructure phase has completed (directories exist,
ownership correct).

Owns the application lifecycle:

- clones or updates the repository
- generates `.env` with secrets
- builds or pulls Docker images
- starts Docker Compose
- runs database migrations
- seeds the administrator account
- runs health checks

## Security Boundaries

```
Host OS
  └── Virtual Machine         ← Layer 1 (trust boundary)
        └── Docker Engine
              ├── Platform Containers    ← Layer 2
              └── Ephemeral Analysis
                  Containers             ← Layer 3
```

### Layer isolation

If an analysis container is compromised, the attacker remains inside the VM,
not the host infrastructure.

### Data access isolation

Platform containers (backend, worker) see the full `/read-only-data`. This is
necessary for orchestration — they need to know what resources exist.

Analysis containers see only `/data`, which contains exclusively the resources
authorised for that job. The Executor enforces this by mounting only the
relevant subset of `/read-only-data` into the container as `/data/{alias}`.

The analysis container has no access to the runtime's full resource pool.

## Development Environment

The development environment is identical to production: an Ubuntu VM running Docker Engine.

The only host dependencies are:

- Git
- A VM runtime (OrbStack, Multipass, Lima, VMware, etc.)

No Python, Node.js, or PostgreSQL is ever installed on the host.

### Quickstart (OrbStack)

From the repo root:

```bash
make install
```

This creates the OrbStack VM (if needed), mounts the repo into `/opt/epibridge`, builds Docker images, starts all services, seeds the admin account and platform terms, and verifies health.

First run takes ~3 minutes. Subsequent runs are near-instant.

After installation, `make dev` is the normal edit–build–run workflow for contributors.

### Individual steps

For debugging or CI:

```bash
make install        # full installation (idempotent)
make dev            # rebuild and restart application services
make dev-up         # start all services
make dev-down       # stop all services
make dev-shell      # interactive VM shell
make dev-logs       # tail all container logs
```

### Testing

```bash
make test           # Run tests on the host (unit + integration + smoke)
make dev-test       # Run full suite inside the container (requires dev stack)
```

Unit tests work anywhere. Integration tests require running services. Smoke tests auto-skip if the full stack isn't available.

### Other VM providers

The same Makefile supports production VMs and other hypervisors via SSH:

```bash
make deploy SSH="ssh -i key.pem ubuntu@192.168.1.100"
make up    SSH="ssh -i key.pem ubuntu@192.168.1.100"
make down  SSH="ssh -i key.pem ubuntu@192.168.1.100"
```

Provider-specific setup examples:

| Runtime    | Create VM                          | Mount repo              |
|------------|------------------------------------|--------------------------|
| Multipass  | `multipass launch --cloud-init vm/cloud-init.yaml 24.04 --name epibridge-dev` | `multipass mount . epibridge-dev:/opt/epibridge` |
| Lima       | `limactl start --name=epibridge vm/cloud-init.yaml` | `limactl mount epibridge .` |
| Manual KVM | `virt-install --initrd-inject vm/cloud-init.yaml ...` | 9p/virtiofs mount |
| AWS EC2    | cloud-init from user-data          | `rsync -avz --exclude .git . epibridge@ip:/opt/epibridge` |

### Multipass

```bash
multipass launch --cloud-init vm/cloud-init.yaml 24.04 --name epibridge-dev
multipass mount . epibridge-dev:/opt/epibridge
make deploy SSH="ssh ubuntu@epibridge-dev.local"
```

### Manual (VMware, KVM, Proxmox, etc.)

```bash
# 1. Create VM with cloud-init (provider-specific)
# 2. Copy the repository
rsync -avz --exclude .git . epibridge@vm-ip:/opt/epibridge
# 3. Install
make deploy SSH="ssh epibridge@vm-ip"
```

## Deployment Targets

The same runtime specification applies to all targets:

- OrbStack (development)
- VMware / Hyper-V / KVM
- Proxmox
- OpenStack
- AWS EC2
- Azure VM
- Google Compute Engine

## Future Distribution Formats

All produced from this runtime specification:

- VMware OVA
- AWS AMI
- Azure Image
- OpenStack Image
- QCOW2 appliance

## Related Scripts

| Script                  | Purpose                         |
|-------------------------|---------------------------------|
| `vm/cloud-init.yaml`    | OS provisioning (infra)         |
| `scripts/install.sh`    | First-time application install  |
| `scripts/upgrade.sh`    | Application upgrade             |
| `scripts/backup.sh`     | Database and data backup        |
| `scripts/restore.sh`    | Restore from backup             |
| `scripts/healthcheck.sh`| Service health check            |
| `scripts/orbstack.sh`   | OrbStack dev helpers (optional) |
