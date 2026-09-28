<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# web

Interfaz de Hestia: Next.js (App Router), TypeScript estricto, Tailwind, pnpm.

## Reglas

- Next.js es solo interfaz. Prohibido poner lógica de dominio en API routes, route handlers o server actions. Como mucho, proxy transparente hacia FastAPI.
- Consumir la API solo mediante el cliente TS generado desde `shared/openapi.json` (`make contract`). Nada de `fetch` a mano contra endpoints de negocio. TODO: elegir generador (openapi-typescript, orval o hey-api) vía ADR.
- La web no calcula resultados físicos ni decide estados del workflow: los muestra.
- Temperaturas: la API entrega Kelvin; la UI muestra °C. Convertir solo en la capa de presentación.
- Eventos en tiempo real desde FastAPI. TODO: SSE o WebSocket (decidir vía ADR). La UI debe reflejar cambios de otros actores (humanos o agentes) sin recargar.
- Humano y agente se muestran igual en historial y autoría.
- Toda acción de escritura pide justificación.

## Comandos (desde `web/`)

```sh
pnpm install
pnpm dev          # http://localhost:3000
pnpm lint         # eslint
pnpm typecheck
pnpm format:check # prettier
pnpm build
```

## Librerías previstas (no instaladas)

React Flow (grafo del workflow), Plotly (gráficos), generador de cliente OpenAPI.
