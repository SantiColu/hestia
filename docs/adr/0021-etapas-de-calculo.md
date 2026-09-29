# 0021. Etapas de cálculo: parámetros, Actualizar y resultado

- **Estado:** propuesto
- **Fecha:** 2026-09-29
- **Amplía:** 0009, 0017

## Contexto

Entorno (`environment`) es la primera etapa que calcula. A diferencia de Misión y Equipos (etapas formulario, ADR 0017), su artefacto no es lo cargado: es un resultado que depende del contexto aguas arriba (ADR 0016) y de parámetros propios de la etapa (valores de diseño, dispersiones, muestreo). Hay que decidir cómo se editan esos parámetros, qué es «correr», qué estado tiene la celda y cómo se registran autor y procedencia del resultado (principio 7), con paridad humano-agente.

## Decisión

- **Dos partes por celda:**
  - **Parámetros:** se editan como un formulario (ADR 0017): borrador en la UI, validación en seco en el backend, Aplicar con justificación en un solo cambio, defaults de biblioteca y procedencia por campo (`entered`, `imported`, `default`). Mismos endpoints genéricos del artefacto (ADR 0019) y mismo JSON Schema con extensiones `x-`.
  - **Resultado:** lo produce la etapa al actualizarse; nunca se edita a mano.
- **Actualizar (correr):** acción explícita sobre una celda, como «Update» en Workbench, disponible para humanos y agentes (endpoint y tool MCP). Toma el contexto resuelto y los parámetros aplicados, llama a `hestia_core` y guarda el resultado. Es un cambio del historial con autor; la justificación puede ir vacía. Deshacer vuelve al resultado anterior.
- **No corre sola:** cambiar Misión o los parámetros no recalcula nada; deja la celda desactualizada. Actualizar en cadena («Actualizar todo») queda para después.
- **Estados:**
  - `never_run`: nunca se actualizó.
  - `up_to_date`: el último resultado corresponde al contexto y los parámetros actuales.
  - `outdated`: cambió algo aguas arriba o se aplicaron parámetros nuevos. El resultado anterior se conserva y se muestra como desactualizado.
  - `failed`: la última actualización no produjo resultado. Los problemas usan el formato `{path, code, message}` del ADR 0017: parámetros inválidos, requisitos faltantes (`missing`), un formulario de contexto con problemas (`context_invalid`) o una entrada fuera de la envolvente del proveedor (ADR 0020).
- **Aplicar parámetros** desactualiza la propia celda (si tenía resultado) y todo lo aguas abajo, en un solo cambio.
- **Procedencia del resultado:** guarda qué celda proveyó cada tipo del contexto y en qué cambio estaba, qué parámetros usó y qué proveedor y versión lo calcularon. Mismas entradas → mismo resultado.
- **Resultado fuera de las instantáneas:** los resultados se guardan aparte en el `.hestia` y las instantáneas del historial (ADR 0010) los referencian por id, para no copiarlos en cada cambio.

## Consecuencias

- Las etapas de cálculo reutilizan todo lo de los formularios para sus parámetros; la UI arma el formulario igual que en Misión.
- El historial registra quién actualizó y con qué entradas; un resultado viejo siempre se puede auditar.
- Los agentes corren etapas con la misma tool que la UI y leen el resultado; nunca calculan por su cuenta (principio 4).
- Actualizar es síncrono mientras las etapas tarden segundos. Si alguna tarda más, hace falta ejecución en segundo plano con progreso (eventos SSE, ADR 0012).
- Pendiente: Actualizar todo en orden, formato de resultados pesados (fase 1) y si conviene guardar resultados en otro formato (Parquet u otro) cuando el volumen lo justifique.
