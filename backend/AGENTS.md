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
- Persistencia: un `.hestia` SQLite por proyecto con log de cambios (ADR 0006, 0008, 0010). Guardado explícito, lock y recientes en `hestia_project`.
- Autor de cada escritura: headers `X-Hestia-Actor-Kind` / `X-Hestia-Actor` (`hestia_api.deps.get_author`, ADR 0011). Justificación en el cuerpo; obligatoria en eliminar y desvincular.
- Los modelos expuestos por la API heredan de `hestia_project.base.Schema` (campos con default quedan requeridos en las respuestas del contrato).
- Errores de dominio: subclases de `hestia_project.errors.ProjectError` con `code` estable; `hestia_api.errors` las mapea a HTTP (`404`, `409`, `422`, `423`).
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

## `hestia_project`

| Módulo | Contiene |
|---|---|
| `catalog` | Tipos de etapa, entradas válidas, plantillas «Fase 0» y «Fase 1» |
| `model` | `Project` (con `SCHEMA_VERSION`), `System`, `Cell`, `Link`, estados, procedencia |
| `schematic` | Operaciones del esquemático, validación de vínculos, propagación de `outdated` |
| `history`, `document` | Log de cambios con autor y justificación; deshacer/rehacer; dirty |
| `storage`, `lock`, `recents` | Archivo `.hestia`, lock contra doble apertura, recientes |
| `workspace` | Fachada de la API: proyecto abierto, ciclo de archivo, eventos |

## `hestia_api`

`main.create_app()` compone `Workspace` + `EventBroker`; rutas en `routes/` (`meta`, `files`, `schematic`, `history`, `events`), cuerpos de request en `schemas.py`. `HESTIA_HOME` (por defecto `~/.hestia`) guarda los recientes; `HESTIA_CORS_ORIGINS` sobreescribe los orígenes permitidos.

Dependencias nuevas: `uv add --package <hestia-xxx> <lib>` en el paquete que corresponde a su capa.

## Librerías previstas (no instaladas)

numpy, scipy, CoolProp (core/adapters) · orekit-jpype, pyviewfactor, pyvista (adapters) · SALib, OpenMDAO (sensibilidad/optimización; capa a decidir por ADR).
