# 0019. Contrato de las etapas formulario y migración del proyecto

- **Estado:** propuesto
- **Fecha:** 2026-09-29
- **Amplía:** 0014, 0016, 0017

## Contexto

Al implementar el contexto por cadena (ADR 0016) y la etapa Misión (ADR 0017) quedaron decisiones que esos ADR no fijan: la forma de los endpoints del artefacto, cómo arma la UI un formulario sin decidir reglas, qué pasa al aplicar un borrador idéntico, qué copia el portapapeles de una celda formulario, cómo se autovincula una celda nueva sin crear vínculos inútiles y cómo se abren los `.hestia` anteriores.

## Decisión

- **Endpoints por celda, genéricos:** `GET /project/cells/{id}/artifact` (artefacto aplicado, problemas, procedencia, estado y contexto), `POST …/artifact/validate` (en seco) y `PUT …/artifact` (aplicar, justificación obligatoria). El cuerpo está tipado con el modelo de la etapa (hoy `MissionArtifact`; con Equipos pasa a ser una unión y el backend valida contra el modelo de la etapa de la celda). Una etapa sin formulario responde `stage_not_implemented` (422).
- **Esquema para formularios:** `GET /catalog/stages/{stage}/artifact-schema` devuelve el JSON Schema del artefacto con extensiones `x-`: `x-unit` y `x-display-unit` (unidades), `x-enum-labels` (etiquetas), `x-show-if` (campos que aplican a una opción, p. ej. tipo de órbita), `x-notes` (nota por opción), `x-input` (`textarea`, `time`) y `x-default` (default de biblioteca). La UI arma el formulario solo con eso; un campo de otra opción con valor sigue visible para poder corregir el `not_allowed` que informa la API.
- **Aplicar sin diferencias:** si el contenido es igual al aplicado (y la celda ya se había aplicado), no se registra nada y la respuesta trae `change: null`. La primera aplicación de los defaults sí se registra (cambia el estado) pero no desactualiza aguas abajo.
- **Ids de listas:** los ítems conservan el id que ya tenían; los nuevos, desconocidos o repetidos reciben un id del backend. La procedencia se compara por id, así que insertar una fila no cambia la procedencia de las demás.
- **Procedencia pendiente:** una operación marca la procedencia nueva con un id provisorio y `ProjectDocument` lo reemplaza por el id del cambio que la registra. Los defaults de celdas que vienen de archivos viejos no tienen cambio (`change_id: null`).
- **Portapapeles, fragmento v2:** una celda formulario lleva su artefacto, si estaba aplicada y la fuente de cada campo (sin ids de cambio). Al pegar se revalida: queda `never_run` si no estaba aplicada y si no `up_to_date`/`failed`. Se siguen aceptando fragmentos v1 (la celda recibe los defaults).
- **Autovinculación al agregar una celda:** solo se agregan vínculos válidos que **aportan un requisito faltante** (como destino, recorriendo en orden inverso del catálogo; como fuente, hacia celdas a las que les falta algo que la nueva aporta). Así una misión suelta no se vincula a un concepto TCS, lo que después impediría unir el balance.
- **Plantillas con vínculos explícitos:** cada plantilla declara sus vínculos en el catálogo (Fase 0: la unión en el balance; Fase 1: cadena lineal) y se validan como cualquier vínculo.
- **Migración del proyecto:** `SCHEMA_VERSION` 3. v1 → v2: los vínculos se reevalúan en orden de creación con las reglas nuevas; los descartados llegan como `warnings` del evento `project_opened` (Mensajes), sin cambio en el historial. v2 → v3: las celdas de Misión reciben los defaults (`never_run`). El archivo se reescribe en la versión nueva al guardar.

## Consecuencias

- Una etapa formulario nueva (Equipos) solo agrega su modelo, validación y defaults en `hestia_core`, se registra en `hestia_project.forms.FORMS` y entra en la unión del cuerpo; la UI y el MCP no cambian.
- Las extensiones `x-` son contrato: renombrarlas rompe el formulario. Las conversiones de unidades de presentación viven en la UI (`app/src/lib/units.ts`) y hay que sumar ahí cada `x-display-unit` nueva.
- Las reglas de unión permiten vincular una rama de Fase 0 a cualquier celda de una Fase 1 suelta; `link-targets` lo refleja.
- Pendiente: vista previa en la API de las celdas que desactualiza un Aplicar (hoy el diálogo lo dice en genérico), popover de procedencia e historial por campo, y revalidación de formularios con contexto cuando exista alguno que no sea raíz.
