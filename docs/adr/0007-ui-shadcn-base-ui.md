# 0007. Componentes de UI: shadcn/ui sobre Base UI

- **Estado:** aceptado
- **Fecha:** 2026-09-28

## Contexto

La UI necesita un set de componentes accesibles con un lenguaje visual propio (tema Graphite, oscuro, de ingeniería; ver `app/design/`). La mayoría de las entradas son numéricas con unidad. El grafo del workflow se hará con React Flow.

## Decisión

- shadcn/ui (estilo `base-nova`) con primitivas de **Base UI** (`@base-ui/react`), sobre Tailwind v4. El código de los componentes vive en el repo (`app/src/components/ui/`).
- Tokens de Graphite mapeados a las variables CSS de shadcn en `app/src/styles.css`. Solo tema oscuro.
- Componentes de Hestia en `app/src/components/<grupo>/` (forms, feedback, navigation, data, workflow, overlays), construidos sobre las primitivas.
- Campo numérico propio sobre `NumberField` de Base UI (shadcn no lo provee), con locale fijo `en-US` para valores técnicos.
- Íconos: lucide-react. Tipografías: Inter y JetBrains Mono vía `@fontsource`.

## Consecuencias

- Control total del estilo sin pelear con una librería con lenguaje visual propio.
- Compatible con los componentes de React Flow basados en shadcn.
- Las primitivas copiadas no se actualizan solas: `shadcn add --overwrite` pisa ajustes locales (button, switch, dialog, select, dropdown-menu). Revisar el diff al actualizar.
- Pendiente: TanStack Table cuando las tablas necesiten orden, filtros o virtualización.
