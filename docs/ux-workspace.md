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

- **Barra superior:** marca · menús (**Archivo**: nuevo, abrir, recientes, guardar, guardar como, cerrar, con atajos; **Editar**: deshacer/rehacer; Ver, Proyecto y Ayuda deshabilitados por ahora) · nombre del archivo con el indicador de cambios sin guardar (●) y el botón guardar (solo con cambios pendientes) · herramientas futuras deshabilitadas (paleta de comandos Ctrl+K, comparar, informe, exportar a NX, Stefan) · resumen de celdas desactualizadas y Actualizar todo. Deshacer no está en la barra: vive en Editar y en Ctrl+Z.
- **Toolbox (izquierda):** árbol por fase. El encabezado de la fase (Fase 0 · Viabilidad, Fase 1 · Modelo nodal) se arrastra entero y crea el sistema con todas sus celdas vinculadas; cada etapa se arrastra sola. Sin números de etapa: son internos. Abajo, post-proceso (Comparación).
- **Esquemático (centro):** sistemas como bloques con nombre editable (✎) y filas de celdas; cada celda muestra número, nombre y estado. Vínculos como conectores ortogonales entre celdas (una salida puede ir a muchas celdas).
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
- Clic derecho en sistema: renombrar, actualizar, duplicar, eliminar. En celda: renombrar, actualizar, ramificar, desvincular, eliminar.
- Las celdas no se mueven entre sistemas.

## Decisiones cerradas

- **Actividad de agentes / Stefan:** pestaña «Agentes» del dock derecho, alternable con Propiedades (2026-09-28).
- **Editor de celda:** pantalla completa con breadcrumb (2026-09-28).

## Decisiones abiertas

- Contenido del panel Propiedades (candidatos: entradas con su fuente, últimos resultados, historial, procedencia).
- Formato del sistema de Comparación.
- Estilo exacto del conector (ortogonal con flecha, como en el boceto inicial).
