# UX del workspace

Estructura de pantallas de la app de escritorio. Modelo de dominio: [ADR 0009](adr/0009-esquematico-de-proyecto.md). Estilo: `app/design/README.md`.

## Principios

- Basado en el **Project Schematic de Ansys Workbench**: el esquemático de sistemas y celdas es la pantalla principal.
- Todo es editable siempre (sin gates). Un cambio desactualiza lo dependiente y la UI lo muestra al instante.
- Humanos y agentes se ven igual en autoría e historial. Toda escritura pide justificación (`ConfirmChangeDialog`).
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
- **Dock derecho:** dos pestañas.
  - **Propiedades:** información de la celda o sistema seleccionado. Contenido pendiente.
  - **Agentes:** actividad de agentes y de Stefan (cambios con autor y justificación, corridas lanzadas). Un agente activo se indica en la pestaña.
- **Panel inferior:** mensajes y corridas en curso.

### Editor de celda

Doble clic en una celda: abre el editor a pantalla completa en lugar del lienzo, con breadcrumb en la barra superior (`SAT-M1 › Fase 0 · base › Balance global`) para volver al esquemático. Muestra entradas y resultados completos de esa etapa. Diseño detallado por etapa: pendiente.

### Diálogos

Confirmar cambio (diff + justificación) · Abrir/Guardar nativos · Proyecto bloqueado por otra instancia (lock) · Eliminar sistema/celda.

## Interacciones

- Arrastrar del Toolbox al lienzo: crea un sistema (plantilla o celda suelta).
- Soltar del Toolbox **sobre una celda**: ramifica, crea lo soltado vinculado desde esa celda. Al arrastrar se resaltan solo las celdas donde el vínculo es válido.
- Clic: selecciona y muestra propiedades. Doble clic: abre el editor de celda.
- Clic derecho en sistema: renombrar, agregar etapa, actualizar, cortar, copiar, pegar, duplicar, eliminar. En celda: renombrar, actualizar, ramificar, desvincular, cortar, copiar, pegar, duplicar, eliminar. El clic derecho selecciona el sistema o la celda.
- Las celdas no se mueven entre sistemas.

## Menú Editar y atajos

Mismo estilo que Archivo (ícono, etiqueta y atajo). Actúa sobre la selección (un sistema o una celda); sin selección, Cortar, Copiar, Duplicar, Renombrar, Deseleccionar y Eliminar quedan deshabilitados. Los menús contextuales de sistema y celda muestran los mismos ítems con su atajo.

| Ítem | Atajo | Comportamiento |
| --- | --- | --- |
| Deshacer «operación» | Ctrl+Z | La etiqueta nombra lo que revierte (`undo_label`, p. ej. «Deshacer renombrar sistema»); el resumen completo va en el tooltip. |
| Rehacer «operación» | Ctrl+Shift+Z / Ctrl+Y | Ídem con `redo_label`. |
| Cortar | Ctrl+X | Pide la justificación (obligatoria), copia y elimina. Cancelar no copia ni elimina. |
| Copiar | Ctrl+C | Pide el fragmento a la API y lo deja en el portapapeles del sistema. No cambia el proyecto. |
| Pegar | Ctrl+V | Con el teclado pega donde está el cursor si está sobre el lienzo; desde el menú, desplazado respecto del original. Las celdas sueltas van al sistema seleccionado (o al de la celda seleccionada, o al del menú contextual). Deshabilitado si el portapapeles no tiene un fragmento; con el teclado, avisa en Mensajes. |
| Duplicar | Ctrl+D | Sistema: `duplicate_system` (conserva vínculos entrantes). Celda: copia y pega en su sistema. |
| Renombrar | F2 | Diálogo de renombrar del sistema o la celda. |
| Deseleccionar | Esc | Limpia la selección. |
| Eliminar | Supr | Con justificación obligatoria (`ConfirmChangeDialog`). |

Los atajos de edición no se interceptan en campos de texto, diálogos ni menús abiertos (cortar, copiar, pegar y deshacer de texto siguen siendo nativos), ni Ctrl+C / Ctrl+X cuando hay texto seleccionado en la página. Lo pegado queda seleccionado.

### Portapapeles

Detalle en [ADR 0014](adr/0014-portapapeles-de-esquematico.md). El fragmento es JSON con el marcador `"kind": "hestia.fragment"` en el portapapeles del sistema (plugin de Tauri en el escritorio, `navigator.clipboard` en el navegador, con copia en memoria si el navegador no da permiso), así que se puede copiar en un proyecto y pegar en otro. Pegar crea ids nuevos, conserva los vínculos internos, descarta los externos, deja las celdas «nunca corrida» y es un solo cambio en el historial. Nombres repetidos reciben « (2)».

## Decisiones cerradas

