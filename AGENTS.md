# AGENTS.md

## Project status — pre-MVP, no code yet

This repo has zero commits, zero config files, and zero application code.
Everything is still in the planning stage. The `docs/` directory contains architecture, API, and security documents that describe the intended design.

Do not assume any dependency, framework version, or tool is available. Nothing has been installed.

## Intended architecture (from docs/)

```
frontend/    Next.js + React + TypeScript
backend/     FastAPI + SQLAlchemy + Alembic + PostgreSQL
worker/      Python job executor
shared/      Shared schemas and types across packages
containers/  Base analysis Docker images
examples/    Synthetic datasets and analysis templates
docs/        Architecture, security, API, roadmap, vision
```

Single monorepo. Do not add top-level directories without justification.

## Foreseen conventions (documented, not yet enforced)

- Backend: FastAPI dependency injection, business logic in `services/`, thin endpoints, SQLAlchemy ORM, Pydantic models
- Frontend: App Router, TypeScript, server components where appropriate, functional components

## Security constraints (must preserve in implementation)

- Researchers never get direct dataset access
- All analysis executes through the Worker in isolated Docker containers
- Datasets mounted read-only in containers
- Two-stage approval: execution approval then output approval
- Never bypass the approval workflow
- Use `Storage` and `Executor` interfaces (not coupling directly to Docker)
- Firebase Auth for auth, internal PostgreSQL for authorisation
- Audit trail required for all actions

## No developer commands exist yet

There are no `package.json`, `pyproject.toml`, `requirements.txt`, `Makefile`, Dockerfiles, or CI workflows. Commands for test, lint, format, typecheck, codegen, dev servers, and migrations will all need to be created.

Stand up each package independently before wiring integration tests.
