# Diseños (pen.dev)

Pantallas y componentes de la UI de Hestia en [pen.dev](https://docs.pencil.dev). Los `.pen` se versionan con el código y se revisan en el mismo PR que la feature.

## Estructura

- `hestia.lib.pen`: librería con tokens (tema **Graphite**, oscuro) y componentes base. Todas las pantallas la importan con el alias `lib`.
- `workspace.pen`: pantalla principal (inicio y workspace con esquemático). Importa la librería como `lib`. Estructura en `docs/ux-workspace.md`.
- Pantallas: un `.pen` por área o feature, no uno por ruta ni uno para toda la app. Cada pantalla y cada estado relevante es un frame.

## Reglas

- pen.dev no guarda automáticamente: guardar (Ctrl+S) antes de commitear.
- Importar la librería con alias `lib`; referenciar componentes como `lib:<id>` y variables como `$lib:<token>`.
- Después de cambiar y guardar la librería, cerrar y reabrir los archivos que la importan.
- Todo lo que se repite se hace con componentes de la librería, no con copias.

## Notas para agentes (MCP de pen.dev)

- Si el `filePath` pedido no está abierto en pen.dev, el MCP opera **sobre el archivo activo** (puede ser de otro proyecto). Antes de escribir: `get_app_state` y confirmar que el archivo activo es el correcto; en cada `execute`, abortar (`throw`) si no se encuentra un nodo o variable propio del archivo.
- Los `.pen` son JSON. Un archivo nuevo se puede crear en disco (`{"version":"2.19","imports":{...},"children":[]}`), pero hay que abrirlo en pen.dev antes de editarlo.
- `TakeScreenshot` suele mostrar un estado viejo o vacío; verificar con `Export` a PNG (a una carpeta temporal) y con `Get` + `ctx.problems`.
- `Replace` sobre un componente le cambia el id y desconecta sus instancias; preferir `Update`. `Copy` de un componente crea una instancia, no otro componente.
- Pedirle al usuario que guarde (Ctrl+S) al terminar: pen.dev no guarda solo.

## Estilo

Oscuro, minimalista, de ingeniería. Sin gradientes, glow ni decoración. El color solo tiene significado: acción primaria/selección (`accent`), estado de etapa (`ok`, `warn`, `error`, `idle`) y casos térmicos (`hot`, `cold`).

- Tipografía: Inter (`$font-sans`) y JetBrains Mono (`$font-mono`) para valores numéricos, unidades, ids de etapa y etiquetas de sección.
- Radio: `$radius` = 4.
- Valores numéricos siempre con unidad; internamente SI/K, la UI muestra °C.

## Componentes

| Grupo      | Componentes                                                                                                                     |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Buttons    | `Button/{Primary,Secondary,Ghost,Danger,Icon}` y variantes `/sm`                                                                |
| Forms      | `Field/{Number,Number/Error,Select,Text,Justification}`, `Checkbox/{On,Off}`, `Toggle/{On,Off}`, `Segment/{Active,Default}`     |
| Feedback   | `Status/{UpToDate,Outdated,Failed,NeverRun,Running}`, `Tag/{Hot,Cold,Neutral}`, `Alert/{Info,Warning,Error,Success}`, `Tooltip` |
| Navigation | `Tab/{Active,Default}`, `SectionLabel`, `NavItem`, `NavItem/Active`, `Breadcrumb`                                               |
| Data       | `Table/{HeaderCell,Cell}`, `Metric`, `KeyValue`, `Avatar`, `EmptyState`                                                         |
| Workflow   | `StageNode` (a reemplazar), `HistoryItem`, `ProvenanceRow`                                                                      |
| Overlays   | `Menu`, `MenuItem`, `MenuItem/Danger`, `MenuDivider`, `Dialog` (confirmación con justificación)                                 |

**Pendiente en la librería** (esquemático, ADR 0009):

- Quitar el componente `Gate` (sin gates por ahora).
- Agregar `SystemBlock` (encabezado: nombre editable ✎ + menú; cuerpo: slot de celdas), `SystemCell` (número mono, nombre, indicador de estado; variantes seleccionada y desactualizada), conector/vínculo ortogonal con flecha y `ToolboxItem`.
- `StageNode` se reemplaza por `SystemBlock` + `SystemCell`.

Implementación en código: `app/src/components/` (ver `app/AGENTS.md` y ADR 0007).

Convenciones de uso:

- `StageNode` seleccionado: override `stroke: $accent`, `strokeWidth: 1.5`.
- Toda acción de escritura pasa por `Field/Justification` (principio 7: autor + justificación).
- Humano y agente se muestran igual en `HistoryItem`.
