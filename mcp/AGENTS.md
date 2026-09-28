# mcp

Servidor MCP de Hestia. Proyecto uv independiente (Python 3.12, SDK oficial `mcp` 2.x con `MCPServer`, `httpx`).

## Reglas

- Es un cliente de la API REST y nada más. Prohibido importar `hestia_core`, `hestia_project`, `hestia_adapters` o `hestia_api`.
- Cada tool corresponde a una operación de la API. Sin lógica propia, sin cálculos: los números vienen de la API.
- Tools de grano grueso, orientadas a tareas de ingeniería (ej. "correr los casos de la etapa y devolver márgenes"), no micro-operaciones ("agregar un nodo").
- Toda tool de escritura exige un parámetro `justification: str` y lo envía a la API.
- Cada tool declara su `operationId` (`_tool("...")` en `server.py`) y `api.OPERATIONS` guarda método y ruta. `tests/test_parity.py` los valida contra `shared/openapi.json`: toda operación de la API tiene una tool salvo las listadas en `api.NOT_TOOLS` (con su motivo). Los enums (`StageType`, `TemplateId`) también se validan contra el contrato. TODO: generar los modelos de request/response desde el contrato.
- El autor de las escrituras va en los headers `X-Hestia-Actor-Kind: agent` y `X-Hestia-Actor` (`HESTIA_AGENT_NAME`, ADR 0011).
- Los errores de la API llegan al agente como `ToolError` con `código: mensaje` (p. ej. `project_locked: …`).
- Nueva operación → skill `add-api-operation`. Paridad verificada por el subagente `parity-checker`.

## Correr localmente

```sh
uv sync
# con la API levantada (make dev o uvicorn en backend/)
HESTIA_API_URL=http://127.0.0.1:8000 HESTIA_AGENT_NAME=claude uv run hestia-mcp   # stdio
uv run pytest && uv run ruff check . && uv run pyright
```

## Tools

Una por operación de la API (ver `api.OPERATIONS`):

- Sistema y catálogo: `ping`, `get_catalog`.
- Archivo: `get_session`, `new_project`, `open_project`, `save_project`, `save_project_as`, `close_project`, `list_recent_projects`, `remove_recent_project`.
- Historial: `get_history`, `undo`, `redo`.
- Esquemático: `create_system`, `rename_system`, `move_system`, `duplicate_system`, `delete_system`, `add_cell`, `rename_cell`, `delete_cell`, `branch_cell`, `list_branch_targets`, `list_link_targets`, `link_cells`, `unlink_cells`.

Sin tool: `stream_events` (SSE para la UI; los agentes leen `get_session` y `get_history`).
