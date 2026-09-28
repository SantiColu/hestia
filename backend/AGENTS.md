# backend

uv workspace (Python 3.12). Toda la lógica de dominio de Hestia vive acá.

## Capas

| Paquete | Ruta | Contiene | Puede importar |
|---|---|---|---|
| `hestia_core` | `packages/hestia-core` | Física pura, modelos de artefactos (pydantic), Protocols de proveedores externos | nada de Hestia |
| `hestia_adapters` | `packages/hestia-adapters` | Implementaciones de los Protocols de core (Orekit, pyViewFactor, SciPy…) | `hestia_core` |
| `hestia_project` | `packages/hestia-project` | Grafo de etapas, estados, procedencia, historial/deshacer, persistencia | `hestia_core` |
| `hestia_api` | `apps/api` | FastAPI: rutas, DTOs, composición de dependencias | todos |

Las reglas las hace cumplir import-linter (`[tool.importlinter]` en `pyproject.toml`). No las relajes sin un ADR.

## Reglas

- `hestia_core` no hace I/O ni depende de librerías externas de herramientas: las pide por Protocol.
- Los endpoints solo orquestan; no contienen física ni reglas de workflow.
- Todo cálculo nuevo requiere test contra un caso de referencia (a mano o de libro), con tolerancia explícita y la referencia citada en el test. Ver skill `physics-validation`.
- Unidades SI, temperaturas en K. Nombres con sufijo de unidad cuando no es SI obvio (`power_w`, `area_m2`, `temperature_k`).
- Toda escritura por API registra autor y justificación.
- Persistencia prevista: SQLite + log de cambios (ADR 0006). No implementada aún.
- Cambios en la API → skill `add-api-operation` (regenerar contrato + tool MCP).

## Comandos (desde `backend/`)

```sh
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run lint-imports
uv run uvicorn hestia_api.main:app --reload   # http://localhost:8000/health
```

Dependencias nuevas: `uv add --package <hestia-xxx> <lib>` en el paquete que corresponde a su capa.

## Librerías previstas (no instaladas)

numpy, scipy, CoolProp (core/adapters) · orekit-jpype, pyviewfactor, pyvista (adapters) · SALib, OpenMDAO (sensibilidad/optimización; capa a decidir por ADR).
