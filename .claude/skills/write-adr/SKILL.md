---
name: write-adr
description: Crea un nuevo Architecture Decision Record en docs/adr/ siguiendo la plantilla. Usala cuando se toma o cambia una decisión de arquitectura, stack, contrato o convención global.
---

# Escribir un ADR

1. Número siguiente: `ls docs/adr/` → último `NNNN` + 1, con 4 dígitos.
2. Copiá `docs/adr/0000-template.md` a `docs/adr/NNNN-slug-en-espanol.md`.
3. Completá en español, breve: **Contexto** (hechos), **Decisión** (qué, no cómo), **Consecuencias** (qué facilita, qué complica, qué queda pendiente).
4. Estado `propuesto` hasta que el usuario lo acepte. Fecha de hoy.
5. Si reemplaza a otro ADR, marcá el viejo como `reemplazado por NNNN` (única edición permitida sobre ADRs aceptados).
6. Si cambia reglas, actualizá el `AGENTS.md` y el doc de `docs/` afectados.
