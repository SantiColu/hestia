# 0026. Derivados de formularios y editores propios

- **Estado:** propuesto
- **Fecha:** 2026-10-05
- **Amplía:** 0017, 0019

## Contexto

El ADR 0017 fija que validar un formulario no produce valores, y el ADR 0019 que una etapa formulario nueva (Equipos) solo agrega modelo, validación y defaults: «la UI y el MCP no cambian». Equipos ([especificación](../etapas/equipment.md)) necesita dos cosas que eso no cubre:

- La disipación total de cada modo operativo mientras se edita, para personas y agentes. Calcularla en la UI o en el agente rompe los principios 1 y 4 de `AGENTS.md`.
- Una matriz equipos × modos operativos trasponible, que el formulario generado desde el JSON Schema no puede armar.

## Decisión

- **Derivados:** el registro de formularios admite un derivado opcional por etapa, una función pura de `hestia_core` sobre el artefacto. La lectura del artefacto de una celda y la validación en seco lo devuelven en `derived` (un modelo tipado por etapa en el contrato; `null` en las etapas sin derivados). Validar sigue sin cambiar el artefacto: el derivado no se guarda ni tiene procedencia.
- **Editores propios:** una etapa formulario puede tener un editor propio en la UI en lugar del formulario generado, sobre el mismo borrador, la misma validación en seco y el mismo Aplicar (`useArtifactDraft`). Sigue leyendo títulos, unidades, etiquetas y prefijos de id del JSON Schema; solo decide la disposición y los ajustes del borrador que mantienen sus referencias internas (ADR 0025). Hoy: Equipos.

## Consecuencias

- Los totales de Equipos salen del backend con test y llegan a la UI y al MCP sin cálculo propio; `global_balance` usará la misma función.
- Cada derivado nuevo suma un miembro a la unión `Derived` del contrato.
- Un editor propio es código de UI por etapa: hay que mantenerlo alineado con el modelo. Se reserva para pantallas que el formulario generado no puede dar.
- Modifica la consecuencia del ADR 0019 «la UI y el MCP no cambian» para Equipos (el MCP no cambia: sus tools genéricas devuelven `derived`).
