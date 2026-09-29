# 0015. Hestia es un sistema determinístico sin dependencias de IA

- **Estado:** propuesto
- **Fecha:** 2026-09-28

## Contexto

Hestia produce resultados de ingeniería (dimensionamiento térmico) que tienen que ser reproducibles, testeables y trazables. Los agentes de IA (externos y el futuro Stefan) trabajan sobre los proyectos como pares de los humanos (ADR 0003), a través del MCP, que es un cliente HTTP de la API. Nada impedía todavía que el backend o la web incorporaran un SDK o framework de IA y metieran un modelo dentro del loop del sistema.

## Decisión

- El backend y la web no dependen de ningún componente de IA: ni SDKs de modelos (Anthropic, OpenAI, Vercel AI SDK), ni frameworks de agentes u orquestación (LangChain, LlamaIndex, LiteLLM, Pydantic AI), ni modelos locales (transformers), ni observabilidad de IA (Logfire). La librería `pydantic` base sí se permite: es la validación de datos del contrato.
- Los agentes son actores externos: operan vía MCP → API REST, con los mismos permisos y la misma trazabilidad (autor y justificación) que un humano.
- El MCP es opcional: si no se levanta, Hestia funciona igual. `mcp/` es la única frontera donde puede vivir código relacionado con agentes y queda fuera de esta regla.
- La regla se verifica automáticamente en `make lint` y `make test`.

## Consecuencias

- Todo resultado sale de código determinístico y testeable; ningún número depende de un modelo.
- La paridad humano-agente se garantiza por construcción: el agente no tiene otro camino que la API.
- Verificación en el backend: contrato `forbidden` de import-linter con paquetes externos (imports) y `backend/tests/test_no_ai_dependencies.py` (dependencias declaradas y `uv.lock`, incluidas las transitivas). En la web: `no-restricted-imports` de ESLint (imports) y `app/scripts/check-no-ai.mjs` (`package.json` y `pnpm-lock.yaml`), que corre con `pnpm lint`.
- Las listas de paquetes prohibidos se mantienen a mano y cubren lo conocido hoy; un producto nuevo de IA necesita agregarse. Si una librería legítima pasa a depender de un paquete prohibido, el chequeo del lock falla y hay que decidir caso por caso.
- Stefan, cuando exista, es un cliente más del MCP/API (fuera del backend y de la web), no un módulo de Hestia.
