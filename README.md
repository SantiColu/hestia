# Hestia

Herramienta de prediseño del sistema de control térmico (TCS) de satélites medianos, fases 0 (viabilidad) y 1 (dimensionamiento nodal).

- **Web** (`web/`): interfaz para el ingeniero.
- **API** (`backend/`): toda la lógica de dominio (FastAPI + paquetes Python).
- **MCP** (`mcp/`): permite a agentes de IA trabajar sobre lo mismo que la web, vía la API.

## Requisitos

- [uv](https://docs.astral.sh/uv/) (instala Python 3.12 automáticamente)
- Node.js ≥ 20 y pnpm
- GNU Make

## Inicio rápido

```sh
make setup
make dev        # API en :8000, web en :3000
make test
make lint
```

## Documentación

- [Arquitectura](docs/architecture.md)
- [Workflow fases 0 y 1](docs/workflow-fases-0-1.md)
- [Convenciones](docs/conventions.md)
- [ADRs](docs/adr/)
- Instrucciones para agentes: `AGENTS.md` (raíz y cada módulo).
