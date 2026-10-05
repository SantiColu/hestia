# 0024. Justificación solo para agentes

- **Estado:** propuesto
- **Fecha:** 2026-10-05

## Contexto

El ADR 0011 exigía una justificación no vacía en las escrituras destructivas (eliminar sistema o celda, desvincular) y el ADR 0017 la sumó al aplicar un artefacto. En la UI eso eran diálogos (`ConfirmChangeDialog`) al eliminar, cortar, desvincular y aplicar, y un campo opcional al renombrar. En el uso diario resultan molestos: la persona ya decide el cambio con la acción, y todo cambio se puede deshacer desde el historial. Para los agentes la justificación sí sirve: explica a la persona por qué un actor externo cambió su proyecto.

## Decisión

- El autor sigue viajando en los headers `X-Hestia-Actor-Kind` (`human` | `agent`) y `X-Hestia-Actor`, como en el ADR 0011. Todo cambio registra autor y justificación (que puede ir vacía).
- La justificación no vacía es obligatoria **solo para agentes**, en las mismas operaciones: eliminar sistema o celda, desvincular y aplicar un artefacto (`hestia_project.history.JUSTIFICATION_REQUIRED`). A un humano nunca se le exige.
- En la API, `justification` es opcional en el cuerpo (vacía por defecto). Las tools MCP de escritura la siguen pidiendo siempre.
- La UI no pide justificación en ninguna escritura: eliminar, cortar, desvincular y aplicar se ejecutan directo y se revierten con Deshacer. Renombrar pide solo el nombre. El historial muestra la justificación cuando la hay.

## Consecuencias

- Menos fricción para las personas; el resguardo pasa a ser Deshacer y el historial.
- La UI ya no muestra antes de aplicar qué celdas aguas abajo se desactualizan (`outdates` sigue en la API para agentes y para una UI futura que lo muestre sin bloquear); el esquemático las marca desactualizadas al aplicar.
- Reemplaza al ADR 0011 y modifica la justificación obligatoria al aplicar del ADR 0017 (y el principio 7 de `AGENTS.md`).
- En Pencil se quitan `Field/Justification` y el frame «Workspace · Misión (aplicar)»; `Dialog` queda como confirmación simple.
