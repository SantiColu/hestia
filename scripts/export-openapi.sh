#!/usr/bin/env bash
# Export the FastAPI OpenAPI schema to shared/openapi.json.
# Placeholder: currently prints the schema for the /health-only API.
# TODO: decide whether to commit the full schema now or once business endpoints exist.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root/backend"
uv run python -c 'import json; from hestia_api.main import app; print(json.dumps(app.openapi(), indent=2, sort_keys=True))' \
  > "$root/shared/openapi.json"
echo "wrote shared/openapi.json"
