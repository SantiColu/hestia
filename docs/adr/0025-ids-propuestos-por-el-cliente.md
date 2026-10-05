# 0025. Ids de listas propuestos por el cliente

- **Estado:** propuesto
- **Fecha:** 2026-10-05

## Contexto

El ADR 0019 fija que los ítems de las listas de un artefacto conservan su id y que los nuevos, desconocidos o repetidos reciben un id del backend al aplicar. Alcanzaba mientras ningún campo del artefacto referenciara a otro ítem del mismo borrador.

En Equipos ([especificación](../etapas/equipment.md)) cada modo operativo dice en qué modo está cada equipo: referencia equipos y modos de equipo del mismo artefacto. En un borrador, un equipo o un modo recién agregado todavía no tiene id, así que no se lo puede referenciar. Una alineación por posición se rompe al borrar o reordenar, y que la UI reescriba referencias cuando el backend asigna ids mete lógica en los dos lados. Lo mismo le pasa a un agente que arma un artefacto completo en una sola escritura.

## Decisión

- El cliente (UI o agente) puede proponer el id de un ítem nuevo de una lista con id. El backend lo conserva si tiene el formato válido (`<prefijo>_<hex>`, el prefijo de esa lista) y no está repetido en el artefacto.
- El backend genera el id solo cuando falta, tiene otro formato o está repetido. Las referencias dentro del artefacto usan los ids, así que un id propuesto válido es estable desde el borrador.
- Si el backend tiene que reemplazar un id que alguna referencia usa, la referencia queda inválida y la validación la informa como problema; no se reescribe en silencio.
- Los ids siguen siendo inmutables una vez aplicados.

## Consecuencias

- Las referencias cruzadas dentro de un artefacto (Equipos y lo que venga en fase 1) funcionan desde el borrador, sin reescrituras.
- La UI genera ids con el mismo formato que el backend; es un formato, no una regla de negocio. Las tools MCP documentan que el agente puede proponerlos.
- Modifica la regla de ids de listas del ADR 0019.