- **Actividad de agentes / Stefan:** pestaña «Agentes» del dock derecho, alternable con Propiedades (2026-09-28).
- **Editor de celda:** pantalla completa con breadcrumb (2026-09-28).

## Estado de la implementación (2026-09-29)

Alineado con `app/design/workspace.pen` (frames Workspace, Workspace · menú Archivo, Inicio e Inicio · primer uso) y los componentes de `hestia.lib.pen`. Código en `app/src/screens/` y `app/src/project/`.

Implementado:

- **Inicio:** logotipo, Nuevo y Abrir, y recientes (archivo, carpeta, última apertura; los que ya no existen se marcan como «archivo no encontrado»; quitar de recientes aparece al pasar el mouse). Sin recientes: la marca como plano de construcción. Pie con el estado de la API y la versión.
- **Barra superior:** menú Archivo (Nuevo Ctrl+N, Abrir Ctrl+O, Recientes, Guardar Ctrl+S, Guardar como Ctrl+Shift+S, Cerrar Ctrl+W) y Editar (ver [Menú Editar y atajos](#menú-editar-y-atajos)); Ver, Proyecto y Ayuda deshabilitados; nombre del archivo, ● de cambios sin guardar y botón guardar solo con cambios; herramientas futuras y Actualizar todo visibles y deshabilitados.
- **Toolbox:** fases y etapas por nombre. Arrastrar al lienzo crea el sistema (plantilla o celda suelta) donde se suelta; soltar sobre una celda ramifica. Durante el arrastre solo se resaltan las celdas que la API (`branch-targets`) da como válidas.
- **Esquemático (React Flow):** sistemas con sus celdas, estado de cada celda como ícono y vínculos ortogonales entre sistemas (los vínculos dentro de un sistema no se dibujan: el bloque ya los expresa); control de zoom abajo a la izquierda; selección de sistema o celda; mover sistemas; vincular arrastrando de la salida (derecha) a la entrada (izquierda) de otra celda, con destinos válidos según la API (`link-targets`). Menú contextual de sistema (renombrar, agregar etapa, actualizar deshabilitado, cortar, copiar, pegar, duplicar, eliminar) y de celda (renombrar, actualizar deshabilitado, ramificar con opciones de la API, desvincular, cortar, copiar, pegar, duplicar, eliminar).
- **Justificación:** eliminar, cortar y desvincular la exigen (`ConfirmChangeDialog`); renombrar la ofrece opcional; crear, ramificar, mover, vincular, duplicar, pegar y deshacer van sin justificación.
- **Errores de render:** la ruta raíz tiene `errorComponent`: un error muestra un mensaje con «Recargar» en lugar de dejar la ventana en blanco.
- **Diálogos:** cambios sin guardar (al crear, abrir, cerrar proyecto o cerrar la ventana de escritorio), proyecto bloqueado por otra instancia (cancelar o abrir de todos modos), renombrar, confirmar cambio.
- **Dock derecho:** pestañas Propiedades y Agentes, vacías.
- **Panel inferior:** Mensajes (eventos del proyecto de cualquier actor, por SSE, y errores) e Historial (autor, resumen y justificación); Corridas deshabilitada.

TODO:

- Selección múltiple (clic con Ctrl/Shift o rectángulo) y, con ella, «Seleccionar todo» (Ctrl+A) y copiar/cortar/eliminar varios a la vez. La API de copiar ya acepta listas de sistemas y celdas.
- Menú contextual del fondo del lienzo con «Pegar aquí» (hoy se pega en el cursor con Ctrl+V).
- Portapapeles en Tauri: el plugin compila (clippy) pero solo se probó en el navegador (Chromium); probar copiar entre dos ventanas en `make desktop`.
- Editor de celda (doble clic) y breadcrumb.
- Contenido de Propiedades y Agentes; indicador de agente activo.
- Cantidad de sistemas en cada reciente (el diseño la muestra; `RecentProject` de la API no la trae).
- Contador de agentes activos en la pestaña Agentes («Agentes · 1» en el diseño).
- Encuadrar la vista cuando un agente crea un sistema fuera de la zona visible (hoy hay que usar «ajustar vista»).
- Comparación, Actualizar, Exportar a NX, informe, paleta Ctrl+K y Stefan (dependen de cálculo o de funciones futuras).
- Diálogos nativos y cierre de ventana en Tauri: compilan (clippy) pero solo se probaron en el navegador, donde el respaldo pide la ruta con `window.prompt`. Probarlos en `make desktop`.
- Sidecar de la API con puerto aleatorio + token y archivo de instancia para el MCP (ADR 0008): hoy la API corre aparte en `:8000`.

## Decisiones abiertas

- Contenido del panel Propiedades (candidatos: entradas con su fuente, últimos resultados, historial, procedencia).
- Formato del sistema de Comparación.
