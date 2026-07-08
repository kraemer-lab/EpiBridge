VM_HOST      ?= epibridge.local
VM_USER      ?= epibridge
VM_DIR       ?= /opt/epibridge
SSH          ?= ssh $(VM_USER)@$(VM_HOST)
PYTHON       ?= python3
DOCKER_COMPOSE ?= docker compose

.PHONY: dev dev-ai clean clean-db install up down upgrade backup restore dev-install dev-up dev-down dev-shell dev-logs dev-build test dev-test format lint fix playwright bootstrap ci ci-clean

# --- Shared bootstrap (no VM, no SSH) ---------------------------------------
# Bootstrap initialises EpiBridge from scratch. Requires:
#   - current directory = repository root
#   - Docker + Docker Compose available
# Used by both development (inside OrbStack VM) and CI (natively).

bootstrap:
	./scripts/bootstrap.sh

reset:
	$(MAKE) clean-db
	./scripts/orbstack.sh ssh 'cd $(VM_DIR) && ./scripts/bootstrap.sh'
	@echo "=== Development environment reset to known-good state ==="

# --- CI targets (native Linux) -----------------------------------------------
# CI bootstraps EpiBridge directly on the runner, runs the canonical workflow test,
# then tears everything down.

ci: bootstrap

ci-clean:
	docker compose down -v
	rm -f .env

# --- Development (OrbStack VM) -----------------------------------------------
# Development provisions an OrbStack VM, mounts the repo, then bootstraps
# EpiBridge inside the VM using the exact same bootstrap.sh script.

dev:
	./scripts/orbstack.sh create || true
	./scripts/orbstack.sh mount
	$(MAKE) dev-install

dev-ai:
	./scripts/orbstack.sh ssh 'cd $(VM_DIR) && $(DOCKER_COMPOSE) --profile ai up -d'

dev-install:
	./scripts/orbstack.sh ssh 'cd $(VM_DIR) && ./scripts/install.sh --dev'

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

install:
	$(SSH) 'cd $(VM_DIR) && ./scripts/install.sh'

install-dev:
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
	cd frontend && npx playwright test

# --- Maintenance -------------------------------------------------------------

clean-db:
	./scripts/orbstack.sh ssh 'cd $(VM_DIR) && docker compose start postgres 2>/dev/null; docker compose exec -T postgres psql -U epibridge -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" 2>/dev/null || (docker compose up -d postgres && sleep 3 && docker compose exec -T postgres psql -U epibridge -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"); docker compose restart backend'
	@echo "=== Database reset (all tables recreated on startup) ==="

clean:
	@echo "=== EpiBridge Clean ==="
	-./scripts/orbstack.sh ssh 'cd $(VM_DIR) && docker compose down -v' 2>/dev/null || true
	-./scripts/orbstack.sh delete || true
	@echo ""
	@echo "Development environment reset."
	@echo "Recreate with: make dev"
