# app

Interfaz de Hestia: React + Vite + TanStack Router, TypeScript estricto, Tailwind v4, pnpm. Se compila a estáticos que carga el shell de escritorio (Tauri, ADR 0008); no hay servidor Node.

## Reglas

- La UI es solo interfaz. No calcula resultados físicos ni decide estados del workflow: los muestra.
- Consumir la API solo mediante `src/api/client.ts` (openapi-fetch sobre los tipos generados en `src/api/schema.gen.ts` con `make contract`, ADR 0013). Nada de `fetch` a mano contra endpoints de negocio. URL de la API: `VITE_HESTIA_API_URL` (por defecto `http://127.0.0.1:8000`).
- Temperaturas: la API entrega Kelvin; la UI muestra °C. Convertir solo en presentación.
- Eventos en tiempo real por SSE (`GET /events`, ADR 0012): ante cada evento la UI vuelve a pedir `GET /session`; así refleja cambios de otros actores (humanos o agentes) sin recargar.
- Las reglas de negocio las decide la API: destinos válidos al arrastrar o vincular (`branch-targets`, `link-targets`), opciones de ramificar (`branch-options`), cambios sin guardar (`unsaved_changes`) y lock (`project_locked`). La UI pregunta al usuario y reintenta; no deduce reglas del workflow.
- Nunca mostrar números de etapa (0.1, 1.3…): etapas y celdas van por nombre.
- Humano y agente se muestran igual en historial y autoría. Toda escritura pide justificación.

## Estructura

- `src-tauri/`: shell de escritorio (Tauri 2, Rust). Solo ventana, diálogos nativos (`tauri-plugin-dialog`) y ciclo de vida del sidecar; nada de lógica de dominio. `dragDropEnabled: false` para que funcione el drag & drop HTML5 del Toolbox.
- `src/api/`: cliente de la API (`client.ts`) y tipos generados (`schema.gen.ts`, no editar).
- `src/project/`: estado del proyecto abierto (`store.tsx`, con la suscripción SSE), diálogos por promesa (`dialogs.tsx`), acciones de Archivo/Editar (`actions.ts`) y atajos (`shortcuts.ts`).
- `src/screens/`: pantallas. `home.tsx` (inicio) y `workspace/` (barra superior, Toolbox, esquemático con React Flow, dock y panel inferior).
- `src/lib/native.ts`: diálogos nativos de Tauri (con `window.prompt` como respaldo en el navegador).
- `src/routes/`: rutas por archivo (TanStack Router); `src/routeTree.gen.ts` es generado, no editar. Archivos con prefijo `-` no son rutas.
- `src/components/ui/`: primitivas shadcn/ui sobre Base UI (ADR 0007). Agregar con `pnpm dlx shadcn@latest add <nombre>`; hay ajustes locales en button, switch, dialog, select y dropdown-menu. `context-menu.tsx` se escribió a mano siguiendo el de shadcn (el registro no estaba accesible).
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

## Librerías

Instaladas: React Flow (`@xyflow/react`, esquemático), openapi-fetch + openapi-typescript (cliente), `@tauri-apps/api` y `@tauri-apps/plugin-dialog`.

Previstas (no instaladas): Plotly (gráficos), TanStack Table.
