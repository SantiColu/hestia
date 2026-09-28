# app

Interfaz de Hestia: React + Vite + TanStack Router, TypeScript estricto, Tailwind v4, pnpm. Se compila a estáticos que carga el shell de escritorio (Tauri, ADR 0008); no hay servidor Node.

## Reglas

- La UI es solo interfaz. No calcula resultados físicos ni decide estados del workflow: los muestra.
- Consumir la API solo mediante el cliente TS generado desde `shared/openapi.json` (`make contract`). Nada de `fetch` a mano contra endpoints de negocio. TODO: elegir generador (openapi-typescript, orval o hey-api) vía ADR.
- Temperaturas: la API entrega Kelvin; la UI muestra °C. Convertir solo en presentación.
- Eventos en tiempo real desde FastAPI. TODO: SSE o WebSocket (ADR). La UI refleja cambios de otros actores (humanos o agentes) sin recargar.
- Humano y agente se muestran igual en historial y autoría. Toda escritura pide justificación.

## Estructura

- `src-tauri/`: shell de escritorio (Tauri 2, Rust). Solo ventana, diálogos nativos y ciclo de vida del sidecar; nada de lógica de dominio.
- `src/routes/`: rutas por archivo (TanStack Router); `src/routeTree.gen.ts` es generado, no editar. Archivos con prefijo `-` no son rutas.
- `src/components/ui/`: primitivas shadcn/ui sobre Base UI (ADR 0007). Agregar con `pnpm dlx shadcn@latest add <nombre>`; hay ajustes locales en button, switch, dialog, select y dropdown-menu.
- `src/components/{forms,feedback,navigation,data,workflow,overlays}/`: componentes de Hestia. Usarlos antes que las primitivas.
- `src/styles.css`: tokens Graphite. En shadcn `primary` = acento de Graphite; `accent` = superficie de hover.
- `design/`: diseño fuente en Pencil (`hestia.lib.pen` librería, `workspace.pen` pantallas). Leer `design/README.md` antes de usar el MCP de pen.dev. Catálogo en `/dev/components` (solo en desarrollo).
- Estructura de pantallas e interacciones: `docs/ux-workspace.md`.

## Estilo

- Solo tema oscuro. Sin gradientes, sombras decorativas ni glow; el color solo con significado.
- Todo lo cliqueable muestra `cursor: pointer` (regla global en `src/styles.css`).
- Números: `font-mono tabular-nums`, siempre con unidad. Datos de ejemplo solo en `/dev`.

## Comandos (desde `app/`)

```sh
pnpm install
pnpm dev          # http://localhost:5173 (navegador)
pnpm tauri dev    # ventana nativa (arranca Vite solo)
pnpm lint
pnpm typecheck
pnpm format:check
pnpm build        # dist/
```

## Librerías previstas (no instaladas)

React Flow (grafo del workflow), Plotly (gráficos), TanStack Table, generador de cliente OpenAPI.
