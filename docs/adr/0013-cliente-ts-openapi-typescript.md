# 0013. Cliente TypeScript: openapi-typescript + openapi-fetch

- **Estado:** propuesto
- **Fecha:** 2026-09-28

## Contexto

La UI consume la API solo mediante un cliente generado desde `shared/openapi.json` (principio 5). Estaba pendiente elegir el generador entre openapi-typescript, orval y hey-api.

## Decisión

- `openapi-typescript` genera solo tipos (`app/src/api/schema.gen.ts`) a partir del contrato; `openapi-fetch` (runtime de ~6 kB) los usa para tipar rutas, parámetros, cuerpos y respuestas.
- `make contract` exporta el OpenAPI y regenera los tipos (`scripts/generate-client.sh`). El archivo generado no se edita ni se lintea.
- `app/src/api/client.ts` es el único punto de acceso: base URL, desenvolver errores (`ApiError` con `code`) y alias de tipos del contrato.

## Consecuencias

- Sin código generado que mantener ni plantillas: cambiar el contrato y correr `make contract` rompe el typecheck donde la UI quedó desalineada.
- No genera hooks de datos (como orval o hey-api con TanStack Query); el estado del proyecto se maneja a mano en la UI. Se reevalúa si la cantidad de consultas crece.
