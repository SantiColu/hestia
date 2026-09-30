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
- Estilo: el de Python de `docs/conventions.md` (mismas reglas de ruff que el backend). Docstring de cada tool en inglés, orientado al agente: qué hace, qué devuelve y cuándo falla (con el `code` del error).

## Correr localmente

```sh
uv sync
# con la API levantada (make dev o uvicorn en backend/)
HESTIA_API_URL=http://127.0.0.1:8000 HESTIA_AGENT_NAME=claude uv run hestia-mcp   # stdio
uv run pytest && uv run ruff check . && uv run pyright
```

## Tools

Una por operación de la API (ver `api.OPERATIONS`):

- Sistema y catálogo: `ping`, `get_catalog`, `get_artifact_schema`.
- Archivo: `get_session`, `new_project`, `open_project`, `save_project`, `save_project_as`, `close_project`, `list_recent_projects`, `remove_recent_project`.
- Historial: `get_history`, `undo`, `redo`.
- Esquemático: `create_system`, `rename_system`, `move_system`, `duplicate_system`, `delete_system`, `add_cell`, `rename_cell`, `delete_cell`, `branch_cell`, `list_branch_options`, `list_branch_targets`, `list_link_targets`, `get_cell_context`, `link_cells`, `unlink_cells`.
- Artefactos de etapas formulario (ADR 0017) y parámetros de etapas de cálculo (ADR 0021): `get_cell_artifact`, `validate_cell_artifact` (en seco) y `apply_cell_artifact` (con justificación).
- Etapas de cálculo (ADR 0021): `update_cell` (Actualizar; justificación opcional), `get_cell_result` (estado, procedencia y resultado sin perfiles), `get_orbit_profile` (un perfil orbital de Entorno por condición y modo de actitud) y `preview_orbit` (la órbita de un borrador de parámetros de Entorno, sin guardar nada; ADR 0023).
- Portapapeles (ADR 0014): `copy_to_clipboard` (devuelve el fragmento) y `paste_from_clipboard` (lo recibe; sirve para otro proyecto). Cortar = copiar + `delete_system`/`delete_cell`.

Sin tool: `stream_events` (SSE para la UI; los agentes leen `get_session` y `get_history`).
