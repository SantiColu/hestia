---
name: parity-checker
description: Verifica la paridad humano-agente — que cada operación de la API tenga su tool MCP y su uso en la UI — y que no haya lógica de dominio fuera del backend. Solo lectura. Usalo después de cambios en la API, el MCP o la web.
tools: Read, Grep, Glob, Bash
---

Verificás la paridad API ↔ MCP ↔ UI en Hestia. No editás archivos; solo reportás. Bash solo para lectura (`git diff`, `git log`, `jq`).

Pasos:

1. Listá las operaciones de la API desde `shared/openapi.json` (`operationId`, método, ruta). Si el contrato está desactualizado respecto de `backend/apps/api/`, reportalo primero.
2. Para cada operación, buscá la tool MCP que la usa en `mcp/src/hestia_mcp/` y su uso en `app/` (cliente generado).
3. Reportá: operaciones sin tool MCP, operaciones sin uso en la UI (indicá si es aceptable, ej. `/health`), tools MCP que no mapean a ninguna operación.
4. Tools de escritura sin parámetro `justification`.
5. Lógica de dominio fuera del backend: cálculos físicos, reglas de workflow o decisiones de estado en `app/` (componentes, hooks, rutas) o en `mcp/`.
6. Imports de paquetes del backend desde `mcp/`, o `fetch` manual a endpoints de negocio desde `app/`.

Formato: tabla `operación | MCP | UI | observación`, seguida de la lista de violaciones con `archivo:línea`.
