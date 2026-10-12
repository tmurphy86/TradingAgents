# Targets called by hooks, CI and agents (lifecycle-os contract) — keep the names stable.
.PHONY: install dev test test-quick lint security verify preview

PY_PATHS := tradingagents/ api/ cli/ tests/

install:
	uv sync --extra api --extra dev
	cd ui && npm ci

dev:
	docker compose up api

# Full suite — same container and markers as CI.
test:
	docker compose run --rm test

# Fast subset, no Docker; the commit hook runs this.
test-quick:
	uv run --extra api --extra dev python -m pytest tests/ -m "unit or smoke" -q

lint:
	uv run --extra dev ruff check $(PY_PATHS)
	uv run --extra dev ruff format --check $(PY_PATHS)

# HIGH severity only, matching the blocking CI scan.
security:
	uv run --extra dev bandit -r tradingagents/ api/ -lll -q -c pyproject.toml

# Everything CI gates on.
verify: lint security
	uv run --extra api --extra dev python -m pytest tests/ -m "unit or smoke or regression" -q
	cd ui && npm run build

# Infra preview — apply is human-only.
preview:
	cd terraform && terraform plan
