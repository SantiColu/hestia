# Arquitectura

## Principios

1. **Dominio solo en el backend.** Toda regla de negocio y todo cálculo físico viven en Python (FastAPI y paquetes `hestia_*`). La UI (React) es interfaz; nunca decide.
2. **MCP es cliente de la API.** No importa código del backend. Un agente no puede hacer nada que la API no permita.
3. **Paridad humano-agente.** Toda operación de lectura/escritura de la UI existe como tool MCP y viceversa.
4. **Los agentes no calculan.** Todo número físico sale de `hestia_core`, determinístico y testeado.
5. **Un solo contrato.** pydantic → OpenAPI (`shared/openapi.json`) → cliente TS (UI) y tools (MCP).
6. **Esquemático tipo Workbench.** Celdas (etapas instanciadas) agrupadas en sistemas y conectadas por vínculos tipados, con estado y procedencia; cambios aguas arriba desactualizan lo dependiente. Sin gates: todo es editable. Ver [ADR 0009](adr/0009-esquematico-de-proyecto.md) y [workflow-fases-0-1.md](workflow-fases-0-1.md).
7. **Autoría y justificación.** Todo cambio registra autor (humano o agente, sin distinción en la UI) y justificación, con historial y deshacer.

## Capas

```
            ┌──────────────┐     ┌──────────────┐     ┌────────────────────┐
 humanos ──▶│  UI (React)  │     │  mcp (Python)│◀──  │ agentes (Stefan,   │
            └──────┬───────┘     └──────┬───────┘     │ externos)          │
                   │ cliente TS         │ httpx       └────────────────────┘
                   │ generado           │
                   ▼                    ▼
            ┌────────────────────────────────────┐
            │  hestia_api (FastAPI) — REST + eventos
            └──────┬──────────────┬──────────────┘
                   ▼              ▼
          ┌────────────────┐ ┌─────────────────┐
          │ hestia_project │ │ hestia_adapters │
          │ workflow,      │ │ Orekit, pyVF,   │
          │ estado, historial │ SciPy…        │
          └───────┬────────┘ └────────┬────────┘
                  ▼                   ▼
            ┌────────────────────────────────────┐
            │ hestia_core — física pura, modelos, Protocols
            └────────────────────────────────────┘
```

## Reglas de dependencia

| Módulo | Puede depender de |
|---|---|
| `hestia_core` | ningún paquete de Hestia (define Protocols de proveedores externos) |
| `hestia_adapters` | `hestia_core` |
| `hestia_project` | `hestia_core` |
| `hestia_api` | todos los anteriores |
| `hestia_mcp` | solo HTTP contra `hestia_api` |
| `app` (UI) | solo la API, vía cliente generado |

Las reglas del backend se verifican con import-linter (`backend/pyproject.toml`). El resto lo revisan los subagentes `architecture-guardian` y `parity-checker`.

## Despliegue: app de escritorio (ADR 0008)

- Shell Tauri que carga la UI estática (`app/dist`) y lanza la API como sidecar en `127.0.0.1` (puerto aleatorio + token).
- El MCP se conecta a esa API local; descubre puerto y token por un archivo de instancia.

## Persistencia (prevista, no implementada)

El backend es dueño del estado. Cada proyecto es **un archivo SQLite** (`.hestia`) con entradas, artefactos, resultados y log de cambios (autor, justificación, timestamp, diff) que soporta historial y deshacer. Abrir / Guardar / Guardar como, como en Ansys o Pencil. Git sirve para exportar snapshots, no como almacenamiento primario. Ver [ADR 0006](adr/0006-estado-en-backend-sqlite.md) y [ADR 0008](adr/0008-app-escritorio-proyecto-archivo.md).

## Pendientes de decisión

- Generador del cliente TS (openapi-typescript, orval o hey-api).
- Canal de eventos en tiempo real (SSE o WebSocket).
- Cómo el MCP deriva/valida tipos desde `shared/openapi.json`.
- Test automático de paridad API ↔ MCP ↔ UI.
- Empaquetado del sidecar Python + JRE (Orekit) y formato interno del archivo `.hestia`.
