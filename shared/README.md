# shared

Contrato entre backend, UI y MCP.

- `openapi.json`: especificación OpenAPI **generada** desde FastAPI (`make contract`). No editar a mano. Es la fuente para el cliente TS de la UI y las tools del MCP.
- Por ahora es un placeholder vacío: se exportará cuando existan operaciones de la API.
- Cambios en el contrato se revisan como cambios de API: skill `add-api-operation`.
