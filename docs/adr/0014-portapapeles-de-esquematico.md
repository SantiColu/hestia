# 0014. Portapapeles del esquemático: fragmentos versionados

- **Estado:** propuesto
- **Fecha:** 2026-09-29
- **Amplía:** 0009, 0011

## Contexto

El menú Editar necesita cortar, copiar, pegar y duplicar sistemas y celdas, también entre proyectos distintos. La lógica de dominio vive en el backend (la UI no decide qué se copia ni cómo se reconstruye), los agentes tienen que poder hacer lo mismo por MCP y todo cambio lleva autor, justificación y deshacer. Ya existía `duplicate_system`, que copia un sistema dentro del mismo proyecto conservando los vínculos entrantes.

## Decisión

- **Qué se copia:** sistemas completos (con todas sus celdas) y celdas sueltas, agrupadas por el sistema del que vienen.
- **Formato:** un *fragmento* JSON que genera el backend (`hestia_project.clipboard.Fragment`): `kind: "hestia.fragment"` como marcador, `schema_version` (hoy 1), id del proyecto de origen, los sistemas (nombre, posición, si va completo y sus celdas: id de origen, tipo de etapa y nombre) y los vínculos entre celdas del fragmento. No lleva estados, resultados ni procedencia.
- **Copiar:** `POST /project/clipboard/copy` con `system_ids` y `cell_ids` devuelve el fragmento. Es de solo lectura: no cambia el proyecto ni el historial.
- **Pegar:** `POST /project/clipboard/paste` con el fragmento, posición opcional, sistema destino opcional y justificación (puede ir vacía, como duplicar). El backend:
  - rechaza con `invalid_fragment` (422) un fragmento de versión desconocida, sin celdas, con celdas repetidas o con vínculos a celdas que no incluye;
  - crea todo con ids nuevos y celdas en «nunca corrida»;
  - crea los sistemas completos como sistemas nuevos; las celdas sueltas van al sistema destino si se indica y si no a un sistema nuevo (con el nombre de la celda si es una sola, o el del sistema de origen);
  - resuelve nombres en conflicto como duplicar: « (2)», « (3)»… para sistemas, y para celdas dentro del mismo sistema;
  - con posición, el sistema de arriba a la izquierda del fragmento cae ahí y el resto conserva su disposición; sin posición, cada sistema se desplaza respecto del original y baja hasta no superponerse;
  - recrea los vínculos internos validándolos como cualquier vínculo (tipos, fuente única, sin ciclos); si alguno no es válido rechaza el pegado entero;
  - **descarta los vínculos externos** (entrantes y salientes): en otro proyecto no tienen sentido y en el mismo proyecto una entrada solo admite una fuente. Quien quiera conservar las entradas usa Duplicar;
  - registra un solo cambio `paste` en el historial, con autor y justificación: un deshacer lo revierte entero.
- **Cortar:** copiar y después eliminar (`delete_system` / `delete_cell`), con justificación obligatoria. La UI la pide antes de copiar, así cancelar no toca nada.
- **Duplicar:** los sistemas usan `duplicate_system`. Una celda se duplica copiándola y pegándola en su mismo sistema (un solo cambio).
- **Dónde vive el fragmento:** en el portapapeles del sistema operativo como texto JSON (plugin de portapapeles de Tauri en el escritorio, `navigator.clipboard` en el navegador, con una copia en memoria si el navegador niega el acceso). La UI solo reconoce el marcador `kind` para habilitar Pegar; la validación es del backend y sus errores llegan a Mensajes.
- **MCP:** `copy_to_clipboard` devuelve el fragmento y `paste_from_clipboard` lo recibe. El agente guarda el fragmento entre llamadas; no hay portapapeles del lado del servidor.
- **Etiquetas de deshacer:** el estado del documento expone `undo_label` / `redo_label` (nombre corto de la operación, p. ej. «renombrar sistema») además del resumen, para el menú Editar.

## Consecuencias

- Copiar de un proyecto y pegar en otro funciona sin estado en la API; el fragmento es autocontenido y versionado, y un cambio incompatible exige subir `schema_version`.
- El texto JSON en el portapapeles es legible y se puede pegar por error en otra aplicación; es aceptable para una app local.
- Pegar no recrea vínculos externos: tras pegar un sistema de Fase 1 hay que volver a vincularlo a su Fase 0.
- Pendiente: selección múltiple (copiar varios sistemas desde la UI; la API ya acepta listas), pegar en el lienzo desde un menú contextual del fondo y conservar vínculos entrantes al pegar dentro del mismo proyecto si se pide.
