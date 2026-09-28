# 0003. Humanos primero; agentes como pares vía MCP

- **Estado:** aceptado
- **Fecha:** 2026-09-28

## Contexto

El ingeniero debe ver y controlar todo. A la vez, queremos que agentes de IA (externos y el futuro agente integrado Stefan) trabajen sobre el mismo proyecto sin privilegios ni caminos especiales.

## Decisión

- La web es la interfaz principal.
- Los agentes acceden vía un servidor MCP que es un cliente más de la API REST; no importa código del backend.
- Paridad: toda operación de la web existe como tool MCP y viceversa.
- Los agentes nunca calculan números; todo resultado sale de `hestia_core` vía API.
- Toda escritura lleva autor y justificación; la UI no distingue humano de agente.

## Consecuencias

- La API debe ser completa: nada se hace "solo desde la web".
- Tools MCP de grano grueso para que los agentes trabajen por tareas de ingeniería.
- Hace falta un chequeo de paridad (subagente `parity-checker`; test automático pendiente).
