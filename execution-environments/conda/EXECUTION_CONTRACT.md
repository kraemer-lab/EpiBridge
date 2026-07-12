## Execution Contract

Analysis runs in a protected container with the following guarantees.

### Filesystem

| Path | Purpose | Permissions |
|------|---------|-------------|
| `/analysis` | Bundle source code | Read-write |
| `/data` | Data resources | Read-only |
| `/output` | Analysis results | Read-write |
| `/work` | Scratch workspace | Read-write |

### Output convention

Analysis scripts should write results to `/output`. All files in `/output` after execution are collected as candidate output files. Expected output files may be declared in the bundle manifest.

### Network access

Internet access is not available during institutional execution. All data resources are mounted from the platform.

### Build process

The execution environment builder creates a conda environment from the `environment.yml` file provided in the Analysis Bundle. The analysis runs within the created environment.
