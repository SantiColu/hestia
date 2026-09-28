# 0005. Modelo de workflow tipo Workbench

- **Estado:** aceptado · ampliado por 0009 (celdas, vínculos, sistemas; sin gates)
- **Fecha:** 2026-09-28

## Contexto

El prediseño térmico es una cadena de etapas con dependencias e iteraciones (0.4↔0.3, 1.6→1.1) y transferencias entre fases. Un cambio en la misión debe invalidar resultados posteriores de forma visible.

## Decisión

El proyecto es un grafo de etapas. Cada etapa tiene entradas, salidas tipadas (artefactos con esquema versionado), estado (`up_to_date`, `outdated`, `failed`, `never_run`) y procedencia (qué entradas y versión de código produjeron cada salida). Cambiar algo aguas arriba marca como `outdated` lo dependiente. Vive en `hestia_project`.

## Consecuencias

- Toda etapa nueva se registra con entradas, salidas y dependencias explícitas (skill `add-workflow-stage`).
- Los resultados son reproducibles y auditables.
- Pendiente: modelado de iteraciones y semántica de gates.
