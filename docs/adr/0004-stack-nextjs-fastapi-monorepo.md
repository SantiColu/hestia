# 0004. Stack Next.js (interfaz) + FastAPI (dominio) en monorepo

- **Estado:** aceptado
- **Fecha:** 2026-09-28

## Contexto

El ecosistema científico está en Python; la mejor experiencia de UI interactiva (grafos, gráficos) está en React. Se necesita un contrato único entre ambos y el MCP.

## Decisión

- Backend: Python 3.12, uv workspace (`hestia_core`, `hestia_project`, `hestia_adapters`, `hestia_api`), FastAPI, pydantic v2.
- Web: Next.js (App Router), TypeScript estricto, Tailwind, pnpm. Sin lógica de dominio.
- MCP: proyecto uv independiente.
- Contrato: pydantic → OpenAPI (`shared/openapi.json`) → cliente TS y tools MCP.
- Todo en un monorepo.

## Consecuencias

- Dos toolchains (uv y pnpm) orquestadas por `Makefile`.
- Las reglas de capas del backend se verifican con import-linter.
- Pendiente: generador del cliente TS y canal de tiempo real (SSE/WebSocket).
