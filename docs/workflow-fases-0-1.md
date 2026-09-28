# Workflow: fases 0 y 1

Catálogo de **tipos de etapa**. En el proyecto, cada etapa se instancia como una **celda** dentro de un **sistema**, y las celdas se conectan con **vínculos** (esquemático tipo Ansys Workbench, ver [ADR 0009](adr/0009-esquematico-de-proyecto.md)). Cada celda tiene entradas, salidas tipadas (artefactos con esquema versionado), estado y procedencia. Puede haber varias celdas del mismo tipo (ramas y variantes).

**Estados:** `up_to_date` (actualizada) · `outdated` (desactualizada) · `failed` (fallida) · `never_run` (nunca corrida). Cambiar una entrada aguas arriba marca como `outdated` todo lo que depende de ella.

> Este documento describe el dominio. Ninguna etapa está implementada todavía.

## Fase 0 · viabilidad

| # | id | Contenido |
|---|---|---|
| 0.1 | `mission` | Órbita y actitud, modos operativos, disipaciones, límites de temperatura |
| 0.2 | `environment` | Ángulo beta, eclipse, flujos externos, casos hot/cold |
| 0.3 | `global_balance` | Nodo único, rango de temperatura, área de radiador, potencia de heaters |
| 0.4 | `tcs_concept` | Alternativas, trade-off, arquitectura. Itera a 0.3 |

## Fase 1 · dimensionamiento nodal

| # | id | Contenido |
|---|---|---|
| 1.1 | `discretization` | Nodos, masa y capacidad, propiedades ópticas |
| 1.2 | `couplings` | Conductivos, radiativos, factores de vista |
| 1.3 | `load_cases` | Operativos hot/cold, modo seguro, transitorios |
| 1.4 | `solution` | Estacionario, transitorio, chequeo contra 0.3 |
| 1.5 | `margins` | Por unidad y caso, criterios ECSS, unidades críticas |
| 1.6 | `sensitivity` | Drivers de diseño, variantes. Itera a 1.1 |

Al terminar la fase 1 los resultados pasan a Siemens NX.

## Vínculos válidos

Dentro de cada fase, cada etapa se alimenta de la anterior. Las plantillas «Fase 0» y «Fase 1» crean estas cadenas ya vinculadas; también se pueden crear celdas sueltas y vincularlas a mano. Una salida puede alimentar a varias celdas.

Transferencias entre fases:

| Desde | Hacia | Qué se transfiere |
|---|---|---|
| 0.1 `mission` | 1.1 `discretization` | Unidades → nodos |
| 0.2 `environment` | 1.3 `load_cases` | Casos de carga |
| 0.3 `global_balance` | 1.4 `solution` | Chequeo de cordura |
| 0.1 `mission` | 1.5 `margins` | Límites de temperatura para márgenes |

```
0.1 mission ─▶ 0.2 environment ─▶ 0.3 global_balance ─▶ 0.4 tcs_concept
  │  │               │                    │
  │  │               │                    └──────────────────────┐
  │  └───────────────┼───────────────────────────────┐           │
  ▼                  ▼                               ▼           ▼
1.1 discretization ─▶ 1.2 couplings ─▶ 1.3 load_cases ─▶ 1.4 solution ─▶ 1.5 margins ─▶ 1.6 sensitivity ─▶ NX
```

## Reglas del esquemático (implementadas en `hestia_project.schematic`)

- **Vínculo válido:** el tipo de la celda fuente alimenta una entrada del tipo destino (tabla de arriba), esa entrada no tiene otra fuente y el grafo sigue siendo acíclico. Cada tipo de etapa tiene una sola salida, así que la entrada se identifica por el tipo que la alimenta.
- **Plantillas:** «Fase 0 · Viabilidad» y «Fase 1 · Modelo nodal» crean el sistema con sus cadenas internas vinculadas; las transferencias entre fases quedan libres.
- **Agregar celda a un sistema:** se vincula sola con celdas del mismo sistema cuando hay un único candidato y la entrada está libre. No recrea vínculos quitados a propósito entre celdas existentes.
- **Ramificar** una plantilla o etapa desde una celda crea un **sistema nuevo** y vincula la celda de origen a toda entrada libre del sistema nuevo que acepte su tipo (p. ej. Fase 1 sobre `mission` vincula `discretization` y `margins`). Si ninguna entrada la acepta, no es un destino válido (p. ej. Fase 0 sobre `mission`: sus entradas ya están cubiertas adentro).
- **Duplicar sistema:** copia celdas (con estado), vínculos internos y vínculos entrantes desde otros sistemas; los salientes no (una fuente por entrada).
- **Eliminar:** borra la celda o el sistema con sus vínculos. Un sistema que queda sin celdas se elimina.
- **Desactualización:** vincular, desvincular o perder una fuente marca la celda afectada y todo lo aguas abajo, incluso en otros sistemas. Solo cambian las celdas con resultados (`up_to_date`, `failed` → `outdated`); `never_run` se mantiene.

## Pendientes

- Iteraciones (0.4 → 0.3, 1.6 → 1.1): no son vínculos; se resuelven editando aguas arriba o ramificando (ADR 0009). El grafo es acíclico.
- Sin gates de revisión por ahora: todo es editable siempre.
- TODO: formato del sistema de comparación y tipos detallados de cada entrada/salida.
