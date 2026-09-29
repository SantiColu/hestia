# Workflow: fases 0 y 1

Catálogo de **tipos de etapa** y reglas del esquemático. En el proyecto, cada etapa se instancia como una **celda** dentro de un **sistema**, y las celdas se conectan con **vínculos** (esquemático tipo Ansys Workbench, [ADR 0009](adr/0009-esquematico-de-proyecto.md)). Cada celda tiene un artefacto con esquema versionado, estado y procedencia. Puede haber varias celdas del mismo tipo (ramas y variantes).

**Estados:** `up_to_date` (actualizada) · `outdated` (desactualizada) · `failed` (fallida) · `never_run` (nunca corrida). Cambiar algo aguas arriba marca como `outdated` todo lo que depende de ello.

> **Estado de la implementación (2026-09-29):** el modelo de este documento (contexto por cadena, [ADR 0016](adr/0016-contexto-de-celda-por-cadena.md)) está decidido y pendiente de implementar. El código todavía usa la regla anterior de «una fuente por entrada» y no tiene la etapa `equipment`. Ninguna etapa calcula todavía; las etapas formulario (Misión, Equipos) se especifican en [ADR 0017](adr/0017-etapas-formulario.md) y en [`etapas/`](etapas/).

## Tipos de etapa

El número es metadato interno (orden de lectura y documentación): nunca se muestra en la UI ni forma parte de un id.

### Fase 0 · viabilidad

| # | id | Clase | Requiere en su contexto | Contenido |
|---|---|---|---|---|
| 0.1 | `mission` | raíz, formulario | — | Órbita, actitud, envolvente, criterios ([campos](etapas/mission.md)) |
| 0.2 | `environment` | cálculo | `mission` | Ángulo β, eclipse, flujos externos, casos hot/cold de ambiente |
| 0.3 | `equipment` | raíz, formulario | — | Modos operativos y equipos: masa, ubicación, disipación, límites ([campos](etapas/equipment.md)) |
| 0.4 | `global_balance` | cálculo | `mission`, `environment`, `equipment` | Nodo único, rango de temperatura, área de radiador, potencia de heaters |
| 0.5 | `tcs_concept` | cálculo | `global_balance` (y su contexto) | Alternativas, trade-off, arquitectura. Itera a 0.4 |

### Fase 1 · dimensionamiento nodal

| # | id | Clase | Requiere en su contexto | Contenido |
|---|---|---|---|---|
| 1.1 | `discretization` | cálculo | `mission`, `equipment`, `tcs_concept` | Nodos, masa y capacidad, propiedades ópticas |
| 1.2 | `couplings` | cálculo | `discretization` | Conductivos, radiativos, factores de vista |
| 1.3 | `load_cases` | cálculo | `couplings`, `environment`, `equipment`, `mission` | Operativos hot/cold, modo seguro, transitorios |
| 1.4 | `solution` | cálculo | `load_cases`, `global_balance` | Estacionario, transitorio, chequeo contra el balance global |
| 1.5 | `margins` | cálculo | `solution`, `equipment`, `mission` | Por equipo y caso, criterios ECSS, equipos críticos |
| 1.6 | `sensitivity` | cálculo | `margins` | Drivers de diseño, variantes. Itera a 1.1 |

Al terminar la fase 1 los resultados pasan a Siemens NX.

### Post-proceso (futuro)

| id | Clase | Descripción |
|---|---|---|
| `comparison` | colector | Compara salidas de varias celdas del mismo tipo (dos soluciones, dos balances). Formato pendiente de diseño; no está en el catálogo todavía |

Las listas «Requiere» son el punto de partida y se ajustan al implementar el cálculo de cada etapa.

## Contexto de una celda

- El **contexto** de una celda es el conjunto de celdas aguas arriba de ella (todas, no solo los padres directos), indexado por tipo: `tipo → celda que lo provee`. Un vínculo transmite todo el contexto de la fuente.
- Una celda puede correr solo si su contexto contiene todos los tipos que requiere. Si falta alguno, la API lo informa (`missing: [...]`) y la UI lo muestra en la celda.
- La procedencia de cada dato del contexto es la celda concreta que lo provee; la API expone el contexto resuelto de cada celda.

