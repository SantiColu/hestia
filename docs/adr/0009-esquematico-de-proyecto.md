# 0009. Esquemático de proyecto: celdas, vínculos y sistemas

- **Estado:** aceptado
- **Fecha:** 2026-09-28
- **Amplía:** 0005

## Contexto

El ADR 0005 modelaba el proyecto como un grafo fijo de las diez etapas de las fases 0 y 1. En la práctica se quiere trabajar como en el Project Schematic de Ansys Workbench: explorar variantes (dos entornos a partir de la misma misión, varias fase 1 sobre la misma fase 0) y comparar resultados.

## Decisión

- **Celda:** instancia de un tipo de etapa (`mission`, `environment`, …, `sensitivity`) con nombre editable, entradas, salidas tipadas, estado y procedencia. Es la unidad del grafo.
- **Vínculo:** conecta una salida de una celda con una entrada de otra. El backend valida los tipos; las transferencias de `docs/workflow-fases-0-1.md` definen qué conexiones son válidas. Una salida puede alimentar muchas celdas; cada entrada tiene una sola fuente: un vínculo o un valor cargado a mano.
- **Sistema:** contenedor con nombre que agrupa celdas (p. ej. «Fase 0 · base»). Puede tener todas las celdas de una fase, algunas o una sola. Las plantillas «Fase 0» y «Fase 1» crean el sistema con sus celdas ya vinculadas. Las celdas no se mueven entre sistemas.
- **Ramificar:** crear celdas o sistemas vinculados a partir de cualquier celda existente (p. ej. dos `environment` alimentados por la misma `mission`).
- **Comparación:** tipo de sistema de post-proceso que toma salidas de varias celdas del mismo tipo y las muestra lado a lado.
- **Sin gates por ahora:** todo es editable siempre. Cambiar algo marca como desactualizado todo lo que depende de ello.
- **Iteraciones** (0.4 → 0.3, 1.6 → 1.1) no son vínculos: se resuelven editando aguas arriba o ramificando. El grafo de vínculos es acíclico.

## Consecuencias

- `hestia_project` modela celdas, vínculos y sistemas; la propagación de `outdated` recorre vínculos, incluso entre sistemas.
- La API y el MCP exponen operaciones de esquemático (crear sistema desde plantilla, agregar celda, vincular, ramificar, renombrar, eliminar) con autor y justificación.
- La UI principal es un esquemático: Toolbox, lienzo de sistemas, propiedades y panel inferior.
- Pendiente: gates de revisión (si se reintroducen), formato de la comparación y validación detallada de tipos por entrada.
