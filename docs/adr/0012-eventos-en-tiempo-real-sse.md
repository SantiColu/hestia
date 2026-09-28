# 0012. Eventos en tiempo real con Server-Sent Events

- **Estado:** propuesto
- **Fecha:** 2026-09-28

## Contexto

La UI tiene que reflejar sin recargar los cambios que hacen otros actores, en particular agentes vía MCP (ADR 0003). Estaba pendiente elegir entre SSE y WebSocket.

## Decisión

- **SSE** en `GET /events` (`text/event-stream`), con el soporte nativo de FastAPI (`EventSourceResponse`, keep-alive incluido).
- El primer evento es `connected` con la revisión actual. Luego cada cambio del workspace se emite con su tipo como nombre de evento (`project_created`, `project_opened`, `project_saved`, `project_closed`, `project_changed`) y un `ProjectEvent` JSON como dato (mensaje, revisión, ruta y, en `project_changed`, el `Change` con autor y justificación).
- Los clientes tratan el evento como aviso y vuelven a pedir `GET /session`; no reconstruyen estado a partir de los eventos.
- `stream_events` no tiene tool MCP: los agentes consultan estado e historial.

## Consecuencias

- El flujo es unidireccional, que es lo que se necesita: las escrituras siguen siendo REST y pasan por el mismo contrato. `EventSource` reconecta solo y funciona en el webview de Tauri sin dependencias.
- Un cliente lento pierde eventos (cola acotada) pero se pone al día al refrescar con el siguiente.
- Si en el futuro hace falta canal bidireccional (p. ej. progreso de corridas con cancelación), se reevalúa WebSocket.
