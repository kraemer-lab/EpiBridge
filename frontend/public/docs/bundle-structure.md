## Bundle Structure

An Analysis Bundle is a ZIP archive containing your analysis code, optional dependency specifications, and (for Custom Build) a Dockerfile.

### Minimal Structure

```
run.py              # Entrypoint script (required)
requirements.txt    # Python dependencies (optional)
```

### Advanced Structure

```
run.py              # Entrypoint script
requirements.txt    # Python dependencies
environment.yml     # Conda environment definition (conda runtime only)
data/               # Local test data (not included in upload)
output/             # Local test output (not included in upload)
```

### Custom Build

If your bundle uses the **Custom Build** strategy, include a `Dockerfile` at the root
of the ZIP. The Dockerfile receives `ARG BASE_IMAGE` (the selected execution environment's
image reference) and extends the institutional environment. Custom Build requires the
`build.customize` capability.

### Entrypoint

The entrypoint is the script that the platform executes. It must be:

- A single file at the top level of the ZIP archive.
- One of: `.py` (Python), `.r` (R), `.sh` (Shell).

The script runs inside the chosen [Execution Environment](/environments).

### File System Contract

| Path | Purpose | Access |
|------|---------|--------|
| `/analysis` | Bundle source code | Read-write |
| `/data` | Data resources | Read-only |
| `/output` | Analysis results | Read-write |
| `/work` | Scratch workspace | Read-write |

Your script should write results to `/output`. All files in `/output` after execution are collected as candidate output files.

### Dependencies

- For the **Python** runtime: include a `requirements.txt` in your bundle.
- For the **Conda** runtime: include an `environment.yml` in your bundle.
- Pre-installed packages are listed in the [Software](/environments/python-3.14#software) tab for each environment.

### Examples

See published [Example Analyses](/examples) for complete working examples.
