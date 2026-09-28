# 0002. Backends de cálculo open source con API/SDK

- **Estado:** aceptado
- **Fecha:** 2026-09-28

## Contexto

Los cálculos (mecánica orbital, factores de vista, resolución de redes térmicas, propiedades de fluidos, sensibilidad) requieren librerías especializadas. Herramientas propietarias o sin API programática impiden la automatización y el uso por agentes.

## Decisión

Usar herramientas open source con API/SDK programable: Orekit (orekit-jpype), pyViewFactor, pyvista, numpy/SciPy, CoolProp, SALib, OpenMDAO. Se integran detrás de Protocols definidos en `hestia_core` e implementados en `hestia_adapters`.

## Consecuencias

- `hestia_core` queda testeable sin las herramientas externas.
- Cambiar de proveedor es reemplazar un adapter.
- Orekit requiere JVM: impacta instalación y CI (pendiente de resolver).
