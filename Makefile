VM_HOST      ?= epibridge.local
VM_USER      ?= epibridge
VM_DIR       ?= /opt/epibridge
SSH          ?= ssh $(VM_USER)@$(VM_HOST)
PYTHON       ?= python3
DOCKER_COMPOSE ?= docker compose

# Load execution context (silent if absent — defaults to native Docker).
-include .epibridge-context
EPIBRIDGE_TARGET ?= native

.PHONY: certs dev dev-ai dev-destroy clean-db install uninstall up down upgrade backup restore dev-up dev-down dev-shell dev-logs dev-build test dev-test format lint fix playwright ci ci-clean demo deploy deploy-dev seed-institution seed-personas seed-developer seed-demo reset

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
		if [ "$(EPIBRIDGE_TARGET)" = "orbstack" ]; then \
			./scripts/orbstack.sh ssh 'cd $(VM_DIR) && docker compose restart reverse-proxy' || { \
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
				false; }; \
		else \
			docker compose restart reverse-proxy || { \
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
				false; }; \
		fi; \
		echo ""; \
		echo "✓ Certificate configuration applied."; \
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
	./scripts/orbstack.sh ssh 'cd $(VM_DIR) && ./scripts/install.sh --dev && ./scripts/seed-institution.sh'
	@echo "EPIBRIDGE_TARGET=$(TARGET)" > .epibridge-context
	@echo "EPIBRIDGE_VM=epibridge" >> .epibridge-context
else
	./scripts/bootstrap.sh
	./scripts/seed-institution.sh
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
ifeq ($(EPIBRIDGE_TARGET),orbstack)
	-./scripts/orbstack.sh ssh 'cd $(VM_DIR) && docker compose down' 2>/dev/null || true
	-./scripts/orbstack.sh delete || true
else
	-docker compose down -v 2>/dev/null || true
endif
	@rm -f .epibridge-context
	@rm -rf certs
	@if [ -f .env ]; then \
		echo ""; \
		echo ".env preserved at $$PWD/.env"; \
	fi

# --- Evaluation ----------------------------------------------------------------
# demo seeds evaluation personas and prints the welcome message.
# Dispatch depends on the execution context (.epibridge-context).

demo:
ifeq ($(EPIBRIDGE_TARGET),orbstack)
	./scripts/orbstack.sh ssh 'cd $(VM_DIR) && ./scripts/seed-personas.sh && ./scripts/seed-demo.sh'
else
	./scripts/seed-personas.sh
	./scripts/seed-demo.sh
endif

reset:
	$(MAKE) clean-db
	./scripts/orbstack.sh ssh 'cd $(VM_DIR) && ./scripts/bootstrap.sh && ./scripts/seed-institution.sh && ./scripts/seed-personas.sh && ./scripts/seed-developer.sh'
	@echo "=== Development environment reset to known-good state ==="

# --- CI (native Linux) ---------------------------------------------------------
# CI bootstraps the platform natively (no OrbStack) and seeds all accounts needed
# by the test suite.  Composes the same internal building blocks as install.

ci:
	./scripts/bootstrap.sh
	./scripts/seed-institution.sh
	./scripts/seed-personas.sh
	./scripts/seed-developer.sh

ci-clean:
	docker compose down -v
	rm -f .env

# --- Development ----------------------------------------------------------------
# dev rebuilds and restarts application services for the edit–build–run cycle.
# It deliberately skips bootstrap (EE image builds, health wait) and does NOT
# reseed users or terms — those are one-time concerns managed by install/reset.
# Dispatch depends on the execution context (.epibridge-context).

dev:
ifeq ($(EPIBRIDGE_TARGET),orbstack)
	./scripts/orbstack.sh ssh 'cd $(VM_DIR) && docker compose build backend frontend worker && docker compose up -d'
else
	docker compose build backend frontend worker
	docker compose up -d
endif

dev-ai:
	./scripts/orbstack.sh ssh 'cd $(VM_DIR) && $(DOCKER_COMPOSE) --profile ai up -d'

dev-up:
	./scripts/orbstack.sh ssh 'cd $(VM_DIR) && docker compose up -d'

dev-down:
	./scripts/orbstack.sh ssh 'cd $(VM_DIR) && docker compose down'

dev-shell:
	./scripts/orbstack.sh ssh

dev-logs:
	./scripts/orbstack.sh ssh 'cd $(VM_DIR) && docker compose logs -f'

SVC ?=

dev-build:
	./scripts/orbstack.sh ssh 'cd $(VM_DIR) && docker compose build $(SVC) && docker compose up -d $(SVC)'

# --- Production deployment (SSH to Ubuntu VM) --------------------------------

deploy:
	$(SSH) 'cd $(VM_DIR) && ./scripts/install.sh'

deploy-dev:
	$(SSH) 'cd $(VM_DIR) && ./scripts/install.sh --dev'

up:
	$(SSH) 'cd $(VM_DIR) && docker compose up -d'

down:
	$(SSH) 'cd $(VM_DIR) && docker compose down'

upgrade:
	$(SSH) 'cd $(VM_DIR) && ./scripts/upgrade.sh'

backup:
	$(SSH) 'cd $(VM_DIR) && ./scripts/backup.sh'

restore:
	$(SSH) 'cd $(VM_DIR) && ./scripts/restore.sh $(FILE)'

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

dev-test:
	./scripts/orbstack.sh ssh 'cd $(VM_DIR) && docker compose exec -T backend python3 -m pytest tests/unit tests/integration tests/smoke -v --no-header -q --tb=short'

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
	./scripts/orbstack.sh ssh 'cd $(VM_DIR) && docker compose start postgres 2>/dev/null; docker compose exec -T postgres psql -U epibridge -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" 2>/dev/null || (docker compose up -d postgres && sleep 3 && docker compose exec -T postgres psql -U epibridge -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"); docker compose restart backend'
	@echo "=== Database reset (all tables recreated on startup) ==="

dev-destroy:
	@echo "=== EpiBridge Clean ==="
	-./scripts/orbstack.sh ssh 'cd $(VM_DIR) && docker compose down -v' 2>/dev/null || true
	-./scripts/orbstack.sh delete || true
	@echo ""
	@echo "Development environment reset."
	@echo "Recreate with: make dev"
