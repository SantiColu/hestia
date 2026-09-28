# 0011. Autoría y justificación de las escrituras

- **Estado:** propuesto
- **Fecha:** 2026-09-28

## Contexto

Todo cambio debe registrar autor y justificación (principio 7, ADR 0003), y la UI no distingue humanos de agentes. La skill `add-api-operation` dejaba como TODO cómo identifica la API al autor. Mientras Hestia sea una app local de un solo usuario no hay cuentas ni sesiones.

## Decisión

- El autor viaja en headers de cada request: `X-Hestia-Actor-Kind` (`human` | `agent`, por defecto `human`) y `X-Hestia-Actor` (nombre; por defecto el usuario del sistema operativo que corre la API).
- La UI no manda headers: el autor es la persona que usa la máquina. El MCP manda `agent` y el nombre de `HESTIA_AGENT_NAME`.
- Toda escritura del esquemático lleva `justification` en el cuerpo. La API la exige como campo; puede ir vacía en operaciones chicas (crear, mover, renombrar, vincular, deshacer) y es obligatoria no vacía en las destructivas (eliminar sistema o celda, desvincular). La regla vive en `hestia_project.history.JUSTIFICATION_REQUIRED`.
- Las tools MCP de escritura piden siempre `justification`.

## Consecuencias

- El header no autentica: cualquier cliente local puede declararse agente o humano. Alcanza para una app local; si Hestia pasa a multiusuario hace falta autenticación real (y reemplazar este ADR).
- El tipo de autor se guarda para auditoría, pero la UI muestra a todos igual.
