---
name: add-workflow-stage
description: Implementa una etapa del workflow de Hestia (ej. mission, global_balance, load_cases) de punta a punta — esquemas, física, registro en el grafo, API, tool MCP, vista web y tests. Usala al agregar o implementar cualquier etapa de las fases 0 o 1.
---

# Agregar una etapa del workflow

Referencia de dominio: `docs/workflow-fases-0-1.md`. Id en snake_case inglés; el número (0.3, 1.4…) es metadato.

Orden obligatorio (cada paso con sus tests antes del siguiente):

1. **Esquemas de artefactos** (pydantic, en `hestia_core`): entradas y salidas de la etapa, con versión de esquema y unidades SI/K en los nombres de campo. TODO: ubicación y convención exacta de módulos de esquemas.
2. **Cálculo en `hestia_core`**: función pura, sin I/O. Si necesita una herramienta externa, definí un Protocol en core e implementalo en `hestia_adapters`. Validá con la skill `physics-validation`.
3. **Registro en `hestia_project`**: declarar entradas, salidas, dependencias aguas arriba (incluidas transferencias entre fases) y cómo se propaga `outdated`. TODO: API de registro de etapas (aún no existe).
4. **Operación en la API** (`hestia_api`): skill `add-api-operation`. Escrituras con autor + justificación.
5. **Tool MCP**: de grano grueso (ej. "correr la etapa y devolver resultados"), incluida en `add-api-operation`.
6. **Vista web**: consume el cliente generado; muestra estado, procedencia y resultados (°C en UI). Sin lógica.
7. **Tests por capa**: core (referencia), project (dependencias/estados), api (contrato), mcp (mapeo a la API).

Al terminar: `make test && make lint`, y pedí revisión a `physics-reviewer`, `architecture-guardian` y `parity-checker`.
