# Hestia

Herramienta de prediseño del sistema de control térmico (TCS) de satélites medianos, fases 0 (viabilidad) y 1 (dimensionamiento nodal).

- **UI** (`app/`): interfaz para el ingeniero (app de escritorio; cada proyecto es un archivo local).
- **API** (`backend/`): toda la lógica de dominio (FastAPI + paquetes Python).
- **MCP** (`mcp/`): permite a agentes de IA trabajar sobre lo mismo que la UI, vía la API.

## Requisitos

- [uv](https://docs.astral.sh/uv/) (instala Python 3.12 automáticamente)
- Node.js ≥ 20 y pnpm
- Rust (vía [rustup](https://rustup.rs)) y las dependencias de sistema de [Tauri](https://tauri.app/start/prerequisites/)
- GNU Make

## Inicio rápido

```sh
make setup
make dev        # API en :8000, UI en :5173 (navegador)
make desktop    # API + app de escritorio
make test
make lint
```

## Documentación

- [Arquitectura](docs/architecture.md)
- [Workflow fases 0 y 1](docs/workflow-fases-0-1.md)
- [Convenciones](docs/conventions.md)
- [ADRs](docs/adr/)
- Instrucciones para agentes: `AGENTS.md` (raíz y cada módulo).
