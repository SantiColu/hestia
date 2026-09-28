---
name: add-api-operation
description: Agrega o modifica un endpoint de la API de Hestia manteniendo el contrato y la paridad — endpoint FastAPI, regenerar shared/openapi.json y el cliente TS, tool MCP equivalente y test de paridad. Usala ante cualquier cambio en la superficie de la API.
---

# Agregar una operación de la API

1. **Endpoint** en `backend/apps/api/src/hestia_api/`: solo orquesta llamadas a `hestia_project`/`hestia_core`. Modelos de request/response pydantic con `operation_id` explícito y estable.
   - Escrituras: el request incluye `justification: str`; el autor sale del contexto de la sesión. TODO: mecanismo de identificación de autor.
2. **Test de la API** con `fastapi.testclient.TestClient`.
3. **Contrato**: skill `regenerate-contract` (actualiza `shared/openapi.json` y el cliente TS). Commiteá el diff del contrato junto con el endpoint.
4. **Tool MCP** en `mcp/src/hestia_mcp/`: una tool por operación (o una tool de grano grueso que compone operaciones de la API, nunca lógica propia). Si escribe, exige `justification`. Test que verifique el mapeo.
5. **Web**: si la operación es usable por humanos, agregar su uso vía el cliente generado.
6. **Paridad**: TODO: test automático de paridad API ↔ MCP ↔ web (no existe todavía). Hasta entonces, pedí revisión al subagente `parity-checker`.
7. `make test && make lint`.
