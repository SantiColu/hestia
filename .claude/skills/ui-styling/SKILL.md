---
name: ui-styling
description: Cómo escribir o modificar UI en app/ con Tailwind v4 y los componentes de Hestia — escala de spacing, tokens de tipografía y color de Graphite, sin valores arbitrarios, cuándo agregar un token, qué componente reutilizar. Usala antes de escribir o cambiar clases de Tailwind, un componente o una pantalla, y al pasar un diseño de Pencil a código.
---

# UI y estilos (app/)

Reglas completas: `docs/conventions.md` («Web» y «Tailwind»). Estilo visual: `app/AGENTS.md` («Estilo») y `app/design/README.md`. El diseño en Pencil es la fuente de verdad: el código sigue al `.pen`, no al revés.

## 1. Reutilizar antes de escribir

Buscá en este orden y usá lo primero que sirva:

1. Componentes de Hestia: `src/components/{forms,feedback,navigation,data,workflow,overlays}/` (`TextField`, `NumberField`, `SelectField`, `Segmented`, `Notice`, `StageStatusBadge`, `Tag`, `SectionLabel`, `PanelTabs`, `EmptyState`, `KeyValue`, `HistoryItem`, `ConfirmChangeDialog`…). Catálogo vivo en `/dev/components` (`pnpm dev`).
2. Primitivas shadcn de `src/components/ui/` (`Button`, `DropdownMenu`, `ContextMenu`, `Dialog`…).
3. Recién entonces, HTML con clases. Si el patrón aparece en el diseño como componente de la librería (`hestia.lib.pen`), creá el componente en `src/components/<grupo>/` y sumalo al catálogo `/dev`.

Helpers que ya existen (no reescribirlos): `cn` (`@/lib/utils`), `plural`/`joinList`/`timeFormat`/`dateFormat` (`@/lib/format`), `findCell`/`findSystem`/`stageName` (`@/project/lookup`), `isApiError` (`@/api/client`), `toDisplay`/`fromDisplay` (`@/lib/units`).

## 2. Traducir medidas del diseño

Pencil da px. Nunca `-[Npx]`: convertí a la escala (px / 4; Tailwind v4 acepta múltiplos de 0.25).

| px del diseño | clase | px | clase | px | clase |
|---|---|---|---|---|---|
| 1 | `-px` / `w-px` | 18 | `4.5` | 104 | `26` |
| 3 | `0.75` | 21 | `5.25` | 168 | `42` |
| 6 | `1.5` | 30 | `7.5` | 232 | `58` |
| 9 | `2.25` | 37 | `9.25` | 340 | `85` |
| 10 | `2.5` | 52 | `13` | 480 | `120` |
| 14 | `3.5` | 76 | `19` | 760 | `190` |

Ejemplos: `w-[232px]` → `w-58`; `h-[30px]` → `h-7.5`; `py-[3px]` → `py-0.75`; `after:bottom-[-1px]` → `after:-bottom-px`; `sm:max-w-[480px]` → `sm:max-w-120`.

## 3. Tipografía, color y radio: solo tokens

| Diseño | Clase |
|---|---|
| 10 px | `text-3xs` |
| 11 px | `text-2xs` |
| 12 px | `text-xs` |
| 13 px (texto base de la UI) | `text-ui` |
| 14 px | `text-sm` |
| 15 px | `text-title` |
| 18 / 24 / 30 px | `text-lg` / `text-2xl` / `text-3xl` |
| letter-spacing de SectionLabel (0.08em) | `tracking-label` |

- Colores Graphite (`src/styles.css`): superficies `bg-background`, `bg-surface`, `bg-surface-2`; bordes `border-border`, `border-border-strong`; texto `text-foreground`, `text-muted-foreground`, `text-subtle-foreground`; acento `primary`/`primary-soft`; estados `ok`, `warn`, `error`, `idle` (+ `-soft`); casos `hot`, `cold`. Nunca hex ni la paleta de Tailwind (`zinc`, `slate`…). El color solo con significado.
- Radio: `rounded-lg` (= `$radius` 4 px del diseño), `rounded-md`, `rounded-full` para puntos.
- Números: `font-mono tabular-nums` y siempre con unidad.

## 4. Si falta un token

Solo si el valor se repite y es parte del sistema (no para un caso aislado; ahí usá el paso de escala más cercano):

1. Agregalo en `@theme inline` de `src/styles.css` con comentario (`--text-foo: 0.8125rem; /* 13px: … */`).
2. Registralo en `createCn` de `src/lib/utils.ts` (grupo `font-size`, `tracking`, etc.). Sin esto, `cn("text-foo", "text-muted-foreground")` descarta `text-foo` porque lo toma por un color.
3. Documentalo en la tabla de arriba y en `docs/conventions.md`.

## 5. Otras reglas

- Clases estáticas y completas. Para variantes por valor, un mapa (`const ROW_GRID = ["grid-cols-1", "grid-cols-2", …]`), nunca `` `grid-cols-${n}` ``.
- `style={{…}}` solo para valores calculados en runtime (posiciones de React Flow, geometría del dibujo de inicio).
- Variantes arbitrarias (`[&>svg]:size-4`, `data-[state=open]:`) permitidas; valores arbitrarios no (ESLint `hestia-tailwind/no-arbitrary-value`).
- `!` solo para pisar estilos de librerías externas (React Flow, shadcn).
- Lo cliqueable es `button`/`a` (o tiene `role`); el cursor lo pone la regla global. Íconos decorativos con `aria-hidden`; botones de solo ícono con `aria-label` y `title`.
- Textos en español rioplatense (vos), sin números de etapa (0.1, 1.3…).
- `src/components/ui/` es shadcn vendoreado: no reescribas sus clases de origen; los ajustes locales siguen estas reglas.

## 6. Verificar

```sh
cd app && pnpm lint && pnpm typecheck && pnpm format:check
```

Y mirá la pantalla (`pnpm dev`, o `/dev/components` para componentes) contra el frame del `.pen`.
