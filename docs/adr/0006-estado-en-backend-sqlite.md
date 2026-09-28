# 0006. El backend es dueño del estado (SQLite + log de cambios)

- **Estado:** aceptado
- **Fecha:** 2026-09-28

## Contexto

Varios actores (humanos y agentes) modifican el mismo proyecto. Se necesita historial con autor y justificación, deshacer, y notificación en tiempo real. Usar git como almacenamiento primario complicaría la concurrencia y el deshacer fino.

## Decisión

- El backend es la única fuente de verdad del estado del proyecto.
- Persistencia en SQLite con un log de cambios (autor, justificación, timestamp, diff).
- Git se usa solo para exportar snapshots del proyecto.

## Consecuencias

- Web y MCP nunca escriben archivos del proyecto directamente.
- El log habilita historial, deshacer y eventos en tiempo real.
- No implementado todavía; el esquema del log se definirá en un ADR posterior.
