VM_HOST      ?= epibridge.local
VM_USER      ?= epibridge
VM_DIR       ?= /opt/epibridge
SSH          ?= ssh $(VM_USER)@$(VM_HOST)
PYTHON       ?= python3

# Load execution context (silent if absent — defaults to native Docker).
-include .epibridge-context
EPIBRIDGE_TARGET ?= native

.PHONY: install uninstall certs ai demo up down logs shell build upgrade backup restore clean-db reset deploy deploy-dev dev test format lint fix playwright ci ci-clean

# --- Installation ----------------------------------------------------------------
# install is the canonical first-run experience.  Accepts an optional TARGET
# parameter:
#
#   TARGET=orbstack  (default)  — OrbStack VM installation
#   TARGET=native               — native Docker installation (no VM)
#
# Installs the platform, seeds the institution, and writes the execution context.
# Idempotent — safe to run repeatedly.

TARGET ?= orbstack

# Generate and apply TLS certificates for the hostname derived from PUBLIC_URL.
# Applies the certificate configuration to the running installation: generates
# or refreshes certificates, then restarts the reverse proxy so that new
# certificates take effect immediately.
# Uses mkcert when available; falls back to self-signed certificates.
# Idempotent: safe to run at any time.
certs:
	./scripts/setup-certs.sh
	@if [ -f .epibridge-context ]; then \
		echo "Restarting reverse proxy..."; \
		if ./scripts/platform.sh restart reverse-proxy; then \
			echo ""; \
			echo "✓ Certificate configuration applied."; \
		else \
			echo ""; \
			echo "Certificates were generated successfully."; \
			echo ""; \
			echo "The new certificates are not yet active because the reverse"; \
			echo "proxy could not be restarted automatically."; \
			echo ""; \
			echo "Please restart the reverse proxy manually, then revisit:"; \
			echo ""; \
			echo "    https://localhost"; \
			echo ""; \
			false; \
		fi; \
	fi

install: certs
	$(eval ENV_FRESH := $(shell [ -f .env ] && echo "no" || echo "yes"))
	@if [ "$(TARGET)" != "orbstack" ] && [ "$(TARGET)" != "native" ]; then \
		echo "Unsupported installation target: $(TARGET)"; \
		echo "Supported targets: orbstack, native"; \
		exit 1; \
	fi
ifeq ($(TARGET),orbstack)
	./scripts/orbstack.sh create || true
	./scripts/orbstack.sh mount
	@echo "EPIBRIDGE_TARGET=$(TARGET)" > .epibridge-context
	@echo "EPIBRIDGE_VM=epibridge" >> .epibridge-context
	./scripts/platform.sh run ./scripts/install.sh --dev
	./scripts/platform.sh run ./scripts/seed-institution.sh
else
	./scripts/platform.sh run ./scripts/bootstrap.sh
	./scripts/platform.sh run ./scripts/seed-institution.sh
	@echo "EPIBRIDGE_TARGET=$(TARGET)" > .epibridge-context
endif
	@echo ""
	@echo "=== EpiBridge installed ==="
	@echo ""
	@echo "Frontend:"
	@echo "  https://localhost/"
	@echo ""
	@echo "Administrator account:"
	@echo "  Email:"
	@echo "      admin@epibridge.local"
	@echo "  Password:"
	@echo "      Stored as ADMIN_PASSWORD in .env"
	@echo ""
	@echo "Configuration:"
	@if [ "$(ENV_FRESH)" = "yes" ]; then \
		echo "  .env was created automatically from .env.example"; \
		echo "  and contains installation-specific configuration,"; \
		echo "  including:"; \
		echo ""; \
		echo "    - administrator password"; \
		echo "    - application secrets"; \
		echo "    - optional SMTP configuration"; \
	else \
		echo "  Existing .env configuration reused."; \
	fi
	@echo ""
	@echo "Platform status:"
	@echo "  - Platform running"
	@echo "  - Platform Terms published"
	@echo "  - Institutional publications registered"
	@echo ""
	@echo "To prepare an evaluation environment:"
	@echo ""
	@echo "    make demo"

# --- Uninstall -------------------------------------------------------------------
# uninstall stops the platform and removes the installation.
# Dispatch depends on the execution context (.epibridge-context).
# The Git working tree and .env are preserved.

uninstall:
	@echo "=== EpiBridge Uninstall ==="
	-./scripts/platform.sh compose down 2>/dev/null || true
	-./scripts/platform.sh destroy || true
	@rm -f .epibridge-context
	@rm -rf certs
	@if [ -f .env ]; then \
		echo ""; \
		echo ".env preserved at $$PWD/.env"; \
	fi

# Enable and prepare AI assistance for this EpiBridge installation.
# Configures the platform, starts AI services, pulls the configured
# model, restarts affected services, and verifies AI is operational.
# Idempotent — safe to run at any time.
.PHONY: ai
OLLAMA_MODEL := $(shell grep '^OLLAMA_MODEL=' .env 2>/dev/null | cut -d= -f2-)
OLLAMA_MODEL ?= llama3.2

