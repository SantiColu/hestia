# Convenciones

## Idioma

- Código, identificadores, comentarios, docstrings, mensajes de commit: **inglés**.
- Documentación (`docs/`, READMEs, `AGENTS.md`, ADRs): **español**.

## Unidades

- Internamente **SI** en todo el backend, la API y el MCP.
- Temperaturas en **Kelvin** internamente y en la API. La UI muestra **°C** (conversión solo en presentación).
- Cuando la unidad no es obvia, sufijo en el nombre: `power_w`, `area_m2`, `temperature_k`, `conductance_w_per_k`, `angle_rad`.
- Ángulos en radianes internamente salvo que un ADR diga lo contrario.

## Nombres

- Etapas: snake_case inglés (`mission`, `global_balance`, `load_cases`…). El número (0.1, 1.3…) es metadato, nunca parte del id.
- Python: PEP 8 (ruff). Paquetes `hestia_<capa>`; distribuciones `hestia-<capa>`.
- TypeScript: camelCase para variables, PascalCase para componentes y tipos.

## Artefactos y contrato

- Todo artefacto tiene esquema versionado (campo de versión en el modelo pydantic).
- Los modelos pydantic son la fuente de verdad; OpenAPI y el cliente TS se generan.
- `shared/openapi.json` no se edita a mano.

## Cambios

- Toda escritura (UI o MCP) registra autor y justificación.
- Todo cálculo físico nuevo lleva test contra referencia citada, con tolerancia explícita.
- Decisiones de arquitectura → ADR en `docs/adr/`.

## Commits

Formato `tipo(scope): mensaje`, siempre en **inglés** y en **modo imperativo**.

- `feat(app): add stage node component` — no `added` ni `adds`.
- Scope = módulo afectado (`app`, `api`, `core`, `project`, `adapters`, `mcp`, `docs`…). Si el cambio es global, sin scope: `feat: move UI to a desktop app`.
- `fix` describe **el problema**, no lo que se hizo: `fix(api): health endpoint returns 500 when version is missing`, no `fix(api): handle missing version`.
- Otros tipos con la misma forma: `docs`, `refactor`, `test`, `chore`, `build`, `ci`.

## Estilo

- Python: ruff (lint + format), pyright strict, línea de 100.
- Web: ESLint + Prettier, TypeScript strict.
- `.editorconfig` en la raíz.

## Código limpio

Reglas para humanos y agentes. Lo verificable lo hace cumplir `make lint`; el resto se revisa con la skill `clean-code-review` antes de dar un cambio por terminado. Un cambio no está terminado si `make lint` o `make test` fallan.

### General

- **Una sola fuente de verdad.** Antes de escribir un helper, buscá si ya existe (`rg`). Dos funciones que hacen lo mismo con otro nombre son un bug esperando pasar (p. ej. `listNames` y `joinList`). Si la lógica se repite dos veces, extraela; a la tercera es obligatorio.
- **Nombres que dicen qué es**, no cómo se usa: `findCell`, `applySummary`, `MAX_NAMED_CELLS`. Sin abreviaturas crípticas salvo las idiomáticas (`id`, `i`, `p` en lambdas cortas). Booleanos como afirmación: `is_open`, `canPaste`, `modified`.
- **Sin números mágicos**: constante con nombre y unidad (`VALIDATE_DEBOUNCE_MS = 300`, `MIN_ALTITUDE_M`). Los literales de diseño en la UI van como tokens (ver «Tailwind»).
- **Funciones cortas y de un nivel de abstracción.** Si un componente o función pasa de ~150 líneas o mezcla orquestación con detalle, partilo (subcomponente, helper puro).
- **Sin código muerto**: nada comentado, sin componentes o funciones que nadie usa, sin `TODO` que ya se puede resolver. Un `TODO` explica qué falta y por qué no se hace ahora.
- **Comentarios que explican el porqué** (decisión, ADR, restricción), no el qué. Docstring/JSDoc de una línea en toda función o componente exportado que no sea obvio.
- **Supresiones con motivo**: todo `eslint-disable`, `# noqa`, `# type: ignore` o `# pyright: ignore` lleva la regla y el motivo (`-- reason`). Sin motivo, no se acepta.
- **Errores explícitos**: nunca tragar excepciones en silencio salvo que un comentario diga por qué es seguro (p. ej. recordar pestañas es una comodidad).
- **Alcance**: un cambio hace lo que pide; los refactors oportunistas van aparte o se mencionan.

