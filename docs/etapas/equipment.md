# Etapa Equipos (`equipment`): campos

> **Implementada (2026-10-05):** modelo, validación de los equipos y sus modos, defaults, ids propuestos y editor (sección Equipos). Etapa decidida ([ADR 0016](../adr/0016-contexto-de-celda-por-cadena.md)). Reemplaza la versión del 2026-09-29 (disipación por equipo y modo operativo): ahora cada equipo tiene sus propios modos y cada modo operativo del satélite es una configuración que elige el modo de cada equipo. Edición, validación, estado y procedencia: [ADR 0017](../adr/0017-etapas-formulario.md). Ids propuestos por el cliente: [ADR 0025](../adr/0025-ids-propuestos-por-el-cliente.md). Diseño: `app/design/workspace.pen`, frame «Workspace · Equipos (borrador)». Lo marcado *(propuesta)* se decidió sin revisión y puede cambiar. Convenciones y tipos: los de [mission.md](mission.md#convenciones), salvo los ids (ver abajo).

Formulario, como Misión: su artefacto es lo cargado (o, más adelante, importado de la planilla del proyecto), validado. Lo único derivado que devuelve es la disipación total de cada modo operativo (ver [Derivados](#derivados)), calculada en el backend; el rango común de temperatura y el resto de los cálculos viven en `global_balance`. En 1.1 cada equipo se convierte en nodos.

Es una **raíz** del esquemático, como Misión: no tiene entradas y se une con la rama misión → ambiente en `global_balance`. Por eso una misma lista de equipos puede alimentar variantes de ambiente, y viceversa. Qué actitud corresponde a cada modo operativo se elige al armar los casos (`global_balance`, `load_cases`).

## Modelo

Dos niveles:

1. **Equipos (`items`)** con sus **modos propios** (`items[].modes`): lo que dice la hoja de datos del componente. P. ej. una rueda de reacción: Standby 3 W, Nominal 8 W, Pico 20 W.
2. **Modos operativos (`operating_modes`)**: configuraciones del satélite entero. Cada uno dice en qué modo está cada equipo, o si está apagado. P. ej. «Adquisición»: ruedas en Pico, transmisor en Recepción, batería en Carga.

Así la disipación de un modo de equipo se carga una vez y los modos operativos solo la eligen.

**Apagado implícito:** todo equipo tiene además el estado **Apagado**, que no se carga: 0 W y se verifican sus límites no operativos. Todo modo cargado cuenta como encendido (límites operativos). Un equipo que disipa algo «apagado» (p. ej. un calentador de supervivencia propio) se carga como un modo más (p. ej. «Supervivencia», 0.5 W), que se verifica con los límites operativos: del lado conservador.

**Cantidad:** con `quantity` > 1, los ítems idénticos están siempre en el mismo modo. Si hacen falta estados distintos (p. ej. 3 ruedas encendidas y 1 apagada), se cargan como dos filas. La UI muestra siempre la cantidad junto al nombre («Rueda de reacción × 4»).

## Ids

Equipos, modos de equipo y modos operativos tienen `id`. Como el artefacto tiene referencias internas, el cliente (UI o agente) puede proponer el id de un ítem nuevo; el backend lo conserva si tiene formato válido y no está repetido, y genera el que falte ([ADR 0025](../adr/0025-ids-propuestos-por-el-cliente.md)). Prefijos *(propuesta)*: `item`, `imode` (modo de equipo), `opmode`.

## Equipos (`items`): `list`, al menos uno

Valores **por ítem**: con `quantity` > 1, cada ítem tiene la masa, la disipación y los límites indicados.

| Campo | Tipo | Unidad | Oblig. | Descripción |
|---|---|---|---|---|
| `id` | `str` | — | — | Propuesto por el cliente o generado |
| `name` | `str` | — | sí | P. ej. «Rueda de reacción», «Transmisor banda X» |
| `subsystem` | `enum Subsystem` | — | sí | Subsistema al que pertenece |
| `quantity` | `int` | — | sí | Cantidad de ítems idénticos. Por defecto 1 |
| `mass` | `float` | kg | sí | Masa por ítem |
| `location` | `enum Location` | — | sí | Cara donde va montado, o `internal` |
| `modes` | `list[ItemMode]` | — | sí, al menos uno | Modos propios del equipo (encendido) |
| `operating_min` | `float` | K → °C | sí | Temperatura mínima operativa |
| `operating_max` | `float` | K → °C | sí | Temperatura máxima operativa |
| `non_operating_min` | `float` | K → °C | no | Temperatura mínima no operativa (apagado) |
| `non_operating_max` | `float` | K → °C | no | Temperatura máxima no operativa (apagado) |
| `switch_on_min` | `float` | K → °C | no | Temperatura mínima para encenderlo |

**`ItemMode`** (modo propio de un equipo):

| Campo | Tipo | Unidad | Oblig. | Descripción |
|---|---|---|---|---|
| `id` | `str` | — | — | Propuesto por el cliente o generado |
| `name` | `str` | — | sí | P. ej. «Standby», «Nominal», «Pico» |
| `dissipation` | `float` | W | sí | Disipación media en ese modo, por ítem |

## Modos operativos (`operating_modes`): `list`, al menos uno

| Campo | Tipo | Unidad | Oblig. | Descripción |
|---|---|---|---|---|
| `id` | `str` | — | — | Propuesto por el cliente o generado |
| `name` | `str` | — | sí | P. ej. «Nominal», «Adquisición», «Modo seguro» |
| `max_duration` | `float` | s → h | no | Duración máxima del modo. Vacío: puede durar indefinidamente (estacionario) |
| `states` | `map[ref(items), ref(items[].modes) \| null]` | — | sí | Modo de cada equipo en este modo operativo; `null` es Apagado |

## Enumeraciones

| Enum | Valores |
|---|---|
| `Location` | las caras de `Face` (ver Misión), más `internal` |
| `Subsystem` | `payload` (carga útil), `power` (potencia), `obdh` (computadora de a bordo), `ttc` (comunicaciones), `aocs` (control de actitud), `propulsion` (propulsión), `thermal` (térmico), `structure` (estructura), `other` (otro) |

## Validaciones de consistencia

- Al menos un equipo y un modo operativo; cada equipo con al menos un modo.
- Nombres únicos en `items` y en `operating_modes`; nombres de modo únicos dentro de cada equipo.
- `quantity` ≥ 1; `mass` ≥ 0; `dissipation` ≥ 0.
- `states` tiene exactamente una entrada por equipo: ni faltan ni sobran (claves que no son equipos del artefacto).
- Cada valor de `states` es `null` o el id de un modo **de ese equipo**.
- `operating_min` < `operating_max`.
- Límites no operativos: los dos o ninguno; si están, contienen al rango operativo.
- `switch_on_min` ≤ `operating_max` y, si hay límites no operativos, `switch_on_min` ≥ `non_operating_min`.

## Derivados

El backend (`hestia_core`, con test) calcula la **disipación total de cada modo operativo**: Σ `quantity` × `dissipation` del modo elegido de cada equipo (Apagado = 0). Se devuelve junto al artefacto al leerlo y al validar un borrador en seco, así la UI la muestra mientras se edita (con el mismo *debounce* de la validación) y los agentes la leen por MCP sin calcular. Es la misma suma que usa `global_balance`. Con referencias inválidas, el total del modo afectado no se informa (o se informa sin esos equipos) *(propuesta)*.

## Comportamiento al editar *(propuesta)*

Ajustes del borrador que hace el editor; el backend solo valida.

- **Agregar un equipo:** entra en cada modo operativo como Apagado.
- **Eliminar un equipo:** se borra su entrada en todos los modos operativos.
- **Eliminar un modo de equipo:** los modos operativos que lo usaban pasan a Apagado para ese equipo.
- **Agregar un modo operativo:** todos los equipos empiezan en Apagado.
- **Eliminar un modo operativo:** se borra con su configuración.

Todo es parte del mismo borrador y se aplica junto.

## Celda nueva

Default de una celda nueva: un equipo «Plataforma» con un modo «Nominal» y un modo operativo «Nominal» que lo usa. Al principio de la fase 0, sin lista de equipos, alcanza con ese equipo agregado y su disipación total. Los campos obligatorios sin default (masa, límites, disipación…) quedan vacíos y la validación los pide.

## Pantalla

Editor propio de la etapa (no el formulario genérico: la matriz y la trasposición no entran en él), con las reglas de siempre: la UI no decide, el backend valida y los errores llegan por ruta. Ocupa todo el ancho del editor. Diseño: frame «Workspace · Equipos (borrador)».

- **Equipos** (arriba): tabla con una fila por equipo: nombre, cantidad, subsistema, masa, ubicación, T operativa mín/máx y la **cantidad de modos** («3 modos»). Borrar fila y «Agregar equipo».
  - **Fila expandible** (chevron): a la izquierda, los modos del equipo (tabla con nombre y disipación en W, borrar y «Agregar modo»), con la nota «Apagado está siempre disponible: 0 W, con los límites no operativos»; a la derecha, los límites opcionales (T no operativa mín/máx, T de encendido mín).
- **Modos operativos** (abajo): matriz con una fila por equipo («nombre × cantidad») y una columna por modo operativo.
  - **Encabezado** de cada columna en dos renglones: nombre con un lápiz para renombrar, y debajo la disipación total del modo («Σ 45 W») con un indicador de 5 segmentos que compara los modos operativos entre sí (relativo al de mayor total).
  - Primera fila: **duración máxima** en h («—» = sin límite).
  - **Celdas:** desplegable con los modos del equipo más Apagado. Muestra el modo, los W por ítem y un indicador de 5 segmentos relativo a la mayor disipación por ítem de la tabla (color `hot`); Apagado atenuado y sin indicador. El mismo indicador va en la tabla de modos del equipo.
  - Borrar columna (última fila) y «Agregar modo operativo».
  - **Trasponer** (equipos en filas ↔ modos en filas): control «Filas: Equipos | Modos»; solo de vista.
  - Texto de ayuda: qué es un modo operativo, que Apagado usa los límites no operativos y qué comparan Σ y las barras.
- Los indicadores son presentación (proporción respecto del máximo visible), no cálculos físicos; los totales vienen del backend.
- Encabezado, estado, resumen de errores y barra de borrador (Descartar / Aplicar) como en Misión.

## API y MCP

Los endpoints y tools genéricos de artefacto (leer, validar en seco, aplicar; ADR 0019) alcanzan; la respuesta de leer y validar suma los derivados de la etapa. Las tools documentan que el agente puede proponer ids.

## Importar planilla *(pendiente, prioridad baja)*

Queda para después. Hay que rediseñarla con el modelo de dos niveles (modos por equipo y configuración por modo operativo); la propuesta anterior (una columna por modo operativo con la disipación) ya no corresponde. Se mantiene: la API recibe el archivo y devuelve un **borrador** con sus problemas sin cambiar el proyecto (también como tool MCP), con procedencia `imported`, unidades normalizadas con pint y errores por fila y columna sin importar nada parcial.

## Abierto

- Diseño de la importación con el modelo de dos niveles; mapeo de columnas configurable.
- Límite máximo de encendido.
- Validaciones cruzadas con Misión (Σ `mass` × `quantity` ≤ masa del satélite): van en `global_balance`, donde se unen las dos raíces.
