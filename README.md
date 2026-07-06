# EpiBridge

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
* Authentication: Firebase Authentication

## Repository Structure

frontend/
backend/
worker/
shared/
containers/
examples/
docs/

## Deployment

Initially, EpiBridge is designed to run inside a single Linux virtual machine using Docker Compose.

Future versions will support Kubernetes deployments without significant architectural changes.

## Documentation

See the docs/ directory for:

* Architecture
* Security
* API
* Deployment
* Roadmap
* Vision

# Status

Current stage: MVP development.