ai:
	./scripts/setup-ai.sh
	@if [ -f .epibridge-context ]; then \
		echo "Starting AI services..."; \
		./scripts/platform.sh compose --profile ai up -d || { \
			echo ""; \
			echo "Failed to start AI services."; \
			echo "Check Docker status and try again."; \
			false; }; \
		echo "Pulling AI model ($(OLLAMA_MODEL))..."; \
		./scripts/platform.sh exec ollama ollama pull $(OLLAMA_MODEL) || { \
			echo ""; \
			echo "Failed to pull AI model."; \
			echo "Check network connectivity and Ollama status."; \
			false; }; \
		echo "Restarting backend..."; \
		./scripts/platform.sh restart backend || true; \
		echo "Verifying AI readiness..."; \
		for i in 1 2 3 4 5 6 7 8 9 10 11 12; do \
			./scripts/platform.sh exec backend python -m app.cli check-ai-status 2>/dev/null; \
			if [ $$? -eq 0 ]; then \
				echo ""; \
				echo "=== AI assistance is operational ==="; \
				echo "Model: $(OLLAMA_MODEL)"; \
				echo ""; \
				echo "AI review is not yet enabled."; \
				echo "Enable it in the admin interface:"; \
				echo "  Admin > Settings > Enable AI-assisted bundle review"; \
				exit 0; \
			fi; \
			sleep 5; \
		done; \
		echo ""; \
		echo "=== AI verification timed out ==="; \
		echo "Run the CLI command to diagnose:"; \
		echo "  ./scripts/platform.sh exec backend python -m app.cli check-ai-status"; \
		false; \
	fi

# --- Evaluation ----------------------------------------------------------------
# demo seeds evaluation personas and prints the welcome message.
# Dispatch depends on the execution context (.epibridge-context).

demo:
	./scripts/platform.sh run ./scripts/seed-personas.sh
	./scripts/platform.sh run ./scripts/seed-demo.sh

# --- Platform lifecycle ---------------------------------------------------------

up:
	./scripts/platform.sh compose up -d

down:
	./scripts/platform.sh compose down

logs:
	./scripts/platform.sh logs -f

shell:
	./scripts/platform.sh shell

SVC ?=
build:
	./scripts/platform.sh compose build $(SVC)
	./scripts/platform.sh compose up -d $(SVC)

# --- CI (native Linux) ---------------------------------------------------------

ci:
	./scripts/platform.sh run ./scripts/bootstrap.sh
	./scripts/platform.sh run ./scripts/seed-institution.sh
	./scripts/platform.sh run ./scripts/seed-personas.sh
	./scripts/platform.sh run ./scripts/seed-developer.sh
	@echo "EPIBRIDGE_TARGET=native" > .epibridge-context

ci-clean:
	./scripts/platform.sh compose down -v
	rm -f .env

# --- Development ----------------------------------------------------------------

dev:
	./scripts/platform.sh compose build backend frontend worker
	./scripts/platform.sh compose up -d

dev-test:
	./scripts/platform.sh exec backend python3 -m pytest tests/unit tests/integration tests/smoke -v --no-header -q --tb=short

# --- Production deployment (SSH to Ubuntu VM) ----------------------------------

deploy:
	$(SSH) 'cd $(VM_DIR) && ./scripts/install.sh'
	@echo "EPIBRIDGE_TARGET=remote" > .epibridge-context
	@echo "EPIBRIDGE_HOST=$(VM_HOST)" >> .epibridge-context
	@echo "EPIBRIDGE_USER=$(VM_USER)" >> .epibridge-context
	@echo "EPIBRIDGE_DIR=$(VM_DIR)" >> .epibridge-context

deploy-dev:
	$(SSH) 'cd $(VM_DIR) && ./scripts/install.sh --dev'
	@echo "EPIBRIDGE_TARGET=remote" > .epibridge-context
	@echo "EPIBRIDGE_HOST=$(VM_HOST)" >> .epibridge-context
	@echo "EPIBRIDGE_USER=$(VM_USER)" >> .epibridge-context
	@echo "EPIBRIDGE_DIR=$(VM_DIR)" >> .epibridge-context

upgrade:
	./scripts/platform.sh run ./scripts/upgrade.sh

backup:
	./scripts/platform.sh run ./scripts/backup.sh

restore:
	./scripts/platform.sh run ./scripts/restore.sh $(FILE)

# --- Code quality ------------------------------------------------------------

test:
	@failed=0; \
	(cd backend && $(PYTHON) -m pytest tests/unit -v --cov=app --cov-report=term-missing --no-header -q) || failed=1; \
	echo ""; \
	(cd backend && $(PYTHON) -m pytest tests/integration -v --no-header -q) || failed=1; \
	echo ""; \
	(cd backend && $(PYTHON) -m pytest tests/smoke -v --no-header -q) || failed=1; \
	echo ""; \
	if [ $$failed -eq 0 ]; then echo "=== All tests passed ==="; else echo "=== Some tests failed ==="; exit 1; fi

format:
	cd backend && $(PYTHON) -m ruff format

lint:
	cd backend && $(PYTHON) -m ruff check

fix:
	cd backend && $(PYTHON) -m ruff check --fix
	cd backend && $(PYTHON) -m ruff format

# --- Testing (requires full stack) -------------------------------------------

playwright:
	export ADMIN_PASSWORD=$$(grep ^ADMIN_PASSWORD= .env | cut -d= -f2-); \
	cd frontend && npx playwright test

# --- Maintenance -------------------------------------------------------------

clean-db:
	./scripts/platform.sh compose exec -T postgres psql -U epibridge -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" 2>/dev/null || \
		(./scripts/platform.sh compose up -d postgres && sleep 3 && \
		 ./scripts/platform.sh compose exec -T postgres psql -U epibridge -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
	./scripts/platform.sh restart backend
	@echo "=== Database reset (all tables recreated on startup) ==="

reset:
	$(MAKE) clean-db
	./scripts/platform.sh run ./scripts/bootstrap.sh
	./scripts/platform.sh run ./scripts/seed-institution.sh
	./scripts/platform.sh run ./scripts/seed-personas.sh
	./scripts/platform.sh run ./scripts/seed-developer.sh
	@echo "=== Development environment reset to known-good state ==="

# --- Internal targets ---------------------------------------------------------

dev-destroy:
	./scripts/platform.sh compose down
	@echo "=== Development containers stopped ==="
