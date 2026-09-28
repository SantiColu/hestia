.DEFAULT_GOAL := help
SHELL := bash

BACKEND := backend
MCP := mcp
WEB := web

.PHONY: help setup dev dev-api dev-web test lint format contract

help: ## List available commands
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup: ## Install dependencies for backend, mcp and web
	cd $(BACKEND) && uv sync
	cd $(MCP) && uv sync
	cd $(WEB) && pnpm install

dev: ## Run API (:8000) and web (:3000) together
	@trap 'kill 0' EXIT; $(MAKE) --no-print-directory dev-api & $(MAKE) --no-print-directory dev-web & wait

dev-api: ## Run only the API
	cd $(BACKEND) && uv run uvicorn hestia_api.main:app --reload --port 8000

dev-web: ## Run only the web
	cd $(WEB) && pnpm dev

test: ## Run Python test suites
	cd $(BACKEND) && uv run pytest
	cd $(MCP) && uv run pytest

lint: ## Run all linters, type checkers and dependency contracts
	cd $(BACKEND) && uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run lint-imports
	cd $(MCP) && uv run ruff check . && uv run ruff format --check . && uv run pyright
	cd $(WEB) && pnpm lint && pnpm typecheck && pnpm format:check

format: ## Auto-format all code
	cd $(BACKEND) && uv run ruff check --fix . && uv run ruff format .
	cd $(MCP) && uv run ruff check --fix . && uv run ruff format .
	cd $(WEB) && pnpm format

contract: ## Export OpenAPI to shared/ and regenerate the TS client
	./scripts/export-openapi.sh
	./scripts/generate-client.sh
