# 0022. Contrato de las etapas de cálculo y formato del proyecto v4

- **Estado:** propuesto; la validación contra el tipo de órbita de Misión, reemplazada por 0023
- **Fecha:** 2026-09-29
- **Amplía:** 0019, 0020, 0021

## Contexto

Al implementar Entorno, la primera etapa de cálculo (ADR 0021, [especificación](../etapas/environment.md)), quedaron decisiones que los ADR 0020 y 0021 no fijan: la forma de los endpoints de Actualizar y del resultado, cómo conviven en el mismo cuerpo el artefacto de Misión y los parámetros de Entorno, qué pasa al actualizar una celda que ya está al día o que falla igual, qué se hace con el resultado anterior si falla, cómo se guardan los resultados en el `.hestia` y cómo se abren los archivos anteriores. El resultado de una misión de 5 años con 4 condiciones y 2 modos pesa ~0,6 MB, casi todo perfiles orbitales.

## Decisión

- **Parámetros con los endpoints genéricos del artefacto** (ADR 0019): el cuerpo es la unión `MissionArtifact | EnvironmentParameters`. Los dos modelos prohíben campos desconocidos, así el JSON resuelve a uno solo; el backend lo valida contra el modelo de la etapa de la celda. Los parámetros se validan contra el contexto (p. ej. el tipo de órbita de Misión): al aplicar, al validar en seco y al leer.
- **Endpoints de cálculo, por celda:** `POST /project/cells/{id}/update` (Actualizar; justificación opcional), `GET …/result` (estado, problemas, procedencia, parámetros usados y el resultado **sin los perfiles**, que se listan por condición y modo) y `GET …/result/orbit-profile?condition_id=&mode_id=` (un perfil). Los perfiles se leen de a uno: son lo pesado, los usan la vista 3D y los agentes que los piden.
- **Actualizar sin diferencias:** si la celda está `up_to_date` con la misma versión del proveedor, o falla otra vez con los mismos problemas, no se registra nada y la respuesta trae `change: null` (como Aplicar sin diferencias).
- **Actualizar que falla** deja la celda `failed` con los problemas (`missing`, `context_invalid`, parámetros inválidos o entradas fuera de la envolvente del proveedor) y **conserva el resultado anterior**, que se muestra como anterior. No desactualiza aguas abajo: sus entradas no cambiaron.
- **Desactualizar una celda fallida:** un cambio aguas arriba pasa `failed` a `outdated` aunque la celda no tenga resultado (sus problemas pueden haber dejado de valer). La vista muestra «sin resultado» y ofrece Actualizar.
- **Contexto inválido:** un formulario del contexto nunca aplicado o con problemas, o una etapa de cálculo del contexto sin resultado actual, es `context_invalid`.
- **Registro en `hestia_project`:** cada etapa de cálculo declara su formulario de parámetros (`forms.FORMS`) y su cálculo (`computations.COMPUTATIONS`: modelo del resultado, función de `hestia_core`, proveedor y versión).
- **Formato del proyecto v4:** tabla `results` (id, celda, etapa, parámetros y datos en JSON) y columnas `cells.result_id` y `cells.problems`. Las celdas referencian el resultado por id; las instantáneas del historial también. Al guardar se descartan los resultados que ni el proyecto ni el historial referencian. `FormState.applied_change_id` guarda el cambio de cada Aplicar (procedencia del contexto de un resultado).
- **Migración v3 → v4:** las celdas de Entorno reciben los parámetros por defecto (`never_run`); el `applied_change_id` de los formularios aplicados se recupera del historial (el último cambio a partir del cual la celda tiene su artefacto actual). Sin cambio en el historial.
- **Pegar** una celda de cálculo copia sus parámetros, nunca el resultado: queda `never_run`.

## Consecuencias

- Una etapa de cálculo nueva agrega su modelo de parámetros a la unión del cuerpo, su registro en `FORMS` y `COMPUTATIONS` y, si su resultado tiene partes pesadas, un endpoint para leerlas por partes. La UI arma el formulario igual que en Misión.
- Los agentes leen el resumen con `get_cell_result` y piden perfiles puntuales con `get_orbit_profile` sin traer megabytes a su contexto.
- Un resultado viejo se audita desde el historial: el archivo lo conserva mientras alguna instantánea lo referencie. El `.hestia` crece con cada Actualizar que cambia algo; si pesa demasiado, hará falta compactar el historial o guardar los perfiles en otro formato (pendiente del ADR 0021).
- Pendiente: Actualizar todo en orden y en segundo plano, y un formato de resultados pesados para la fase 1.
