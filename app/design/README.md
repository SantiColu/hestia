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
- En archivos que importan la librería, los ids internos de una instancia `lib:` llevan el prefijo en cada segmento: `instancia/lib:<idHijo>`, tanto en `Update`/`Replace` como en las claves de `descendants`. Sin prefijo el override se ignora sin error.
- Los visitantes de `Get` sobre todo el documento también recorren los nodos de la librería importada (`lib:…`). Un `Get` de un id inexistente aborta el `execute` aunque esté dentro de `try`. Como guarda, listar los ids de primer nivel (`Get((n,c)=>{c.skipChildren();return n.id})`) y comprobar que esté el frame propio esperado.
- `Export` dentro del mismo `execute` que hizo cambios puede salir desactualizado; exportar en una llamada aparte.
- Si el MCP responde «A file needs to be open in the editor» con el archivo abierto, el servidor MCP probablemente apunta a otra app (p. ej. `--app visual_studio_code`) o a un montaje viejo del AppImage: abrir pen.dev antes de iniciar Claude Code, o reconectar con `/mcp`.

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
| Workflow   | `SystemBlock`, `SystemCell`, `SystemCell/{Selected,Outdated,DropTarget}`, `Link/{Straight,Elbow}`, `ToolboxGroup`, `ToolboxItem`, `ToolboxItem/Hover`, `HistoryItem`, `ProvenanceRow` |
| Overlays   | `Menu`, `MenuItem`, `MenuItem/Danger`, `MenuDivider`, `Dialog` (confirmación con justificación)                                 |
| Brand      | `Brand/Mark`, `Brand/Logo`, `Brand/Icon` (32 px, ajustado al píxel, para tamaños < 24 px)                                       |

**Esquemático** (ADR 0009):

- `SystemBlock`: encabezado con nombre y acciones renombrar (✎) y menú; cuerpo `Cells` es un slot de `SystemCell`.
- `SystemCell`: nombre e ícono de estado. El número de etapa es interno: `Number` va oculto (`enabled: false`). Estado por override del ícono `State`: `circle-check` + `$ok` (actualizada), `refresh-cw` + `$warn` (desactualizada), `circle-x` + `$error` (fallida), `circle-dashed` + `$idle` (nunca corrida). Variantes `Selected`, `Outdated` y `DropTarget` (destino válido al arrastrar desde el Toolbox: borde `$accent`, ícono `git-branch-plus`).
- `Link/Straight` y `Link/Elbow`: vínculo ortogonal con flecha, color `$text-subtle` (override a `$accent` para los vínculos de la selección). `Link/Elbow` baja hacia la derecha; para subir, `flipY`. Se estira con width/height.
- `ToolboxGroup`: fase del Toolbox. Encabezado (chevron, ícono, nombre, descripción, agarre oculto) y cuerpo `Stages`, slot de `ToolboxItem` con guía vertical. Se arrastra la fase entera desde el encabezado o una etapa sola.
- `ToolboxItem`: ícono y etiqueta (sin número de etapa). `Meta` y `Grip` ocultos; `ToolboxItem/Hover` muestra fondo y agarre.

**Brand**: paths nativos con la geometría de `brand/` y los tokens `$text` y `$hot` (pen.dev no renderiza SVG como relleno de imagen). Para escalar una instancia, sobrescribir `width`/`height` de la instancia y de cada path hijo con el mismo valor, manteniendo la proporción (marca 88 × 100, logotipo 387.97 × 102.35). Si cambia la marca en `brand/build.py`, actualizar estos paths. Reglas de uso en `brand/README.md`.

Implementación en código: `app/src/components/` (ver `app/AGENTS.md` y ADR 0007).

Convenciones de uso:

- Deshabilitado (funciones futuras): `opacity: 0.4` en la instancia; en menús, atajo reemplazado por «pronto».

- Toda acción de escritura pasa por `Field/Justification` (principio 7: autor + justificación).
- Humano y agente se muestran igual en `HistoryItem`.
