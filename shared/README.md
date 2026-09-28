# shared

Contrato entre backend, UI y MCP.

- `openapi.json`: especificación OpenAPI **generada** desde FastAPI (`make contract`). No editar a mano. Es la fuente para el cliente TS de la UI y las tools del MCP.
- Lo consumen `app/src/api/schema.gen.ts` (openapi-typescript, ADR 0013) y el test de paridad del MCP (`mcp/tests/test_parity.py`).
- Cambios en el contrato se revisan como cambios de API: skill `add-api-operation`.
