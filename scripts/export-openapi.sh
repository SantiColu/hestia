#!/usr/bin/env bash
# Export the FastAPI OpenAPI schema to shared/openapi.json.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root/backend"
uv run python -c 'import json; from hestia_api.main import app; print(json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False))' \
  > "$root/shared/openapi.json"
echo "wrote shared/openapi.json"
