# AI-Assisted Analysis Summaries

EpiBridge can optionally use a local AI model to generate a natural-language
summary of uploaded Analysis Bundles. This feature helps researchers understand
what an uploaded analysis appears to do before executing it.

## Design principles

* **Optional** — AI assistance is disabled by default and must be explicitly
  enabled by an administrator.
* **Non-blocking** — The review runs as a background task immediately after
  upload. The researcher does not wait for it.
* **Advisory only** — The AI summary is metadata attached to an Analysis
  Bundle. Execution never depends on the review succeeding.
* **Cached per bundle** — The review is generated once per uploaded bundle and
  reused until explicitly refreshed.
* **Extensible** — The provider abstraction allows future AI backends without
  changing application code.

## Status

AI assistance is disabled by default (`AI_ASSIST_ENABLED=false`). The platform
behaves identically to how it does today. No AI services are started, no models
are downloaded, and no background tasks are created.

## How to enable

### 1. Start the optional AI service

The Ollama service runs behind a Docker Compose profile. Start it on an
already-running stack:

```bash
make dev-ai
```

This is additive — no containers are rebuilt or reprovisioned. The existing
bootstrap is completely unchanged.

### 2. Enable AI in configuration

Inside the deployment VM, edit the `.env` file:

```bash
./scripts/orbstack.sh ssh 'vim /opt/epibridge/.env'
```

Set:

```
AI_ASSIST_ENABLED=true
```

Restart the backend to reload the configuration:

```bash
./scripts/orbstack.sh ssh 'cd /opt/epibridge && docker compose restart backend'
```

### 3. Install a model

Model installation is an explicit administrator action. Models persist in a
Docker volume and survive container restarts.

```bash
./scripts/orbstack.sh ssh 'cd /opt/epibridge && docker compose exec ollama ollama pull llama3.2'
```

Supported models include any model available in the
[Ollama library](https://ollama.com/library). The model is configured via the
`OLLAMA_MODEL` environment variable (default: `llama3.2`).

## Behaviour when AI is unavailable

The platform continues to function normally in all scenarios:

| Scenario | Frontend display | Effect on execution |
|---|---|---|
| AI not enabled (`AI_ASSIST_ENABLED=false`) | "Not available for this deployment" | None |
| Ollama service not running | Review status shows "Unavailable" | None |
| Model not installed | Review status shows "Unavailable" | None |
| Review in progress | Review status shows "Pending" | None |
| Review completed | Summary, assessment, assessment confidence, reviewer notes shown | None |
| Review failed | Review status shows "Unavailable" | None |

## User interface

The AI Analysis Summary appears as a card on the Analysis Bundle detail page,
below the metadata. The "Run Analysis" button remains the primary action on
the page.

### Actions

| Bundle state | Available action |
|---|---|
| No review exists | "Generate AI Summary" |
| Review exists (any status) | "Refresh AI Summary" |
| Review is pending | No action (auto-refresh in progress) |

Clicking any of these buttons queues a new background review of the currently
stored bundle. No re-upload is required.

The detail page auto-refreshes while a review is pending. Once a terminal
state is reached (completed, failed, unavailable), polling stops permanently.
The only way to trigger another review is by explicitly clicking the button.

## CI

CI runs without the AI profile. No AI services are started, no models are
installed, and all tests pass without any AI dependency. The canonical workflow
Playwright test is unaffected.

## Architecture

```
Analysis Bundle
      ↓
AIReviewService        — creates review record, queues background task
      ↓
AIProvider (ABC)       — provider abstraction
      ↓
OllamaProvider         — first implementation (local Ollama instance)
      ↓
Ollama API             — HTTP inference endpoint
```

The backend communicates with Ollama over the internal Docker network at
`http://ollama:11434`. No application code outside the `OllamaProvider`
implementation is Ollama-specific.
