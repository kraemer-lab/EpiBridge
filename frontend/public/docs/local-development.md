## Local Development

You can develop and test Analysis Bundles locally using the published execution environment images.

### Prerequisites

- Docker installed on your machine

### Pull the Environment Image

```sh
docker pull epibridge/python-3.14:latest
```

### Prepare Your Workspace

```
my-analysis/
    run.py
    requirements.txt
    data/               # Representative data (download from Data Resource)
    output/             # Local output directory
```

### Run Your Analysis

```sh
docker run --rm -it \
  -v $(pwd):/analysis \
  -v $(pwd)/data:/data:ro \
  -v $(pwd)/output:/output \
  epibridge/python-3.14:latest \
  python /analysis/run.py
```

### Test with Representative Data

Each [Data Resource](/resources) may publish a **Representative Dataset** — a small sample suitable for local development. Download it from the resource detail page and place it in your `data/` directory.

### Expected Paths

The container follows the same path conventions as institutional execution:

| Path | Purpose | Access |
|------|---------|--------|
| `/analysis` | Bundle source code | Read-write |
| `/data` | Data resources | Read-only |
| `/output` | Analysis results | Read-write |
| `/work` | Scratch space | Read-write |

### Environment-Specific Guidance

Each [Execution Environment](/environments) has a **Local Development** tab with environment-specific instructions.
