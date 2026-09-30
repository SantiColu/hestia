# app

Interfaz de Hestia: React + Vite + TanStack Router, TypeScript estricto, Tailwind v4, pnpm. Se compila a estáticos que carga el shell de escritorio (Tauri, ADR 0008); no hay servidor Node.

## Reglas

- La UI es solo interfaz. No calcula resultados físicos ni decide estados del workflow: los muestra.
- Consumir la API solo mediante `src/api/client.ts` (openapi-fetch sobre los tipos generados en `src/api/schema.gen.ts` con `make contract`, ADR 0013). Nada de `fetch` a mano contra endpoints de negocio. URL de la API: `VITE_HESTIA_API_URL` (por defecto `http://127.0.0.1:8000`).
- Temperaturas: la API entrega Kelvin; la UI muestra °C. Convertir solo en presentación.
- Eventos en tiempo real por SSE (`GET /events`, ADR 0012): ante cada evento la UI vuelve a pedir `GET /session`; así refleja cambios de otros actores (humanos o agentes) sin recargar.
- Las reglas de negocio las decide la API: destinos válidos al arrastrar o vincular (`branch-targets`, `link-targets`), opciones de ramificar (`branch-options`), cambios sin guardar (`unsaved_changes`) y lock (`project_locked`). La UI pregunta al usuario y reintenta; no deduce reglas del workflow.
- Atajos de edición (`shortcuts.ts`): nunca interceptar en campos de texto, diálogos ni menús abiertos.
- Nunca mostrar números de etapa (0.1, 1.3…): etapas y celdas van por nombre.
- Sin IA (ADR 0015): prohibido importar o depender de SDKs de IA (`ai`, `@ai-sdk/*`, `openai`, `@anthropic-ai/*`, `langchain`…); lo verifican ESLint (`no-restricted-imports`) y `scripts/check-no-ai.mjs` en `pnpm lint`.
- Humano y agente se muestran igual en historial y autoría. Toda escritura pide justificación.

## Estructura

