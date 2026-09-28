# Workflow: fases 0 y 1

El proyecto es un grafo de etapas (modelo Ansys Workbench). Cada etapa tiene entradas, salidas tipadas (artefactos con esquema versionado), estado y procedencia.

**Estados:** `up_to_date` (actualizada) · `outdated` (desactualizada) · `failed` (fallida) · `never_run` (nunca corrida). Cambiar una entrada aguas arriba marca como `outdated` todo lo que depende de ella.

> Este documento describe el dominio. Ninguna etapa está implementada todavía.

## Fase 0 · viabilidad

| # | id | Contenido |
|---|---|---|
| 0.1 | `mission` | Órbita y actitud, modos operativos, disipaciones, límites de temperatura |
| 0.2 | `environment` | Ángulo beta, eclipse, flujos externos, casos hot/cold |
| 0.3 | `global_balance` | Nodo único, rango de temperatura, área de radiador, potencia de heaters |
| 0.4 | `tcs_concept` | Alternativas, trade-off, arquitectura. Itera a 0.3 |

**Gate:** cierre de fase 0 (revisión).

## Fase 1 · dimensionamiento nodal

| # | id | Contenido |
|---|---|---|
| 1.1 | `discretization` | Nodos, masa y capacidad, propiedades ópticas |
| 1.2 | `couplings` | Conductivos, radiativos, factores de vista |
| 1.3 | `load_cases` | Operativos hot/cold, modo seguro, transitorios |
| 1.4 | `solution` | Estacionario, transitorio, chequeo contra 0.3 |
| 1.5 | `margins` | Por unidad y caso, criterios ECSS, unidades críticas |
| 1.6 | `sensitivity` | Drivers de diseño, variantes. Itera a 1.1 |

**Gate:** cierre de fase 1 → pase a Siemens NX.

## Dependencias

Dentro de cada fase, cada etapa depende de la anterior. Iteraciones: 0.4 → 0.3, 1.6 → 1.1.

Transferencias entre fases:

| Desde | Hacia | Qué se transfiere |
|---|---|---|
| 0.1 `mission` | 1.1 `discretization` | Unidades → nodos |
| 0.2 `environment` | 1.3 `load_cases` | Casos de carga |
| 0.3 `global_balance` | 1.4 `solution` | Chequeo de cordura |
| 0.1 `mission` | 1.5 `margins` | Límites de temperatura para márgenes |

```
0.1 mission ─▶ 0.2 environment ─▶ 0.3 global_balance ◀─▶ 0.4 tcs_concept ─▶ [gate 0]
  │  │               │                    │
  │  │               │                    └──────────────────────┐
  │  └───────────────┼───────────────────────────────┐           │
  ▼                  ▼                               ▼           ▼
1.1 discretization ─▶ 1.2 couplings ─▶ 1.3 load_cases ─▶ 1.4 solution ─▶ 1.5 margins ─▶ 1.6 sensitivity ─▶ [gate 1] ─▶ NX
  ▲                                                                                        │
  └────────────────────────────────────────────────────────────────────────────────────────┘
```

## Pendientes

- TODO: semántica exacta de los gates (quién aprueba, qué bloquea, qué pasa si algo se desactualiza tras cerrar).
- TODO: cómo se modelan las iteraciones (0.4↔0.3, 1.6→1.1) sin ciclos en el grafo de dependencias.
