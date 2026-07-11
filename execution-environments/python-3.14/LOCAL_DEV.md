## Local Development

Develop locally using the published execution environment.

### Pull the image

```sh
docker pull epibridge/python-3.14:latest
```

### Run a container

Mount your analysis code and data:

```sh
docker run --rm \
  -v $(pwd):/analysis \
  -v $(pwd)/data:/data:ro \
  epibridge/python-3.14:latest
```

### Run your entrypoint

The container does not automatically execute your script. Run it interactively:

```sh
docker run --rm -it \
  -v $(pwd):/analysis \
  -v $(pwd)/data:/data:ro \
  epibridge/python-3.14:latest \
  python /analysis/run.py
```

### Test with representative data

Download a representative dataset and place it in your local `data/` directory. The container mounts `data/` at `/data` (read-only), matching the production data path.

### Expected paths

| Path | Purpose | Access |
|------|---------|--------|
| `/analysis` | Bundle source code | Read-write |
| `/data` | Data resources | Read-only |
| `/output` | Analysis results | Read-write |
| `/work` | Scratch space | Read-write |
