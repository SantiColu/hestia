# Hestia

Prediseño del sistema de control térmico (TCS) de satélites medianos: fase 0 (viabilidad) y fase 1 (dimensionamiento nodal). Fases posteriores (GMM/TMM detallado, ensayos) se hacen en Siemens NX: fuera de alcance.

Aplicación de escritorio local (ADR 0008): cada proyecto es un archivo `.hestia`. Humanos primero (UI). Agentes de IA trabajan como pares vía MCP. El agente integrado futuro (Stefan) es un cliente más del MCP/API.

## Principios (no negociables)

1. La lógica de dominio vive solo en el backend Python (FastAPI). La UI (React) es interfaz: nunca decide negocio.
2. El servidor MCP es un cliente HTTP de la API REST. No importa código del backend.
3. Paridad humano-agente: toda operación de la UI existe como tool MCP y viceversa.
4. Los agentes nunca calculan números por su cuenta. Todo resultado físico sale de `hestia_core` (determinístico, testeado).
5. Un solo contrato: modelos pydantic → OpenAPI (`shared/openapi.json`) → cliente TS de la UI y tools MCP.
6. Esquemático tipo Ansys Workbench (ADR 0009): celdas (etapas instanciadas) agrupadas en sistemas y conectadas por vínculos tipados. Cada celda tiene estado (actualizada / desactualizada / fallida / nunca corrida) y procedencia. Un cambio aguas arriba desactualiza lo dependiente. Sin gates: todo es editable.
7. Todo cambio tiene autor (humano o agente) y justificación, con historial y deshacer.
8. Hestia no depende de IA (ADR 0015): backend y web no usan SDKs ni frameworks de IA; los agentes son actores externos vía MCP → API. Lo verifican `make lint` y `make test`.

## Módulos

- `backend/` — uv workspace Python 3.12: `hestia_core` (física pura), `hestia_project` (workflow, estados, historial), `hestia_adapters` (Orekit, pyViewFactor, SciPy), `hestia_api` (FastAPI).
- `mcp/` — servidor MCP, proyecto uv independiente; solo HTTP contra la API.
- `app/` — UI: React + Vite + TanStack Router, TypeScript estricto, Tailwind, shadcn/Base UI, pnpm. Shell de escritorio: Tauri 2 en `app/src-tauri/`.
- `shared/` — contrato OpenAPI generado. No editar a mano.
- `scripts/` — exportar OpenAPI y generar cliente TS.
- `docs/` — arquitectura, workflow, convenciones, ADRs.

## Comandos (`make help`)

- `make setup` — instala dependencias de los tres proyectos.
- `make dev` — levanta API (:8000) y UI (:5173) en el navegador.
- `make desktop` — levanta API y la app de escritorio (Tauri).
- `make test` — pytest en backend y mcp.
- `make lint` — ruff, pyright, import-linter, eslint, prettier.
- `make contract` — regenera `shared/openapi.json` y el cliente TS.

## Convenciones

- Código, identificadores y comentarios en inglés. Documentación en español.
- Unidades SI internamente; temperaturas en Kelvin. La UI muestra °C.
- Etapas en snake_case inglés (`global_balance`, `load_cases`) con su número (0.3, 1.3) como metadato.
- Todo artefacto tiene esquema versionado.
- Decisiones de arquitectura nuevas → ADR en `docs/adr/` (skill `write-adr`).
- Commits: `tipo(scope): message` en inglés e imperativo (`feat(app): add x`); global sin scope (`feat: x`); `fix` describe el problema. Ver `docs/conventions.md`.

## Más contexto

`docs/architecture.md`, `docs/workflow-fases-0-1.md`, `docs/ux-workspace.md`, `docs/conventions.md`, `docs/adr/`. Cada módulo tiene su propio `AGENTS.md`.
