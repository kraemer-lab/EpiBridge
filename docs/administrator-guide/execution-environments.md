# Execution Environments

Managing execution environments in EpiBridge.

## What is an Execution Environment?

An **Execution Environment** is an institutional asset that represents an approved runtime for analysis execution. Execution environments define the **institutional execution contract** — a guarantee about the runtime, filesystem layout, and security context that every analysis can rely on.

Researchers select from the curated catalogue of available environments when creating an analysis bundle. They do not specify arbitrary runtime strings; the institution controls which runtimes are available.

An execution environment is more than a language runtime. It represents an institutional commitment that analyses targeting that environment will execute correctly, securely, and consistently.

## The execution contract

Every execution environment guarantees the following runtime contract inside an analysis container:

| Path / property | Purpose |
|-----------------|---------|
| `/analysis` | Bundle injection target — analysis code is placed here |
| `/data` | Resource mount namespace — authorised data appears at `/data/{alias}` |
| `/output` | Writable results directory — analysis outputs go here |
| `/work` | Temporary scratch space |
| `nobody` user | Least-privilege execution identity |

This contract is validated by **Execution Environment Acceptance Tests** — automated tests that verify a published environment can install declared dependencies, build a runnable execution image, and produce expected outputs under governed conditions. Each environment must pass its acceptance test before it can be considered production-ready.

For details of how data resources are mapped to mount paths inside containers, see the [Data Resources guide](data-resources.md#runtime-access-contract).

## Currently supported environments

| Name | Runtime | Base image |
|------|---------|------------|
| Python 3.13 | `python-3.13` | `python:3.13-slim` with NumPy, Pandas |
| Python 3.14 | `python-3.14` | `python:3.14-slim` with NumPy, Pandas |
| Conda | `conda` | `mambaorg/micromamba:2.8.1` |

## Registration

Execution environments are defined by YAML manifests and supporting artefacts in the `execution-environments/` directory:

```
execution-environments/
├── python-3.13/
│   ├── Dockerfile           # Base image definition
│   ├── manifest.yaml        # Registration manifest (name, runtime, image reference)
│   └── ...
├── python-3.14/
│   └── ...
└── conda/
    └── ...
```

Registration follows the same pattern as data resources — the filesystem is the source of truth, the database is a runtime index. Registration is idempotent and happens automatically at startup.

## Researcher discovery

Researchers discover execution environments through the application UI:
- **List page** — all active environments with runtime, description, and image reference
- **Detail page** — full environment details including the curated Dockerfile, local development commands, and published artefact downloads
- **During bundle creation** — environment selector with display names and linked detail pages

Each environment detail page provides concrete local development guidance:

```
docker pull {image_reference}
docker run --rm -it {image_reference} /bin/bash
```

This enables researchers to prepare their analysis locally against the institutional runtime before uploading a bundle.

## Adding a new environment

To add a new execution environment:

1. Create a directory under `execution-environments/` with an identifier name.
2. Add a `Dockerfile` that provides the base image.
3. Add a `manifest.yaml` with the registration metadata.
4. Add an execution environment acceptance test under `frontend/e2e/execution-environment-acceptance/`.
5. Restart the platform — registration happens automatically on startup.

The new environment appears in the catalogue immediately. Existing analyses are unaffected — they continue to reference their selected environment by identifier.

## See also

- [Data Resources](data-resources.md) — how data is mounted during execution
- [Architecture](../architecture-and-reference/architecture.md) — environment builder and execution model
- [Testing](../architecture-and-reference/testing.md) — acceptance test framework
