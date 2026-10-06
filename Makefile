.DEFAULT_GOAL := help
SHELL := bash

BACKEND := backend
MCP := mcp
APP := app

.PHONY: help setup dev desktop desktop-app dev-api dev-app test lint format contract

help: ## List available commands
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Install dependencies for backend, mcp and app
	cd $(BACKEND) && uv sync
	cd $(MCP) && uv sync
	cd $(APP) && pnpm install

dev: ## Run API (:8000) and UI (:5173) together
	@trap 'kill 0' EXIT; $(MAKE) --no-print-directory dev-api & $(MAKE) --no-print-directory dev-app & wait

desktop: ## Run API (:8000) and the desktop shell (Tauri, starts Vite itself)
	@trap 'kill 0' EXIT; $(MAKE) --no-print-directory dev-api & (cd $(APP) && pnpm tauri dev) & wait

desktop-app: ## Run only the desktop shell, against the API and UI of a running `make dev`
	cd $(APP) && pnpm tauri dev --config '{"build":{"beforeDevCommand":""}}'

dev-api: ## Run only the API
	cd $(BACKEND) && uv run uvicorn hestia_api.main:app --reload --port 8000

dev-app: ## Run only the UI (Vite)
	cd $(APP) && pnpm dev

test: ## Run Python test suites
	cd $(BACKEND) && uv run pytest
	cd $(MCP) && uv run pytest

lint: ## Run all linters, type checkers and dependency contracts
	cd $(BACKEND) && uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run lint-imports
	cd $(MCP) && uv run ruff check . && uv run ruff format --check . && uv run pyright
	cd $(APP) && pnpm lint && pnpm typecheck && pnpm format:check
	cd $(APP)/src-tauri && cargo fmt --check && cargo clippy -q -- -D warnings

format: ## Auto-format all code
	cd $(BACKEND) && uv run ruff check --fix . && uv run ruff format .
	cd $(MCP) && uv run ruff check --fix . && uv run ruff format .
	cd $(APP) && pnpm format
	cd $(APP)/src-tauri && cargo fmt

contract: ## Export OpenAPI to shared/ and regenerate the TS client
	./scripts/export-openapi.sh
	./scripts/generate-client.sh
