#!/usr/bin/env bash
# Generate the TypeScript API types for app/ from shared/openapi.json (ADR 0013).
# openapi-typescript writes only types; app/src/api/client.ts wraps them with openapi-fetch.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root/app"
pnpm exec openapi-typescript "$root/shared/openapi.json" -o src/api/schema.gen.ts
pnpm exec prettier --write src/api/schema.gen.ts > /dev/null
echo "wrote app/src/api/schema.gen.ts"
