# backend

uv workspace (Python 3.12). Toda la lógica de dominio de Hestia vive acá.

## Capas

| Paquete | Ruta | Contiene | Puede importar |
|---|---|---|---|
| `hestia_core` | `packages/hestia-core` | Física pura, modelos de artefactos (pydantic) y su validación (`mission`, `forms`, `orbits`), física del entorno (`sun`, `eclipse`, `view_factors`, `attitude`), etapa Entorno (`environment`: parámetros, resultado, Protocol `EnvironmentProvider` y proveedor analítico), Protocols de proveedores externos | nada de Hestia |
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
- Autor de cada escritura: headers `X-Hestia-Actor-Kind` / `X-Hestia-Actor` (`hestia_api.deps.get_author`, ADR 0011). Justificación en el cuerpo; obligatoria en eliminar, desvincular y aplicar un artefacto.
- Los modelos expuestos por la API heredan de `hestia_project.base.Schema` (campos con default quedan requeridos en las respuestas del contrato).
- Errores de dominio: subclases de `hestia_project.errors.ProjectError` con `code` estable; `hestia_api.errors` las mapea a HTTP (`404`, `409`, `422`, `423`). Un fragmento de portapapeles inválido es `invalid_fragment` (422); una etapa sin formulario, `stage_not_implemented` (422).
- Sin IA (ADR 0015): prohibido importar o depender de SDKs/frameworks de IA (anthropic, openai, pydantic-ai, logfire, langchain…); lo verifican el contrato de import-linter y `tests/test_no_ai_dependencies.py`. `pydantic` base sí.
- Cambios en la API → skill `add-api-operation` (regenerar contrato + tool MCP).

## Estilo de código

Reglas completas en `docs/conventions.md` («Código limpio» → General y Python). Lo esencial:

- pyright strict y ruff con reglas ampliadas (`[tool.ruff.lint]` en `pyproject.toml`: comprensiones, `pathlib`, sin `print`, sin código comentado, `datetime` con zona, sin `except` ciego, sin argumentos sin usar). No se relajan sin motivo escrito.
- Mensajes para personas (`Problem.message`, errores de dominio, `Outcome.summary`) en español; código, identificadores y docstrings en inglés.
- Validaciones repetidas → helper (ver `_Problems` en `hestia_core.mission`); búsquedas por id → `get_cell`/`get_system`/`get_link` de `hestia_project.schematic`, que lanzan `NotFoundError`.
- `assert x is not None` solo para estrechar tipos después de una validación que ya lo garantiza; nunca como validación de entrada.
- Antes de terminar: skill `clean-code-review`.

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
| `catalog` | Tipos de etapa (clase, requisitos de contexto, orden, implementada), plantillas «Fase 0» y «Fase 1» con sus vínculos |
| `model` | `Project` (con `SCHEMA_VERSION`), `System`, `Cell`, `Link`, estados, procedencia |
| `schematic` | Operaciones del esquemático, contexto resuelto (ADR 0016), las cinco reglas de vínculo, propagación de `outdated` |
| `forms`, `artifacts` | Registro de formularios (etapas formulario y parámetros de etapas de cálculo) y leer / validar en seco / aplicar su artefacto con procedencia por campo (ADR 0017, 0019) |
| `computations` | Registro de etapas de cálculo, Actualizar, estados, procedencia y lectura del resultado y de los perfiles (ADR 0021, 0022) |
| `migration` | Subir proyectos de versiones anteriores (vínculos reevaluados, avisos) |
| `clipboard` | Fragmentos versionados para copiar y pegar sistemas y celdas (ADR 0014) |
| `history`, `document` | Log de cambios con autor y justificación; deshacer/rehacer; dirty |
| `storage`, `lock`, `recents` | Archivo `.hestia`, lock contra doble apertura, recientes |
| `workspace` | Fachada de la API: proyecto abierto, ciclo de archivo, eventos |

## `hestia_api`

`main.create_app()` compone `Workspace` + `EventBroker`; rutas en `routes/` (`meta`, `files`, `schematic`, `artifacts`, `computations`, `clipboard`, `history`, `events`), cuerpos de request en `schemas.py`. `HESTIA_HOME` (por defecto `~/.hestia`) guarda los recientes; `HESTIA_CORS_ORIGINS` sobreescribe los orígenes permitidos.

Dependencias nuevas: `uv add --package <hestia-xxx> <lib>` en el paquete que corresponde a su capa.

## Librerías

Instaladas: pydantic y numpy (core). Skyfield solo como dependencia de desarrollo: oráculo de β y eclipse en los tests (ADR 0020); la efeméride DE421 se descarga en `HESTIA_SKYFIELD_CACHE` (por defecto `~/.cache/hestia/skyfield`) y sin red esos tests se saltean.

Previstas (no instaladas): scipy, CoolProp (core/adapters) · orekit-jpype, pyviewfactor, pyvista (adapters) · SALib, OpenMDAO (sensibilidad/optimización; capa a decidir por ADR).
