# 0017. Etapas formulario: borrador, validación en seco y Aplicar

- **Estado:** propuesto
- **Fecha:** 2026-09-29

## Contexto

Las primeras etapas por implementar, Misión y Equipos, no calculan: su artefacto es lo que el usuario carga, validado ([campos](../etapas/mission.md)). Hay que decidir cómo se edita un artefacto así desde la UI y desde los agentes, cómo se valida sin que la UI decida nada, qué estado tiene la celda y cómo se registra la procedencia, respetando autor y justificación en todo cambio (ADR 0011) y la paridad humano-agente (ADR 0003).

## Decisión

- **Etapa formulario:** su artefacto es el dato cargado, validado. «Correr» es validar. Hoy son `mission` y `equipment`.
- **Modelo:** un modelo pydantic por etapa (`MissionArtifact`, `EquipmentArtifact`) con `schema_version`, en `hestia_core`. Todo campo es opcional en el borrador: el modelo acepta datos incompletos y la validación de consistencia es aparte.
- **Validación:** una función determinística por etapa, en `hestia_core`, que recibe el artefacto y devuelve una lista de problemas `{path, code, message}`: `path` es la ruta del campo (`orbit.altitude`, `items[2].operating_min`), `code` es estable y `message` está en español. Cubre completitud (obligatorios) y consistencia (reglas de los documentos de campos). No produce valores nuevos.
- **Borrador en la UI, validación en el backend:**
  - Lo editado es un borrador que vive en la UI.
  - Mientras se edita, la UI pide una **validación en seco**: se envía el borrador y vuelven los problemas, sin cambiar el proyecto ni el historial. La UI solo muestra lo que devuelve la API.
- **Aplicar:** reemplaza el artefacto de la celda con el borrador, con justificación obligatoria, en **un solo cambio** del historial (un deshacer). Si el contenido no cambió, no hay cambio. Se puede aplicar con problemas.
- **Estado de una celda formulario:** `never_run` si nunca se aplicó; `up_to_date` si el artefacto aplicado valida sin problemas; `failed` si tiene problemas (se guardan con el artefacto). No pasan a `outdated`: si una etapa formulario tuviera contexto, se revalidaría sola. Aplicar desactualiza todo lo que está aguas abajo.
- **Valores por defecto:** al crear la celda, el artefacto trae los defaults de biblioteca (p. ej. márgenes ECSS) con procedencia `default`.
- **Procedencia por campo:** el artefacto guarda, por ruta de campo hoja, `{source, change_id}`:
  - `source` puede ser `entered` (cargado a mano, por humano o agente), `imported` (planilla) o `default` (biblioteca).
  - Autor, fecha y justificación salen del cambio (`change_id`) en el historial.
  - Aplicar actualiza la procedencia solo de los campos que cambiaron.
- **Unidades:** el contrato y el almacenamiento van en SI, con temperaturas en K. Cada campo físico declara en su JSON Schema la unidad SI y la de presentación (`x-unit`, `x-display-unit`; p. ej. `m` / `km`, `K` / `°C`, `K` / `K` para diferencias). La UI convierte solo para mostrar. Las importaciones de planillas normalizan con pint y distinguen temperatura absoluta de diferencia.
- **Agentes:** las mismas tres operaciones como tools MCP: leer el artefacto con sus problemas, validar un borrador y aplicar con justificación.

## Consecuencias

- La UI no duplica reglas: el formulario se arma con el JSON Schema del contrato, y los errores y el estado vienen de la API.
- Guardar a medias es posible: una misión incompleta se aplica, queda `failed` y muestra qué le falta.
- El historial no se llena de cambios campo por campo, y cada aplicación desactualiza aguas abajo una sola vez.
- Un borrador sin aplicar se pierde si se cierra la app sin aplicar. La UI avisa, igual que con cambios sin guardar.
- La procedencia por campo agrega tamaño al artefacto; es aceptable para formularios de decenas o cientos de campos.
- Pendiente: el popover de procedencia e historial en la UI, la importación de planillas en Equipos (mapeo de columnas) y el contexto de las futuras etapas formulario que no sean raíz.
