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

### Workspace (proyecto abierto)

```
┌ SAT-M1.hestia ● ───────────────────────────────────────────────────────┐
│ TOOLBOX       │ ESQUEMÁTICO                            │ PROPIEDADES   │
│ Plantillas    │  ┌ Fase 0 · base ✎ ─┐   ┌ Fase 1 · A ✎ ┐ │ de la celda o │
│  Fase 0       │  │ Misión         ● │─┬▶│ Discretiz. ○ │ │ sistema       │
│  Fase 1       │  │ Entorno LEO600 ● │ │ │ …            │ │ seleccionado  │
│ Etapas        │  │ Balance global ◐ │ │ └──────────────┘ │               │
│  Misión       │  │ Concepto TCS   ○ │ └▶┌ Entorno · SSO800 ✎ ┐           │
│  Entorno …    │  └──────────────────┘   │ Entorno          ○ │           │
│ Post-proceso  │                         └────────────────────┘           │
│  Comparación  │                                                          │
├───────────────┴──────────────────────────────────────────┴───────────────┤
│ Mensajes · Corridas · Actividad de agentes                               │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Barra superior:** nombre del archivo, indicador de cambios sin guardar (●), acciones globales (Actualizar todo, Guardar).
- **Toolbox (izquierda):** plantillas de sistema (Fase 0, Fase 1: celdas ya vinculadas), etapas sueltas (los 10 tipos) y post-proceso (Comparación).
- **Esquemático (centro):** sistemas como bloques con nombre editable (✎) y filas de celdas; cada celda muestra número, nombre y estado. Vínculos como conectores ortogonales entre celdas (una salida puede ir a muchas celdas).
- **Propiedades (derecha):** resumen de la selección: entradas (con su fuente: vínculo o manual), últimos resultados, historial, procedencia.
- **Panel inferior:** mensajes, corridas en curso y actividad de agentes.

### Editor de celda

Doble clic en una celda: entradas y resultados completos de esa etapa. Diseño detallado por etapa: pendiente.

### Diálogos

Confirmar cambio (diff + justificación) · Abrir/Guardar nativos · Proyecto bloqueado por otra instancia (lock) · Eliminar sistema/celda.

## Interacciones

- Arrastrar del Toolbox al lienzo: crea un sistema (plantilla o celda suelta).
- Soltar del Toolbox **sobre una celda**: ramifica, crea lo soltado vinculado desde esa celda. Al arrastrar se resaltan solo las celdas donde el vínculo es válido.
- Clic: selecciona y muestra propiedades. Doble clic: abre el editor de celda.
- Clic derecho en sistema: renombrar, actualizar, duplicar, eliminar. En celda: renombrar, actualizar, ramificar, desvincular, eliminar.
- Las celdas no se mueven entre sistemas.

## Decisiones abiertas

- **Dónde vive la actividad de agentes / Stefan:** dock derecho alternable con Propiedades (recomendado), pestaña del panel inferior, o paleta flotante (Ctrl+K).
- **Editor de celda:** pantalla completa con breadcrumb para volver, o pestañas.
- Formato del sistema de Comparación.
- Estilo exacto del conector (ortogonal con flecha, como en el boceto inicial).
