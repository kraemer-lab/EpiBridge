## Local Development

Develop locally using the published execution environment.

### Pull the image

```sh
docker pull epibridge/conda:latest
```

### Run a container

Mount your analysis code and data:

```sh
docker run --rm \
  -v $(pwd):/analysis \
  -v $(pwd)/data:/data:ro \
  epibridge/conda:latest
```

### Run your entrypoint

```sh
docker run --rm -it \
  -v $(pwd):/analysis \
  -v $(pwd)/data:/data:ro \
  epibridge/conda:latest \
  python /analysis/run.py
```

The entrypoint and interpreter selected in the bundle determine how the script is executed. For conda environments, the entrypoint runs inside the created conda environment.

### Test with representative data

Download a representative dataset and place it in your local `data/` directory. The container mounts `data/` at `/data` (read-only), matching the production data path.

### Run without Docker

Install micromamba on your development machine:

```sh
curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba
export PATH="$PWD/bin:$PATH"

# Create environment from your Analysis Bundle
micromamba create -f /path/to/analysis/environment.yml
micromamba run -n analysis python /path/to/analysis/run.py
```

### Expected paths

| Path | Purpose | Access |
|------|---------|--------|
| `/analysis` | Bundle source code | Read-write |
| `/data` | Data resources | Read-only |
| `/output` | Analysis results | Read-write |
| `/work` | Scratch space | Read-write |