- `src-tauri/`: shell de escritorio (Tauri 2, Rust). Solo ventana, diálogos nativos (`tauri-plugin-dialog`), portapapeles (`tauri-plugin-clipboard-manager`, leer y escribir texto) y ciclo de vida del sidecar; nada de lógica de dominio. `dragDropEnabled: false` para que funcione el drag & drop HTML5 del Toolbox. En Linux, `main.rs` define `WEBKIT_DISABLE_COMPOSITING_MODE=1` (si no está definida): con la composición acelerada WebKitGTK dibuja borroso el esquemático.
- `src/api/`: cliente de la API (`client.ts`) y tipos generados (`schema.gen.ts`, no editar).
- `src/project/`: estado del proyecto abierto (`store.tsx`, con la suscripción SSE), diálogos por promesa (`dialogs.tsx`), acciones de Archivo y deshacer/rehacer (`actions.ts`), pestañas y borradores sin aplicar (`editor.tsx`), atajos (`shortcuts.ts`), fragmentos del portapapeles (`fragment.ts`: solo reconoce el marcador; valida la API, ADR 0014) y búsquedas de solo lectura en la vista de la API (`lookup.ts`: `findCell`, `findSystem`, `stageName`).
- `src/screens/`: pantallas. `home.tsx` (inicio) y `workspace/` (barra superior, Toolbox, esquemático con React Flow, dock y panel inferior). En `workspace/`, `actions.ts` son las escrituras del esquemático (incluidos cortar, copiar, pegar y duplicar) y `edit.ts` el menú Editar y sus atajos sobre la selección.
- `src/screens/editor/`: pestaña de una celda. `cell-editor.tsx` (formulario, etapa de cálculo o «sin implementar»), `schema-form.tsx` y `schema.ts` (formulario generado desde el JSON Schema del artefacto con las extensiones `x-`, ADR 0019). Etapas de cálculo (ADR 0021): `computation-editor.tsx` (encabezado con contexto, estado y Actualizar; pestañas Parámetros, Resultados y Órbita 3D), `orbit-preview.tsx` (vista previa de la órbita del borrador junto a los parámetros, ADR 0023), `environment-results.tsx` (métricas, gráficos, rangos, condiciones y flujos por cara), `orbit-view.tsx` y `orbit-scene.tsx` (vista 3D con three.js + `@react-three/fiber`; Global/Local, play/pausa, barra de tiempo), `orbit-timeline.tsx` y `use-orbit-clock.ts` (animación de una órbita), `orbit-profile.ts` (solo interpola entre muestras de la órbita que da el backend: perfil o vista previa), `use-cell-context.ts`, `use-mission-envelope.ts` (dimensiones de la envolvente para dibujar el satélite), `format.ts` y `layout.ts`. `src/lib/units.ts`: conversión de unidades solo para mostrar (`x-unit` → `x-display-unit`); `src/lib/json.ts`: utilidades para borradores; `src/lib/format.ts`: textos (`plural`, `joinList`) y fechas (`timeFormat`, `dateFormat`, `isIsoDate`); `src/lib/utils.ts`: `cn` (con los tokens propios registrados).
- `public/brand/`: marca y logotipo (copias de `design/brand/`; si cambia la marca, volver a copiarlos).
- `src/screens/workspace/stage-icons.ts`: ícono de cada tipo de etapa (Toolbox y menús), según `workspace.pen`.
- `src/lib/native.ts`: diálogos nativos de Tauri (con `window.prompt` como respaldo en el navegador). `src/lib/clipboard.ts`: portapapeles de texto (plugin de Tauri o `navigator.clipboard`, con copia en memoria).
- `src/routes/`: rutas por archivo (TanStack Router); `src/routeTree.gen.ts` es generado, no editar. Archivos con prefijo `-` no son rutas.
- `src/components/ui/`: primitivas shadcn/ui sobre Base UI (ADR 0007). Agregar con `pnpm dlx shadcn@latest add <nombre>`; hay ajustes locales en button, switch, dialog, select y dropdown-menu. `context-menu.tsx` se escribió a mano siguiendo el de shadcn (el registro no estaba accesible).
- `src/components/{forms,feedback,navigation,data,workflow,overlays}/`: componentes de Hestia. Usarlos antes que las primitivas.
- `src/styles.css`: tokens Graphite (colores, tipografía, tracking). En shadcn `primary` = acento de Graphite; `accent` = superficie de hover.
- `eslint/tailwind.mjs`: regla local `hestia-tailwind/no-arbitrary-value` (sin valores arbitrarios de Tailwind).
- `design/`: diseño fuente en Pencil (`hestia.lib.pen` librería, `workspace.pen` pantallas). Leer `design/README.md` antes de usar el MCP de pen.dev. Catálogo en `/dev/components` (solo en desarrollo).
- Estructura de pantallas e interacciones: `docs/ux-workspace.md`.

## Estilo

- Solo tema oscuro. Sin gradientes, sombras decorativas ni glow; el color solo con significado.
- Todo lo cliqueable muestra `cursor: pointer` (regla global en `src/styles.css`).
- Números: `font-mono tabular-nums`, siempre con unidad. Datos de ejemplo solo en `/dev`.
- **Tailwind sin valores arbitrarios** (lo verifica ESLint): nada de `text-[13px]`, `w-[232px]`, `bg-[#…]`. Escala de spacing = px / 4 (`w-58`, `h-7.5`, `py-0.75`); tipografía `text-3xs` 10 · `text-2xs` 11 · `text-xs` 12 · `text-ui` 13 · `text-sm` 14 · `text-title` 15; colores solo tokens Graphite. Un token nuevo va en `@theme` (`src/styles.css`) **y** en `createCn` (`src/lib/utils.ts`).
- Clases estáticas y completas (mapas de clases para variantes); `style` solo para valores calculados en runtime.
- Detalle y resto de las reglas de código: `docs/conventions.md` («Código limpio»). Al escribir o modificar UI, skill `ui-styling`.

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

Instaladas: React Flow (`@xyflow/react`, esquemático), openapi-fetch + openapi-typescript (cliente), `@tauri-apps/api`, `@tauri-apps/plugin-dialog`, `@tauri-apps/plugin-clipboard-manager` y three.js + `@react-three/fiber` (órbita 3D de Entorno).

Previstas (no instaladas): Plotly (gráficos; hoy `components/data/line-chart.tsx` es un SVG mínimo), TanStack Table.
