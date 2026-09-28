# Arquitectura

## Principios

1. **Dominio solo en el backend.** Toda regla de negocio y todo cálculo físico viven en Python (FastAPI y paquetes `hestia_*`). Next.js es interfaz; puede hacer de proxy, nunca decide.
2. **MCP es cliente de la API.** No importa código del backend. Un agente no puede hacer nada que la API no permita.
3. **Paridad humano-agente.** Toda operación de lectura/escritura de la web existe como tool MCP y viceversa.
4. **Los agentes no calculan.** Todo número físico sale de `hestia_core`, determinístico y testeado.
5. **Un solo contrato.** pydantic → OpenAPI (`shared/openapi.json`) → cliente TS (web) y tools (MCP).
6. **Workflow tipo Workbench.** Grafo de etapas con entradas/salidas tipadas, estado y procedencia; cambios aguas arriba desactualizan lo dependiente. Ver [workflow-fases-0-1.md](workflow-fases-0-1.md).
7. **Autoría y justificación.** Todo cambio registra autor (humano o agente, sin distinción en la UI) y justificación, con historial y deshacer.

## Capas

```
            ┌──────────────┐     ┌──────────────┐     ┌────────────────────┐
 humanos ──▶│  web (Next)  │     │  mcp (Python)│◀──  │ agentes (Stefan,   │
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
| `web` | solo la API, vía cliente generado |

Las reglas del backend se verifican con import-linter (`backend/pyproject.toml`). El resto lo revisan los subagentes `architecture-guardian` y `parity-checker`.

## Persistencia (prevista, no implementada)

El backend es dueño del estado: SQLite + log de cambios (autor, justificación, timestamp, diff) que soporta historial y deshacer. Git sirve para exportar snapshots del proyecto, no como almacenamiento primario. Ver [ADR 0006](adr/0006-estado-en-backend-sqlite.md).

## Pendientes de decisión

- Generador del cliente TS (openapi-typescript, orval o hey-api).
- Canal de eventos en tiempo real (SSE o WebSocket).
- Cómo el MCP deriva/valida tipos desde `shared/openapi.json`.
- Test automático de paridad API ↔ MCP ↔ web.