### Python

- Tipos completos en toda firma (pyright strict). Nada de `Any` salvo en bordes JSON con comentario.
- Modelos de datos con pydantic (`hestia_project.base.Schema` si los expone la API); enums como `StrEnum`.
- Errores de dominio como subclases con `code` estable (`hestia_project.errors`); nunca `raise Exception`.
- Funciones puras en `hestia_core`; efectos (I/O, reloj, azar) inyectados o en capas externas.
- `pathlib` en vez de `os.path`/`os.replace`; `datetime` siempre con zona (`UTC`); sin `print` (ruff `T20`).
- Constantes de módulo en MAYÚSCULAS con docstring de una línea debajo cuando no son obvias.
- Tests: un comportamiento por test, nombre que lo describe (`test_link_rejects_cycle`), sin parámetros o fixtures sin usar.

### Web (React + TypeScript)

- **Tipos del contrato**: usar los de `@/api/client` (generados). Nunca redefinir a mano un tipo que existe en el contrato; nada de `as never`, `any` ni `!` (non-null). Un `as unknown as T` solo en un helper con nombre y comentario que diga por qué.
- `type` para tipos (no `interface`, salvo declaration merging); `import { x, type T }` inline.
- **Componentes**: uno por responsabilidad; los de más de ~150 líneas se parten. Props tipadas con `type XProps`. Nada de funciones declaradas después del `return`.
- **Reutilizar antes de crear**: primero `src/components/{forms,feedback,navigation,data,workflow,overlays}/`, después las primitivas de `src/components/ui/`, y recién después un elemento HTML con clases.
- **Helpers compartidos**: formato de texto y fechas en `src/lib/format.ts` (`plural`, `joinList`, `timeFormat`); búsquedas en el proyecto en `src/project/lookup.ts` (`findCell`, `findSystem`, `stageName`); errores de la API con `isApiError(error, code)`. No duplicarlos en pantallas.
- **Estado**: derivar en render lo que se puede derivar; `useMemo`/`useCallback` solo cuando la identidad importa (props de componentes memo, dependencias de efectos, contextos). Efectos solo para sincronizar con algo externo (API, DOM, storage), con limpieza.
- **Orden de imports**: React y paquetes externos → alias `@/` → relativos (`./`).
- Textos de la UI en español rioplatense (vos), sin números de etapa.

### Tailwind (v4)

- **Nunca valores arbitrarios** (`text-[13px]`, `w-[232px]`, `bg-[#1d222a]`, `[mask-type:x]`). Lo verifica la regla `hestia-tailwind/no-arbitrary-value` de ESLint (`app/eslint/tailwind.mjs`).
  - Tamaños y espacios: la escala de spacing es px / 4 y acepta múltiplos de 0.25 → `w-58` (232 px), `h-7.5` (30 px), `py-0.75` (3 px), `max-w-190` (760 px), `-bottom-px` (−1 px).
  - Tipografía: `text-3xs` (10), `text-2xs` (11), `text-xs` (12), `text-ui` (13), `text-sm` (14), `text-title` (15), `text-lg` (18)… Tracking: `tracking-label` (etiquetas de sección).
  - Colores: solo los tokens de Graphite (`bg-surface`, `text-subtle-foreground`, `border-border-strong`, `text-warn`…). Nunca hex ni colores de la paleta de Tailwind (`bg-zinc-800`).
  - Un valor que falta y se repite se agrega como token en `@theme` de `src/styles.css` **y** se registra en `src/lib/utils.ts` (si no, `cn` lo confunde con un color y lo descarta al combinar clases).
- Las variantes arbitrarias (`[&>svg]:size-4`, `data-[state=open]:`) sí se permiten: seleccionan, no inventan valores.
- Clases completas y estáticas: nada de construirlas con strings (`` `w-${n}` ``). Para variantes por valor, un mapa de clases (`ROW_GRID = ["grid-cols-1", …]`).
- `style={{…}}` solo para valores calculados en runtime que no son clases (posición de React Flow, geometría del dibujo de inicio). Nunca para colores o tamaños fijos.
- Combinar clases siempre con `cn()`. El `!` (important) solo para pisar estilos de una librería externa (React Flow, shadcn), con comentario si no es obvio.
- `src/components/ui/` es shadcn vendoreado: sus valores arbitrarios de origen se dejan; los ajustes locales siguen estas reglas.
