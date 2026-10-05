# Etapa Equipos (`equipment`): campos

> **Especificación para implementar (2026-09-29).** Etapa decidida ([ADR 0016](../adr/0016-contexto-de-celda-por-cadena.md)) y sin implementar. Edición, validación, estado y procedencia: [ADR 0017](../adr/0017-etapas-formulario.md). Lo marcado *(propuesta)* se decidió sin revisión y puede cambiar. Convenciones y tipos: los de [mission.md](mission.md#convenciones).

Formulario, como Misión: su artefacto es lo cargado (o importado de la planilla del proyecto, CSV/Excel), validado. No calcula nada: la disipación total por modo y el rango común de temperatura se calculan en `global_balance`. En 1.1 cada equipo se convierte en nodos.

Es una **raíz** del esquemático, como Misión: no tiene entradas y se une con la rama misión → ambiente en `global_balance`. Por eso una misma lista de equipos puede alimentar variantes de ambiente, y viceversa. Qué actitud corresponde a cada modo operativo se elige al armar los casos (`global_balance`, `load_cases`).

## Modos operativos (`operating_modes`): `list`, al menos uno

| Campo | Tipo | Unidad | Oblig. | Descripción |
|---|---|---|---|---|
| `id` | `str` | — | — | Generado |
| `name` | `str` | — | sí | P. ej. «Nominal», «Adquisición», «Modo seguro» |
| `max_duration` | `float` | s → h | no | Duración máxima del modo. Vacío: puede durar indefinidamente (estacionario) |

## Equipos (`items`): `list`, al menos uno

Valores **por ítem**: con `quantity` > 1, cada ítem tiene la masa, la disipación y los límites indicados. Al principio de la fase 0, sin lista de equipos, alcanza con uno agregado («Plataforma», con la disipación total por modo).

| Campo | Tipo | Unidad | Oblig. | Descripción |
|---|---|---|---|---|
| `id` | `str` | — | — | Generado |
| `name` | `str` | — | sí | P. ej. «Rueda de reacción», «Transmisor banda X» |
| `subsystem` | `enum Subsystem` | — | sí | Subsistema al que pertenece |
| `quantity` | `int` | — | sí | Cantidad de ítems idénticos. Por defecto 1 |
| `mass` | `float` | kg | sí | Masa por ítem |
| `location` | `enum Location` | — | sí | Cara donde va montado, o `internal` |
| `modes` | `map[ref(operating_modes), ModeState]` | — | sí | Estado y disipación en cada modo operativo |
| `operating_min` | `float` | K → °C | sí | Temperatura mínima operativa |
| `operating_max` | `float` | K → °C | sí | Temperatura máxima operativa |
| `non_operating_min` | `float` | K → °C | no | Temperatura mínima no operativa (apagado) |
| `non_operating_max` | `float` | K → °C | no | Temperatura máxima no operativa (apagado) |
| `switch_on_min` | `float` | K → °C | no | Temperatura mínima para encenderlo |

**`ModeState`** (una entrada por equipo y modo operativo):

| Campo | Tipo | Unidad | Oblig. | Descripción |
|---|---|---|---|---|
| `on` | `bool` | — | sí | Encendido en ese modo (define qué límites aplican: operativos o no operativos) |
| `dissipation` | `float` | W | sí | Disipación media en el modo, por ítem |

## Enumeraciones

| Enum | Valores |
|---|---|
| `Location` | las caras de `Face` (ver Misión), más `internal` |
| `Subsystem` | `payload` (carga útil), `power` (potencia), `obdh` (computadora de a bordo), `ttc` (comunicaciones), `aocs` (control de actitud), `propulsion` (propulsión), `thermal` (térmico), `structure` (estructura), `other` (otro) |

## Validaciones de consistencia

- Nombres únicos en cada lista; `quantity` ≥ 1; `mass` ≥ 0.
- `modes` tiene exactamente una entrada por modo operativo: ni faltan ni sobran.
- `dissipation` ≥ 0; si `on` es `false`, `dissipation` = 0.
- `operating_min` < `operating_max`.
- Límites no operativos: los dos o ninguno; si están, contienen al rango operativo.
- `switch_on_min` ≤ `operating_max` y, si hay límites no operativos, `switch_on_min` ≥ `non_operating_min`.

## Comportamiento *(propuesta)*

- **Agregar un modo operativo:** cada equipo recibe una entrada `{on: false, dissipation: 0}` para ese modo.
- **Eliminar un modo operativo:** se borran sus entradas en todos los equipos.

Las dos operaciones son parte del mismo borrador y se aplican juntas.

## Formulario *(propuesta)*

- **Modos operativos:** tabla editable (nombre, duración máxima).
- **Equipos:** una fila por equipo con nombre, subsistema, cantidad, masa, ubicación y límites operativos, y una columna por modo operativo con la disipación. Una disipación vacía o el interruptor apagado significan `on: false`. Los límites opcionales y la temperatura de encendido van al expandir la fila.
- **Totales:** no se muestran (masa total, disipación por modo). Son cálculos y viven en `global_balance`.

## Importar planilla *(propuesta, prioridad baja)*

- CSV o XLSX con una fila de encabezados. Las columnas se reconocen por nombre (en español o en inglés, sin distinguir mayúsculas) y la unidad va entre corchetes:

  | Columna | Unidad |
  |---|---|
  | `name` / `nombre` | — |
  | `subsystem` / `subsistema` | — |
  | `quantity` / `cantidad` | — |
  | `mass` / `masa` | `[kg]` o `[g]` |
  | `location` / `ubicación` | — |
  | `operating_min`, `operating_max`, `non_operating_min`, `non_operating_max`, `switch_on_min` | `[°C]` o `[K]` |
  | una columna por modo operativo | `[W]` |

  En las columnas de modo, el valor es la disipación; vacío u `off` significan apagado.
- Las unidades se normalizan con pint (°C → K como temperatura absoluta). Los modos que no existen se crean.
- La API recibe el archivo y devuelve el borrador con sus problemas, sin cambiar el proyecto (lo mismo como tool MCP).
- El resultado es un **borrador**, no se aplica solo: el usuario lo revisa y lo aplica. La procedencia de lo importado queda como `imported`.
- Los errores de la planilla (columna desconocida, unidad inválida, valor no numérico) se informan por fila y columna, sin importar nada parcial.

## Abierto

- Mapeo de columnas configurable al importar, si las planillas reales no siguen los encabezados de arriba.
- Límite máximo de encendido.
- Validaciones cruzadas con Misión (Σ `mass` × `quantity` ≤ masa del satélite): van en `global_balance`, donde se unen las dos raíces.
