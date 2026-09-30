# Etapa 0.1 · Misión (`mission`): campos

> **Implementado (2026-09-29):** modelo `hestia_core.mission.MissionArtifact` (v1), validación `validate_mission` con estos códigos (más `format` para el LTAN y `duplicate` para caras repetidas), API y tools MCP (ADR 0019) y formulario en la UI. Pendiente: popover de procedencia e historial por campo. Comportamiento de edición, validación, estado y procedencia: [ADR 0017](../adr/0017-etapas-formulario.md). Lo marcado *(propuesta)* se decidió sin revisión y puede cambiar. Los campos se revisan cuando se implementen las etapas que los consumen.
>
> **Cambio en curso ([ADR 0023](../adr/0023-orbita-y-actitud-en-entorno.md)):** la órbita y los modos de actitud pasan a los parámetros de [Entorno](environment.md). Implementado en backend, API y MCP (2026-09-30): `MissionArtifact` v2.

La etapa es un formulario: su artefacto es exactamente lo cargado, validado. **No calcula nada** (ni disipación total por modo, ni rango común de temperatura, ni unidades críticas): cada derivado vive en la etapa que lo usa (p. ej. `global_balance`). Solo valida consistencia.

La lista de equipos y los modos operativos (qué está encendido y cuánto disipa) **no** van acá: son otra raíz del esquemático, [Equipos](equipment.md) ([ADR 0016](../adr/0016-contexto-de-celda-por-cadena.md)). La órbita y los modos de actitud tampoco: son parámetros de [Entorno](environment.md) (ADR 0023), así una Misión alimenta varias variantes de órbita sin duplicarse. Qué actitud corresponde a cada modo operativo se elige al armar los casos (`global_balance`, `load_cases`).

## Convenciones

- **Secciones:** agrupan los campos en el formulario. La clave (`general`, `envelope`…) es la del artefacto.
- **Unidades:** se guardan en SI y temperaturas en K; la columna indica `interna → UI`. La normalización (pint) distingue temperatura absoluta (°C → K, +273.15) de diferencia de temperatura (ΔT: 5 °C = 5 K).
- **Listas:** cada elemento tiene un `id` generado por el backend (inmutable) y un `name` editable, único dentro de su lista. Las referencias entre objetos usan el `id`.
- **Procedencia:** cada valor registra de dónde viene (`entered`, `imported`, `default`) y el cambio que lo fijó (ADR 0017). Los defaults de biblioteca están marcados en cada tabla.
- **Tiempo:** `time` se guarda como texto `HH:MM` (00:00–23:59). Las duraciones se guardan en s; un año son 365,25 días.

### Tipos

