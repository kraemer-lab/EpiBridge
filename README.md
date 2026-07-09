# EpiBridge
[![EpiBridge](https://github.com/kraemer-lab/EpiBridge/actions/workflows/EpiBridge.yml/badge.svg)](https://github.com/kraemer-lab/EpiBridge/actions/workflows/EpiBridge.yml)

Secure remote analysis for sensitive epidemiological data.

EpiBridge is a platform that allows researchers to analyse sensitive datasets without the data ever leaving the host institution.

Researchers develop analyses locally using schema documentation and synthetic datasets, submit analysis bundles to EpiBridge, and receive approved outputs after execution within a secure environment.

## Core Principle

Move the computation to the data, not the data to the computation.

## Features

* Secure user authentication
* Project-based access control
* Analysis job submission
* Human approval before execution
* Isolated container execution
* Human approval before output release
* Complete audit trail
* Cloud-ready architecture

## Technology

* Frontend: Next.js + React + TypeScript
* Backend: FastAPI
* Database: PostgreSQL
* Queue: Redis
* Worker: Python
* Execution: Docker
* Authentication: Local Identity Provider (Argon2, server-side sessions)

## Repository Structure

```
frontend/
backend/
worker/
vm/
scripts/
docs/
```

## Development

See `vm/runtime.md` for the development quickstart.

The only host dependencies are Git and a VM runtime (OrbStack, Multipass, etc.).

No Python, Node.js, or PostgreSQL is ever installed on the host.

```bash
make dev
```

## Documentation

See the `docs/` directory for:

* Architecture
* Security
* API
* Vision

# Status

Current stage: MVP release.
