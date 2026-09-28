---
name: regenerate-contract
description: Exporta el OpenAPI desde FastAPI a shared/openapi.json y regenera el cliente TypeScript de la UI. Usala después de cualquier cambio en endpoints o modelos pydantic expuestos por la API.
---

# Regenerar el contrato

```sh
make contract
```

Equivale a:

1. `scripts/export-openapi.sh` — escribe `shared/openapi.json` desde `hestia_api.main:app`.
2. `scripts/generate-client.sh` — genera los tipos TS en `app/src/api/schema.gen.ts` con openapi-typescript (ADR 0013); `app/src/api/client.ts` los usa con openapi-fetch.

Después:

- Revisá el diff de `shared/openapi.json`: cambios incompatibles (campos eliminados/renombrados) requieren nueva versión de esquema.
- Actualizá las tools MCP afectadas; `cd mcp && uv run pytest` verifica rutas y enums contra el contrato.
- `make lint` (el build de la UI debe tipar contra el cliente nuevo).

Nunca edites `shared/openapi.json` a mano.
