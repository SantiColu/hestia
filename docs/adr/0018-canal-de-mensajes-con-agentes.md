# 0018. Canal de mensajes entre humanos y agentes

- **Estado:** propuesto
- **Fecha:** 2026-09-29

## Contexto

El dock derecho de la UI pasa a ser solo el chat con el agente conectado (Stefan u otro vía MCP; `docs/ux-workspace.md`). Por el ADR 0015, ni la web ni el backend pueden depender de un componente de IA: el chat no puede hablar con un modelo. Los agentes son externos y solo acceden a Hestia por el MCP, que es un cliente de la API.

## Decisión

- **El chat es un canal de mensajes del proyecto:** la API guarda y reenvía mensajes; no los interpreta.
- **Mensaje:** `{id, author, text, created_at, reply_to?}`. El autor es un actor (humano o agente, ADR 0011). Los mensajes se guardan en el `.hestia` como parte del proyecto, fuera del historial de cambios: no se deshacen ni ensucian el proyecto (no cambian `dirty`).
- **API:** listar mensajes (paginado) y publicar un mensaje. Cada mensaje publicado emite un evento SSE (`message_posted`, ADR 0012), así la UI y cualquier otro cliente lo ven en vivo.
- **MCP:** tools para leer los mensajes nuevos y responder. El agente decide cuándo leer; Hestia no lo despierta ni lo invoca.
- **Presencia:** un agente que usa el MCP se registra como conectado (actor, nombre, última actividad) y la UI lo muestra en el encabezado del chat. Sin agente conectado, el chat muestra que no hay agente y permite dejar mensajes igual.
- **Cambios del agente en el chat:** la UI intercala en el hilo los cambios del historial hechos por agentes (autor, diff, justificación), leyendo el historial; no son mensajes nuevos.

## Consecuencias

- La regla del ADR 0015 se mantiene: la web y el backend solo guardan y muestran texto. Sin MCP ni agente, Hestia funciona igual y el chat queda como notas del proyecto.
- El agente responde a su ritmo (polling por MCP); no hay respuesta en tiempo real garantizada.
- Pendiente: menciones a celdas o campos dentro de un mensaje, adjuntos y varios agentes conectados a la vez.
