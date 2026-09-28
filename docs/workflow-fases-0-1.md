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

## Pendientes

- Iteraciones (0.4 → 0.3, 1.6 → 1.1): no son vínculos; se resuelven editando aguas arriba o ramificando (ADR 0009). El grafo es acíclico.
- Sin gates de revisión por ahora: todo es editable siempre.
- TODO: formato del sistema de comparación y tipos detallados de cada entrada/salida.
