# 0023. La órbita y los modos de actitud pasan de Misión a Entorno, con vista previa de la órbita al editar

- **Estado:** propuesto
- **Fecha:** 2026-09-30
- **Reemplaza en parte:** 0016 (Misión conserva los modos de actitud), 0020 (el proveedor recibe la órbita y los modos de Misión), 0022 (los parámetros de Entorno se validan contra el tipo de órbita de Misión)

## Contexto

Misión (0.1, formulario) define hoy la órbita y los modos de actitud, y Entorno (0.2, cálculo) los traduce en β, eclipses y flujos. Entorno es el único que los usa: `global_balance` y `load_cases` toman la geometría del resultado de Entorno y referencian los modos de actitud por `id`.

Esta división tiene tres costos:

- **Variantes duplicadas.** Con el contexto por cadena (ADR 0016), comparar dos órbitas (otra hora del nodo, otra altitud) obliga a crear dos celdas de Misión y copiar envolvente, masa, criterios y fechas. En la fase 0, ese es el estudio de compromiso más común.
- **Validación partida entre celdas.** Los parámetros de dispersión de Entorno dependen del tipo de órbita de Misión, `eol_altitude` se compara con la altitud de Misión y el default de albedo e IR depende de la inclinación. Nada de eso se puede validar dentro del propio formulario.
- **Editar sin ver.** Para ver cómo queda una órbita o una actitud hay que aplicar en Misión, ir a Entorno, actualizar y abrir la vista 3D.

## Decisión

- **Órbita y modos de actitud son parámetros de Entorno.** Las secciones `orbit` y `attitude_modes` pasan, con los mismos campos y validaciones ([mission.md](../etapas/mission.md)), a `EnvironmentParameters`, antes de `design_values`. Misión conserva `general`, `envelope` y `criteria`. Los dos esquemas suben de versión: `MissionArtifact` v2 y `EnvironmentParameters` v2.
- **Entorno sigue requiriendo Misión.** De Misión toma solo la ventana de la misión (`launch_date`, `design_life`), que acota `mission_step` y define las fechas. Las caras de la envolvente son fijas (+X…−Z).
- **La validación de la órbita queda en una sola celda.** Tipo de órbita, dispersiones, `eol_altitude` y default de albedo e IR por inclinación se validan en seco dentro del formulario de Entorno. Solo `mission_step` ≤ `design_life` mira el contexto.
- **Vista previa de la órbita.** El backend calcula una órbita a partir del borrador de parámetros, sin guardarla: ni cambio, ni historial, ni cambio de estado de la celda. La UI la pide con *debounce*, igual que la validación en seco, y la dibuja en una vista 3D junto al formulario.
  - Contenido: una órbita nominal, en la fecha elegida (por defecto, la de lanzamiento) y para el modo de actitud elegido. Incluye β, período, eclipse y el perfil geométrico: posición, velocidad, vector solar, sol o eclipse, cuaternión cuerpo → inercial y ángulo de rotación terrestre.
  - Sin flujos: los flujos siguen saliendo solo de Actualizar.
  - Mismo proveedor que Actualizar (ADR 0020), así la vista previa y el resultado no difieren.
  - Si el borrador tiene problemas en `orbit` o `attitude_modes`, devuelve los problemas y ninguna órbita.
  - Endpoint en la API y tool MCP equivalente (paridad): un agente puede mirar una órbita antes de aplicarla.
- **Migración del proyecto (formato v5):**
  - La órbita y los modos de actitud de cada Misión se copian a cada celda de Entorno que la tenga en su contexto, con su procedencia.
  - Si una Misión no tiene ningún Entorno aguas abajo, se crea uno vinculado en su sistema (`never_run`), para no perder los datos.
  - Los resultados existentes se conservan con su estado: las entradas no cambiaron, solo de celda.
  - Las instantáneas del historial se migran igual, así deshacer nunca restaura un artefacto con el esquema viejo. En ellas no se crean celdas: si una Misión de una instantánea no tiene Entorno, su órbita y sus modos se descartan (siguen en el Entorno creado en el proyecto actual).

## Consecuencias

- Una Misión puede alimentar varios Entornos con órbitas o actitudes distintas. Balance global, casos y comparación funcionan sobre esas ramas sin duplicar la Misión.
- Se ve la órbita mientras se edita, en la misma pestaña. Es la base para ver también la actitud (la envolvente orientada) antes de actualizar.
- Misión queda como requisitos del proyecto (fechas, envolvente, márgenes, presupuestos), y Entorno mezcla dos cosas: la definición de la órbita y los parámetros del cálculo. El formulario de Entorno crece y necesita secciones claras.
- La vista previa le suma carga al backend en cada edición. Con el proveedor analítico, una órbita cuesta milisegundos. Si un proveedor futuro es lento (Orekit), la vista previa puede usar el analítico y decirlo.
- Hay que cambiar modelos, validaciones, proveedor, API, tools MCP y formularios (el diseño en `workspace.pen` y los documentos de etapa ya están actualizados). Los agentes que escribían `orbit` o `attitude_modes` en Misión reciben un error de campo desconocido y tienen que escribir en los parámetros de Entorno.
- Pendiente: si la vista previa suma flujos (necesita albedo e IR válidos), con qué RAAN dibuja una órbita LEO/MEO (que no lo fija) y si muestra la misión completa (la fecha mueve el plano orbital).
