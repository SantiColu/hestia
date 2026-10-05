# UX del workspace

Estructura de pantallas de la app de escritorio. Modelo de dominio: [ADR 0009](adr/0009-esquematico-de-proyecto.md). Estilo: `app/design/README.md`.

## Principios

- Basado en el **Project Schematic de Ansys Workbench**: el esquemático de sistemas y celdas es la pantalla principal.
- Todo es editable siempre (sin gates). Un cambio desactualiza lo dependiente y la UI lo muestra al instante.
- Humanos y agentes se ven igual en autoría e historial. A las personas nunca se les pide justificación (ADR 0024): las escrituras se ejecutan directo y se revierten con Deshacer.
- Denso y técnico: valores en mono con unidad, color solo con significado (estado, selección, hot/cold).

## Pantallas

### Inicio (sin proyecto abierto)

Nuevo proyecto · Abrir `.hestia` (diálogo nativo) · Proyectos recientes (nombre, ruta, última modificación).

Sin proyectos recientes (primer uso): solo Nuevo proyecto y Abrir. La marca en grande como plano de construcción (cotas, ejes, núcleo anotado) y un rótulo de plano; es la única pantalla con este tratamiento.

### Workspace (proyecto abierto)

```
┌ SAT-M1.hestia ● ───────────────────────────────────────────────────────┐
│ TOOLBOX       │ ESQUEMÁTICO                            │ PROPS|AGENTES │
│ Plantillas    │  ┌ Fase 0 · base ✎ ─┐   ┌ Fase 1 · A ✎ ┐ │ de la celda o │
│  Fase 0       │  │ Misión         ● │─┬▶│ Discretiz. ○ │ │ sistema       │
│  Fase 1       │  │ Entorno LEO600 ● │ │ │ …            │ │ seleccionado  │
│ Etapas        │  │ Balance global ◐ │ │ └──────────────┘ │               │
│  Misión       │  │ Concepto TCS   ○ │ └▶┌ Entorno · SSO800 ✎ ┐           │
│  Entorno …    │  └──────────────────┘   │ Entorno          ○ │           │
│ Post-proceso  │                         └────────────────────┘           │
│  Comparación  │                                                          │
├───────────────┴──────────────────────────────────────────┴───────────────┤
│ Mensajes · Corridas                                                      │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Barra superior:** marca · menús (**Archivo**: nuevo, abrir, recientes, guardar, guardar como, cerrar, con atajos; **Editar**: deshacer/rehacer, cortar, copiar, pegar, duplicar, renombrar, deseleccionar y eliminar; Ver, Proyecto y Ayuda deshabilitados por ahora) · nombre del archivo con el indicador de cambios sin guardar (●) y el botón guardar (solo con cambios pendientes) · herramientas futuras deshabilitadas (paleta de comandos Ctrl+K, comparar, informe, exportar a NX, Stefan) · resumen de celdas desactualizadas y Actualizar todo. Deshacer no está en la barra: vive en Editar y en Ctrl+Z.
- **Toolbox (izquierda):** árbol por fase. El encabezado de la fase (Fase 0 · Viabilidad, Fase 1 · Modelo nodal) se arrastra entero y crea el sistema con todas sus celdas vinculadas; cada etapa se arrastra sola. Sin números de etapa: son internos. Abajo, post-proceso (Comparación).
- **Esquemático (centro):** sistemas como bloques con nombre editable (✎) y filas de celdas; cada celda muestra nombre y estado (el número de etapa es interno). Vínculos como conectores ortogonales entre celdas (una salida puede ir a muchas celdas).
- **Dock derecho: Agente.** Chat con el agente conectado (Stefan u otro vía MCP), con sus cambios (autor y justificación) y corridas lanzadas. Los mensajes pasan por la API (ADR 0015).
- **Panel inferior:** mensajes y corridas en curso.

### Editor de celda

Pestañas tipo IDE bajo la barra superior (frames «Workspace · pestañas» y «Workspace · Misión (…)» en `workspace.pen`):

- **Workflow** (el esquemático) es la primera pestaña y no se cierra. Doble clic en una celda abre su pestaña (o la trae al frente). Título: celda · sistema, con el ícono de estado y un punto si hay borrador sin aplicar.
- El Toolbox solo aparece en Workflow. En una celda, el formulario ocupa el centro en una columna con scroll, sin índice de secciones. El valor aplicado se ve bajo cada campo cambiado; procedencia e historial del campo, en un popover (por diseñar).
- El dock derecho es solo el **Agente**: un chat con el agente conectado (Stefan u otro vía MCP) y sus cambios con autor y justificación. Los mensajes pasan por la API (se guardan y el agente los lee por MCP); la web no habla con ningún modelo (ADR 0015).
- Si la celda se elimina (deshacer, un agente), su pestaña se cierra con un aviso en Mensajes. Las pestañas abiertas son estado de la UI (se recuerdan por proyecto en local, no van al `.hestia`).
- Ctrl+W cierra la pestaña; Cerrar proyecto pasa a Ctrl+Shift+W.

**Edición: borrador + Aplicar.** Lo editado en la pestaña es un borrador: el backend lo valida en seco mientras se escribe (errores por campo; la UI no decide) y los campos cambiados muestran el valor aplicado. **Aplicar** aplica el borrador sin diálogo; entra como un solo cambio en el historial (un deshacer, una desactualización). Se puede aplicar con errores: en una etapa formulario la celda queda Fallida hasta corregirlos. Los agentes hacen lo mismo con una tool MCP (artefacto + justificación obligatoria). Dos niveles de «sin guardar»: el punto de la pestaña (borrador sin aplicar) y el de la barra superior (proyecto sin guardar en el archivo).

### Diálogos

Abrir/Guardar nativos · Proyecto bloqueado por otra instancia (lock) · Renombrar · Borrador sin aplicar.

## Interacciones

- Arrastrar del Toolbox al lienzo: crea un sistema (plantilla o celda suelta).
- Soltar del Toolbox **sobre una celda**: ramifica, crea lo soltado vinculado desde esa celda. Al arrastrar se resaltan solo las celdas donde el vínculo es válido.
- Clic: selecciona. Doble clic: abre la celda en su pestaña.
- Clic derecho en sistema: renombrar, agregar etapa, actualizar, cortar, copiar, pegar, duplicar, eliminar. En celda: renombrar, actualizar, ramificar, desvincular, cortar, copiar, pegar, duplicar, eliminar. El clic derecho selecciona el sistema o la celda.
- Las celdas no se mueven entre sistemas.

## Menú Editar y atajos

Mismo estilo que Archivo (ícono, etiqueta y atajo). Actúa sobre la selección, que puede tener varios sistemas y celdas: Cortar, Copiar y Eliminar toman toda la selección (un solo cambio en el historial); Duplicar y Renombrar necesitan un solo ítem. Sin selección quedan deshabilitados. Los menús contextuales de sistema y celda muestran los mismos ítems con su atajo; con clic derecho sobre un ítem de la selección, actúan sobre toda la selección.

| Ítem | Atajo | Comportamiento |
| --- | --- | --- |
| Deshacer «operación» | Ctrl+Z | La etiqueta nombra lo que revierte (`undo_label`, p. ej. «Deshacer renombrar sistema»); el resumen completo va en el tooltip. |
| Rehacer «operación» | Ctrl+Shift+Z / Ctrl+Y | Ídem con `redo_label`. |
| Cortar | Ctrl+X | Copia y elimina; si no pudo copiar, no elimina. |
| Copiar | Ctrl+C | Pide el fragmento a la API y lo deja en el portapapeles del sistema. No cambia el proyecto. |
| Pegar | Ctrl+V | Con el teclado pega donde está el cursor si está sobre el lienzo; desde el menú, desplazado respecto del original. Las celdas sueltas van al sistema seleccionado (o al de la celda seleccionada, o al del menú contextual). Deshabilitado si el portapapeles no tiene un fragmento; con el teclado, avisa en Mensajes. |
| Duplicar | Ctrl+D | Sistema: `duplicate_system` (conserva vínculos entrantes). Celda: copia y pega en su sistema. |
| Renombrar | F2 | Diálogo de renombrar del sistema o la celda. |
| Deseleccionar | Esc | Limpia la selección. |
| Eliminar | Supr | Elimina directo toda la selección (`delete_items`); se revierte con Deshacer. |

Los atajos de edición no se interceptan en campos de texto, diálogos ni menús abiertos (cortar, copiar, pegar y deshacer de texto siguen siendo nativos), ni Ctrl+C / Ctrl+X cuando hay texto seleccionado en la página. Lo pegado queda seleccionado.

### Portapapeles

Detalle en [ADR 0014](adr/0014-portapapeles-de-esquematico.md). El fragmento es JSON con el marcador `"kind": "hestia.fragment"` en el portapapeles del sistema (plugin de Tauri en el escritorio, `navigator.clipboard` en el navegador, con copia en memoria si el navegador no da permiso), así que se puede copiar en un proyecto y pegar en otro. Pegar crea ids nuevos, conserva los vínculos internos, descarta los externos, deja las celdas «nunca corrida» y es un solo cambio en el historial. Nombres repetidos reciben « (2)».

## Decisiones cerradas

- **Actividad de agentes / Stefan:** el dock derecho es solo el chat del Agente (2026-09-29; reemplaza las pestañas Propiedades/Agentes del 2026-09-28).
- **Editor de celda:** pestañas tipo IDE con Workflow fijo; edición por borrador + Aplicar (sin justificación desde 2026-10-05, ADR 0024); dock derecho solo Agente (2026-09-29; reemplaza «pantalla completa con breadcrumb» y la pestaña Propiedades del 2026-09-28).

## Estado de la implementación (2026-09-29)

Alineado con `app/design/workspace.pen` (frames Workspace, Workspace · menú Archivo, Inicio e Inicio · primer uso) y los componentes de `hestia.lib.pen`. Código en `app/src/screens/` y `app/src/project/`.

Implementado:

- **Inicio:** logotipo, Nuevo y Abrir, y recientes (archivo, carpeta, última apertura; los que ya no existen se marcan como «archivo no encontrado»; quitar de recientes aparece al pasar el mouse). Sin recientes: la marca como plano de construcción. Pie con el estado de la API y la versión.
- **Barra superior:** menú Archivo (Nuevo Ctrl+N, Abrir Ctrl+O, Recientes, Guardar Ctrl+S, Guardar como Ctrl+Shift+S, Cerrar proyecto Ctrl+Shift+W) y Editar (ver [Menú Editar y atajos](#menú-editar-y-atajos)); Ver, Proyecto y Ayuda deshabilitados; nombre del archivo, ● de cambios sin guardar y botón guardar solo con cambios; herramientas futuras y Actualizar todo visibles y deshabilitados.
- **Pestañas** (`DocTab`, `DocTab/Active`): Workflow fija; doble clic en una celda abre su pestaña (o la trae al frente) con ícono de estado, nombre de la celda, sistema y punto de acento si hay borrador sin aplicar; Ctrl+W o la ✕ la cierran (con borrador, pregunta). Se recuerdan por proyecto en `localStorage`. Si la celda desaparece, la pestaña se cierra con un aviso en Mensajes. Los atajos de edición del esquemático solo actúan en Workflow.
- **Editor de Misión** (frames «Workspace · Misión (…)»): columna centrada de 760 px con encabezado (celda, sistema y estado; «Borrador con errores» si el borrador tiene problemas) y secciones con `SectionLabel`. El formulario sale del JSON Schema del artefacto (`get_artifact_schema`, extensiones `x-` del ADR 0019): los campos consecutivos se reparten en filas de hasta 4 columnas parejas (6 → 3 + 3); los selectores y el texto libre ocupan su propia fila. Unidades de presentación (km, °, años), fecha como `aaaa-mm-dd` y hora local con `hh:mm`; caras de radiador como etiquetas en la caja y un menú para elegirlas. El borrador vive en la UI y se valida en seco con *debounce* (300 ms). Un campo cambiado lleva punto y borde de acento y debajo el valor aplicado (`Field/Number/Modified`); uno con error, borde y mensaje en rojo (`Field/Number/Error`); los defaults de biblioteca sin tocar muestran su fuente («default · ECSS-E-ST-31C»). Los errores se resumen arriba por sección («General: vida útil. Envolvente: masa.»). Con borrador (o nunca aplicado) aparece la barra inferior: punto, «N cambios sin aplicar · secciones» (o «· N errores»), Descartar y Aplicar, que aplica directo.
- **Etapa de cálculo (Entorno)** (frames «Workspace · Entorno (…)»): encabezado a todo el ancho con celda, sistema, lo que lee de su contexto («usa Misión · Fase 0 · base»), estado y Actualizar (secundario); debajo, pestañas subrayadas Parámetros · Resultados · Órbita 3D.
  - **Resultados:** cuatro métricas con detalle (β, eclipse máximo, irradiancia, período), un gráfico de β (nominal y envolvente) sobre la duración del eclipse con un solo eje de tiempo, y los flujos incidentes por cara con selectores compactos de condición y modo de actitud y Promedio · Pico (mín. – máx. por componente); debajo, rangos y condiciones.
  - **Órbita 3D:** barra con Global · Local, condición, modo y la ayuda de la cámara; la escena en un marco con su título y la leyenda (global) o la escala de flujo (local); la línea de tiempo con velocidad (×0.5 por defecto: una órbita por minuto) y la lectura del instante (β, sol/eclipse, cara con más flujo total). En las dos vistas se arrastra para rotar y la rueda acerca; la local orbita alrededor del satélite con la vertical local arriba. El satélite es una caja con las proporciones de la envolvente de la Misión del contexto (fuera de escala respecto de la Tierra; un cubo si faltan las dimensiones), también en la vista previa. La local rotula los vectores (Sol, Velocidad, Nadir) y cada cara que mira a la cámara con su flujo incidente total del instante. La órbita se dibuja como arco entre muestras (interpolación de dibujo, sin física).
  - **Fallida:** el aviso con el problema, una tabla con código, campo, contexto y proveedor y, sin resultado anterior, «Sin resultado» con «Ir a Parámetros».
- **Parámetros de Entorno** (frames «Workspace · Entorno (parámetros…)», ADR 0023): mismo formulario que Misión en una columna a la izquierda, con Órbita (selector SSO · LEO/MEO · GEO con su nota al pie) y Modos de actitud (tabla editable con «Agregar modo de actitud») antes de los parámetros del cálculo. A la derecha, un panel fijo de 440 px con la **vista previa de la órbita** del borrador: modo de actitud y fecha (por defecto, la de lanzamiento), la escena de la Órbita 3D con su selector Global · Local, línea de tiempo de una órbita y lectura de β, inclinación, período y eclipse. La pide al backend con el mismo *debounce* que la validación en seco; no tiene flujos ni guarda nada. En LEO/MEO dibuja la órbita con RAAN 0° y lo dice *(propuesta)*.
- **Editor de Equipos** ([campos](etapas/equipment.md#pantalla), frame «Workspace · Equipos (borrador)»; implementación funcional, el ajuste fino contra el diseño queda pendiente): editor propio a todo el ancho, con el mismo borrador, validación en seco, resumen de errores, estado y barra inferior que Misión. Sección **Equipos**: tabla editable (nombre, cantidad, subsistema, masa, ubicación, T operativa mín/máx en °C y «N modos») con borrar fila y «Agregar equipo» (entra expandido, con un modo vacío). Cada fila se expande (chevron) a la tabla de modos del equipo (nombre y disipación en W, borrar, «Agregar modo» y la nota de Apagado) y a los límites opcionales (T no operativa mín/máx, T mínima de encendido). Las celdas cambiadas llevan borde de acento y el valor aplicado al pasar el mouse; las que tienen error, borde rojo y el mensaje, y debajo de la tabla una línea por equipo con sus errores. Los ids de los ítems nuevos los propone el editor (ADR 0025).
- **Otras etapas:** su pestaña dice «Sin implementar» y muestra el contexto resuelto y lo que falta (`missing`). En el esquemático, una celda con requisitos faltantes muestra un aviso con la lista.
- **Borradores sin aplicar:** al cerrar el proyecto, abrir o crear otro, o cerrar la ventana de escritorio, se pregunta antes de descartarlos.
- **Mensajes:** los vínculos descartados al migrar un archivo viejo aparecen como avisos.
- **Toolbox:** fases y etapas por nombre (incluye Equipos en Fase 0). Arrastrar al lienzo crea el sistema (plantilla o celda suelta) donde se suelta; soltar sobre una celda ramifica. Durante el arrastre solo se resaltan las celdas que la API (`branch-targets`) da como válidas.
- **Esquemático (React Flow):** sistemas con sus celdas, estado de cada celda como ícono y vínculos ortogonales entre sistemas (los vínculos dentro de un sistema no se dibujan: el bloque ya los expresa); control de zoom abajo a la izquierda; selección múltiple: clic selecciona uno, Ctrl/Shift + clic suma o quita, arrastrar sobre el lienzo vacío dibuja un recuadro que selecciona los sistemas que toca; el lienzo se desplaza con el botón del medio o Espacio + arrastrar; mover sistemas (los seleccionados se mueven juntos, un solo cambio con `move_systems`); vincular arrastrando de la salida (derecha) a la entrada (izquierda) de otra celda, con destinos válidos según la API (`link-targets`). Menú contextual de sistema (renombrar, agregar etapa, actualizar deshabilitado, cortar, copiar, pegar, duplicar, eliminar) y de celda (renombrar, actualizar en etapas de cálculo, ramificar con opciones de la API, desvincular, cortar, copiar, pegar, duplicar, eliminar).
- **Justificación:** la UI no la pide en ninguna escritura (ADR 0024); el historial la muestra cuando un agente la dio.
- **Errores de render:** la ruta raíz tiene `errorComponent`: un error muestra un mensaje con «Recargar» en lugar de dejar la ventana en blanco.
- **Diálogos:** cambios sin guardar (al crear, abrir, cerrar proyecto o cerrar la ventana de escritorio), proyecto bloqueado por otra instancia (cancelar o abrir de todos modos), renombrar, borrador sin aplicar.
- **Dock derecho:** pestañas Propiedades y Agentes, vacías (el chat del Agente, ADR 0018, es otra tanda).
- **Panel inferior:** Mensajes (eventos del proyecto de cualquier actor, por SSE, y errores) e Historial (autor, resumen y justificación); Corridas deshabilitada.

TODO:

- Selección múltiple (clic con Ctrl/Shift o rectángulo) y, con ella, «Seleccionar todo» (Ctrl+A) y copiar/cortar/eliminar varios a la vez. La API de copiar ya acepta listas de sistemas y celdas.
- Menú contextual del fondo del lienzo con «Pegar aquí» (hoy se pega en el cursor con Ctrl+V).
- Portapapeles en Tauri: el plugin compila (clippy) pero solo se probó en el navegador (Chromium); probar copiar entre dos ventanas en `make desktop`.
- Popover de procedencia e historial de un campo.
- Dock derecho del Agente y resumen de celdas desactualizadas en la barra superior, como en los frames de Misión (hoy el dock tiene las pestañas Propiedades y Agentes vacías).
- Equipos: alinear la pantalla con el frame «Workspace · Equipos (borrador)» de Pencil.
- Chat del Agente (canal de mensajes por la API) e indicador de agente conectado.
- Cantidad de sistemas en cada reciente (el diseño la muestra; `RecentProject` de la API no la trae).
- Encuadrar la vista cuando un agente crea un sistema fuera de la zona visible (hoy hay que usar «ajustar vista»).
- Comparación, Actualizar, Exportar a NX, informe, paleta Ctrl+K y Stefan (dependen de cálculo o de funciones futuras).
- Diálogos nativos y cierre de ventana en Tauri: compilan (clippy) pero solo se probaron en el navegador, donde el respaldo pide la ruta con `window.prompt`. Probarlos en `make desktop`.
- Sidecar de la API con puerto aleatorio + token y archivo de instancia para el MCP (ADR 0008): hoy la API corre aparte en `:8000`.

## Decisiones abiertas

- Popover de procedencia e historial de un campo (reemplaza al panel Propiedades).
- Formato del sistema de Comparación.
