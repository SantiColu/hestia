# mcp

Servidor MCP de Hestia. Proyecto uv independiente (Python 3.12, SDK oficial `mcp` 2.x con `MCPServer`, `httpx`).

## Reglas

- Es un cliente de la API REST y nada más. Prohibido importar `hestia_core`, `hestia_project`, `hestia_adapters` o `hestia_api`.
- Cada tool corresponde a una operación de la API. Sin lógica propia, sin cálculos: los números vienen de la API.
- Tools de grano grueso, orientadas a tareas de ingeniería (ej. "correr los casos de la etapa y devolver márgenes"), no micro-operaciones ("agregar un nodo").
- Toda tool de escritura exige un parámetro `justification: str` y lo envía a la API.
- Tipos de request/response derivados de `shared/openapi.json`. TODO: definir cómo se generan/validan desde el contrato.
- Nueva operación → skill `add-api-operation`. Paridad verificada por el subagente `parity-checker`.

## Correr localmente

```sh
uv sync
# con la API levantada (make dev o uvicorn en backend/)
HESTIA_API_URL=http://localhost:8000 uv run hestia-mcp   # transporte stdio
uv run pytest && uv run ruff check . && uv run pyright
```

Tools actuales: `ping` → `GET /health`.
