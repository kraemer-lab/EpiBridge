VM_HOST ?= epibridge.local
VM_USER ?= epibridge
VM_DIR  ?= /opt/epibridge
SSH     ?= ssh $(VM_USER)@$(VM_HOST)

.PHONY: dev clean install up down upgrade backup restore dev-install dev-up dev-down dev-shell dev-logs dev-build

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

clean:
	@echo "=== EpiBridge Clean ==="
	-./scripts/orbstack.sh ssh 'cd $(VM_DIR) && docker compose down -v' 2>/dev/null || true
	-./scripts/orbstack.sh delete || true
	@echo ""
	@echo "Development environment reset."
	@echo "Recreate with: make dev"
