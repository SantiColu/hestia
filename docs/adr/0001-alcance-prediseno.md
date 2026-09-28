# 0001. Alcance limitado al prediseño (fases 0 y 1)

- **Estado:** aceptado
- **Fecha:** 2026-09-28

## Contexto

El diseño térmico de un satélite mediano pasa por viabilidad, dimensionamiento nodal, modelado detallado (GMM/TMM) y ensayos. Las fases detalladas ya están bien cubiertas por Siemens NX; las tempranas se hacen con planillas y cálculos sueltos, sin trazabilidad.

## Decisión

Hestia cubre solo la fase 0 (viabilidad) y la fase 1 (dimensionamiento nodal). El cierre de fase 1 es el pase a NX.

## Consecuencias

- Modelos de baja/mediana fidelidad (nodo único, redes nodales de decenas a cientos de nodos).
- No se implementa geometría CAD detallada ni correlación con ensayos.
- Hará falta definir un formato de exportación hacia NX (pendiente).