```
Fase 0 (plantilla)                                   Fase 1 (plantilla)
mission ─▶ environment ──┐
                         ├─▶ global_balance ─▶ tcs_concept ─▶ discretization ─▶ couplings ─▶ load_cases ─▶ solution ─▶ margins ─▶ sensitivity
equipment ───────────────┘
```

## Reglas del esquemático

- **Vínculo válido** de A → B, todas a la vez:
  1. El grafo sigue acíclico.
  2. B no es raíz (`mission` y `equipment` nunca tienen padres).
  3. **Padres:** B no tenía padre, o B ya tenía padres y el contexto de A (incluida A) no comparte ningún tipo con el contexto actual de B (**unión**). Los colectores aceptan varios padres del mismo tipo y no pasan contexto aguas abajo.
  4. **Sin repetidos:** el contexto resultante de B no repite tipos y no contiene el tipo de B.
  5. **Orden:** todos los tipos del contexto resultante van antes que el tipo de B en el orden del catálogo (0.1 < 0.2 < … < 0.5 < 1.1 < … < 1.6).
- **Requisitos faltantes no bloquean el vínculo:** p. ej. `mission` → `global_balance` es válido; la celda queda con `missing: [environment, equipment]` hasta que se complete (por unión).
- **Plantillas:** «Fase 0 · Viabilidad» crea las 5 celdas en orden de lectura con `mission → environment`, `environment → global_balance`, `equipment → global_balance`, `global_balance → tcs_concept`. «Fase 1 · Modelo nodal» crea la cadena lineal de sus 6 celdas.
- **Agregar celda a un sistema:** la celda nueva se vincula sola:
  1. Como destino: recorre las celdas del mismo sistema en orden inverso del catálogo y agrega cada vínculo válido hasta cubrir sus requisitos. P. ej., `global_balance` en un sistema con misión, ambiente y equipos toma `equipment` y después `environment` (unión).
  2. Como fuente: la vincula a las celdas del mismo sistema a las que les falta un requisito, si el vínculo es válido.

  No recrea vínculos quitados a propósito entre celdas existentes.
- **Ramificar** una plantilla o etapa desde una celda X crea un **sistema nuevo** y vincula X a la primera celda del sistema nuevo (en orden de catálogo) que la acepte con un vínculo válido. Si ninguna la acepta, X no es un destino válido. Ejemplos:
  - Fase 1 sobre `tcs_concept` vincula `discretization`.
  - Una etapa `environment` sobre `mission` crea una variante de ambiente.
  - Fase 0 sobre cualquier celda no es válido: sus celdas son raíces o ya tienen su padre adentro.
- **Duplicar sistema:** copia celdas (con estado y artefacto), vínculos internos y vínculos entrantes desde otros sistemas; los salientes no.
- **Eliminar:** borra la celda o el sistema con sus vínculos. Un sistema que queda sin celdas se elimina.
- **Desactualización:** vincular, desvincular o perder una fuente, o aplicar un cambio en una celda, marca todo lo aguas abajo, incluso en otros sistemas. Solo cambian las celdas con resultados (`up_to_date`, `failed` → `outdated`); `never_run` se mantiene. Las etapas formulario no se desactualizan por cambios aguas arriba: se revalidan (ADR 0017).
- **Dentro de un sistema los vínculos no se dibujan:** el orden de las celdas en el bloque ya los expresa. Entre sistemas se dibujan como conectores ortogonales.

## Migración de proyectos existentes

Sube `Project.SCHEMA_VERSION`. Al abrir un `.hestia` de la versión anterior:
- Se renumera el catálogo, que es metadato.
- Los vínculos se reevalúan en orden de creación con las reglas nuevas; los que ya no son válidos se descartan y quedan en un aviso en Mensajes, sin cambio en el historial.
- Los sistemas de plantilla Fase 0 existentes no ganan una celda `equipment` automáticamente.

## Pendientes

- Iteraciones (0.5 → 0.4, 1.6 → 1.1): no son vínculos; se resuelven editando aguas arriba o ramificando (ADR 0009). El grafo es acíclico.
- Sin gates de revisión por ahora: todo es editable siempre.
- Formato de `comparison` y tipos detallados de los artefactos de las etapas de cálculo.
