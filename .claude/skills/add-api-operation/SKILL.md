---
name: add-api-operation
description: Agrega o modifica un endpoint de la API de Hestia manteniendo el contrato y la paridad — endpoint FastAPI, regenerar shared/openapi.json y el cliente TS, tool MCP equivalente y test de paridad. Usala ante cualquier cambio en la superficie de la API.
---

# Agregar una operación de la API

1. **Endpoint** en `backend/apps/api/src/hestia_api/`: solo orquesta llamadas a `hestia_project`/`hestia_core`. Modelos de request/response pydantic con `operation_id` explícito y estable.
   - Escrituras: el request incluye `justification: str`; el autor sale de los headers vía `AuthorDep` (ADR 0011). Operaciones destructivas: agregarlas a `JUSTIFICATION_REQUIRED`.
   - Modelos de respuesta: heredar de `hestia_project.base.Schema`.
2. **Test de la API** con `fastapi.testclient.TestClient`.
3. **Contrato**: skill `regenerate-contract` (actualiza `shared/openapi.json` y el cliente TS). Commiteá el diff del contrato junto con el endpoint.
4. **Tool MCP** en `mcp/src/hestia_mcp/`: una tool por operación (`@_tool("<operationId>")` en `server.py` y método/ruta en `api.OPERATIONS`). Si escribe, exige `justification`. Agregar el caso en `tests/test_tools.py`; si la operación no debe tener tool, justificarlo en `api.NOT_TOOLS`.
5. **Web**: si la operación es usable por humanos, agregar su uso vía el cliente generado (estilos según la skill `ui-styling`).
6. **Paridad**: `mcp/tests/test_parity.py` falla si una operación del contrato no tiene tool. Paridad con la UI: TODO test automático; pedí revisión al subagente `parity-checker`.
7. Skill `clean-code-review` (incluye `make test && make lint`).
