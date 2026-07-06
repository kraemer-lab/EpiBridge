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
/var/lib/epibridge/datasets # sensitive dataset mounts
/var/log/epibridge          # audit and application logs
```

## Host Dependencies

Only these must be installed on the host:

- Docker Engine
- Docker Compose plugin
- Git
- curl

Everything else runs in containers. The host never runs Python, Node.js, or PostgreSQL directly.

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

If an analysis container is compromised, the attacker remains inside the VM, not the host infrastructure.

## Development Environment

The development environment is identical to production: an Ubuntu VM running Docker Engine.

The only host dependencies are:

- Git
- A VM runtime (OrbStack, Multipass, Lima, VMware, etc.)

No Python, Node.js, or PostgreSQL is ever installed on the host.

### Quickstart (OrbStack)

From the repo root:

```bash
make dev
```

This creates the OrbStack VM (if needed), mounts the repo into `/opt/epibridge`, builds Docker images, starts all services, runs database migrations, seeds the admin account, and verifies health.

First run takes ~3 minutes. Subsequent runs are near-instant.

### Individual steps

For debugging or CI:

```bash
make dev-install    # install with --dev flag (skips git operations)
make dev-up         # start all services
make dev-down       # stop all services
make dev-shell      # interactive VM shell
make dev-logs       # tail all container logs
```

### Other VM providers

The same Makefile supports production VMs and other hypervisors via SSH:

```bash
make install SSH="ssh -i key.pem ubuntu@192.168.1.100"
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
make install SSH="ssh ubuntu@epibridge-dev.local"
```

### Manual (VMware, KVM, Proxmox, etc.)

```bash
# 1. Create VM with cloud-init (provider-specific)
# 2. Copy the repository
rsync -avz --exclude .git . epibridge@vm-ip:/opt/epibridge
# 3. Install
make install SSH="ssh epibridge@vm-ip"
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