| Tipo | Significado |
|---|---|
| `str` | Texto de una línea |
| `text` | Texto multilínea |
| `bool` | Sí / no |
| `int`, `float` | Número entero / real |
| `date` | Fecha (AAAA-MM-DD) |
| `time` | Hora del día (HH:MM) |
| `enum` | Uno de un conjunto cerrado (ver [Enumeraciones](#enumeraciones)) |
| `ref(X)` | `id` de un elemento de la lista X |
| `list[T]` | Lista de T |
| `map[K, T]` | Un T por cada K |

## 1. General (`general`)

| Campo | Tipo | Unidad | Oblig. | Descripción |
|---|---|---|---|---|
| `description` | `text` | — | no | Objetivo y notas generales |
| `launch_date` | `date` | — | sí | Fecha de lanzamiento prevista. Define las estaciones que recorre la misión (flujo solar, historia de β) |
| `design_life` | `float` | s → años | sí | Vida útil de diseño. Define el fin de vida (degradación de recubrimientos, EOL) |

## 2. Envolvente (`envelope`)

Caja envolvente alineada con los ejes del cuerpo. Sus caras (+X…−Z) son las que usan los modos de actitud de Entorno, la ubicación de los equipos y las caras de radiador.

| Campo | Tipo | Unidad | Oblig. | Descripción |
|---|---|---|---|---|
| `size_x` | `float` | m | sí | Dimensión según X |
| `size_y` | `float` | m | sí | Dimensión según Y |
| `size_z` | `float` | m | sí | Dimensión según Z |
| `mass` | `float` | kg | sí | Masa total del satélite en órbita, al inicio de vida |

## 3. Criterios y restricciones (`criteria`)

| Campo | Tipo | Unidad | Oblig. | Descripción |
|---|---|---|---|---|
| `uncertainty_margin` | `float` (ΔT) | K | sí | Margen de incertidumbre de las predicciones. Default de biblioteca: 10 K (ECSS-E-ST-31C, modelo sin correlacionar) |
| `acceptance_margin` | `float` (ΔT) | K | sí | Margen de aceptación. Default de biblioteca: 5 K |
| `qualification_margin` | `float` (ΔT) | K | sí | Margen de calificación, sobre el de aceptación. Default de biblioteca: 5 K |
| `heater_power_budget` | `float` | W | no | Potencia disponible para heaters (promedio orbital) |
| `tcs_mass_budget` | `float` | kg | no | Masa disponible para el TCS |
| `radiator_faces` | `list[enum Face]` | — | no | Caras donde se permite ubicar radiadores. Vacío: sin restricción |

Cómo se aplican los márgenes a los límites de los equipos (qué rango se compara con qué) se define en `global_balance` y `margins`; acá solo se fija la política. Los valores por defecto hay que verificarlos contra la norma.

## Formulario

Una sola columna con scroll y las secciones en este orden (diseño en `app/design/workspace.pen`, frames «Workspace · Misión (…)»).
- **Criterios:** los defaults de biblioteca se marcan como tales hasta que se cambian *(propuesta)*.

Los campos cambiados en el borrador muestran el valor aplicado debajo. Los problemas de la validación en seco se muestran en su campo y en un resumen arriba.

## Enumeraciones

| Enum | Valores |
|---|---|
| `Face` | `+X`, `-X`, `+Y`, `-Y`, `+Z`, `-Z` |

`Axis`, `OrbitType` y `Target` pasan a [Entorno](environment.md#enumeraciones).

## Validaciones de consistencia

Validar no es calcular: ninguna de estas reglas produce un valor nuevo. Cada problema tiene `path`, `code` estable y mensaje (ADR 0017). Códigos: `required`, `min`, `duplicate`.

**General**
- `design_life` > 0.
- Obligatorios según la tabla.

**Envolvente**
- Dimensiones y `mass` > 0.

**Criterios**
- Márgenes ≥ 0; presupuestos (si están) ≥ 0; `radiator_faces` sin repetidos.

## Fuera de Misión (y dónde va)

| Dato | Etapa |
|---|---|
| Modos operativos y lista de equipos: masa, ubicación, disipación por modo, límites de temperatura | `equipment` ([borrador](equipment.md)) |
| Qué actitud y qué modo operativo forman cada caso | `global_balance` (hot/cold), `load_cases` |
| Disipación total por modo, rango común de temperatura | `global_balance` (se calculan ahí) |
| Órbita, modos de actitud, constante solar, albedo, OLR, ángulo β, eclipse, condiciones extremas de ambiente | `environment` |
| Propiedades ópticas (α, ε), recubrimientos, degradación BOL/EOL | `global_balance` / `tcs_concept` / `discretization` (Misión aporta `design_life`) |
| Paneles solares y apéndices desplegables (geometría, sombras) | `discretization` / `couplings` (evaluar si `environment` los necesita) |
| Montaje, interfaces y conductancias de contacto | `couplings` |
| Ciclos de trabajo dentro de la órbita, perfiles y picos de disipación | `load_cases` |
| Punto de referencia de temperatura (TRP) por equipo, equipos críticos | `margins` |

**Supuestos a revisar** (se agregan si aparece un caso que los necesite): envolvente no prismática.
