VM_HOST ?= epibridge.local
VM_USER ?= epibridge
VM_DIR  ?= /opt/epibridge
SSH     ?= ssh $(VM_USER)@$(VM_HOST)
PYTHON  ?= python3

.PHONY: dev clean clean-db install up down upgrade backup restore dev-install dev-up dev-down dev-shell dev-logs dev-build test dev-test format lint fix playwright

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

dev:
	./scripts/orbstack.sh create || true
	./scripts/orbstack.sh mount
	$(MAKE) dev-install

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

playwright:
	cd frontend && npx playwright test

format:
	cd backend && $(PYTHON) -m ruff format

lint:
	cd backend && $(PYTHON) -m ruff check

fix:
	cd backend && $(PYTHON) -m ruff check --fix
	cd backend && $(PYTHON) -m ruff format

clean-db:
	./scripts/orbstack.sh ssh 'cd $(VM_DIR) && docker compose exec -T postgres psql -U epibridge -c "DELETE FROM outputs; DELETE FROM execution_requests; DELETE FROM analysis_bundle_data_resources; DELETE FROM project_data_resources; DELETE FROM analysis_bundles; DELETE FROM projects;" && docker compose exec -T backend python -m app.cli seed-demo'
	@echo "=== Researcher artefacts reset, demo workspace re-seeded ==="

clean:
	@echo "=== EpiBridge Clean ==="
	-./scripts/orbstack.sh ssh 'cd $(VM_DIR) && docker compose down -v' 2>/dev/null || true
	-./scripts/orbstack.sh delete || true
	@echo ""
	@echo "Development environment reset."
	@echo "Recreate with: make dev"
