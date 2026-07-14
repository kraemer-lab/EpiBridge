# Local Development

Setting up a local development environment for contributing to EpiBridge.

## Development workflow

After installation, the standard edit–build–run cycle is:

```bash
make dev
```

This rebuilds and restarts application services without reseeding users or institutional state. It is faster than re-installing and preserves your working data.

## Iteration speed

For faster iteration on a single service:

```bash
make dev-build SVC=frontend   # rebuild and restart the frontend only
make dev-build SVC=backend    # rebuild and restart the backend only
```

The stack runs in an OrbStack VM. Logs are available via:

```bash
make dev-logs                 # tail all container logs
```

## Code quality

| Command | What it does |
|---------|--------------|
| `make format` | Auto-format code (ruff for Python, prettier for TypeScript) |
| `make lint` | Static analysis (ruff check) |
| `make fix` | Auto-fix all fixable lint issues |

## Testing

| Command | What it runs |
|---------|--------------|
| `make test` | Unit + integration + smoke tests (requires local PostgreSQL + Redis) |
| `make playwright` | e2e institutional acceptance test (requires full stack) |
| `python -m pytest backend/tests/unit -v` | Unit tests only (no database) |
| `python -m pytest backend/tests/integration -v` | Integration tests (requires test database) |

For testing inside the running stack:

```bash
make dev-test                 # run all tests inside the container
```

See [Testing](../architecture-and-reference/testing.md) for the full testing reference.

## Backend development

From `backend/`:

```bash
pip install -e ".[dev]"       # install dev dependencies
alembic upgrade head           # apply pending migrations
alembic revision --autogenerate -m "description"  # create a new migration
```

The backend runs with hot reload during development. Changes to Python files are picked up automatically.

## Database changes

The SQLAlchemy models are the source of truth for the schema. When you modify a model:

1. Generate a migration: `alembic revision --autogenerate -m "description"`
2. Review the generated file in `alembic/versions/`
3. Apply: `alembic upgrade head`
4. Verify with tests

During active development, the migration chain is periodically squashed to prevent unbounded growth. See AGENTS.md for the current policy.

## VM runtime reference

For details on the OrbStack development environment (filesystem mounts, networking, troubleshooting), see `vm/runtime.md` in the repository root.

## Next steps

- [Architecture](../architecture-and-reference/architecture.md) — system design
- [Testing](../architecture-and-reference/testing.md) — testing strategy and runner reference
- [API Reference](../architecture-and-reference/api.md) — REST API endpoints
