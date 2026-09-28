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
2. `scripts/generate-client.sh` — genera el cliente TS en `app/`. TODO: placeholder; el generador (openapi-typescript, orval o hey-api) no está elegido.

Después:

- Revisá el diff de `shared/openapi.json`: cambios incompatibles (campos eliminados/renombrados) requieren nueva versión de esquema.
- Actualizá las tools MCP afectadas. TODO: definir cómo el MCP deriva tipos del contrato.
- `make lint` (el build de la UI debe tipar contra el cliente nuevo).

Nunca edites `shared/openapi.json` a mano.
