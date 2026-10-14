# Etapa Balance global (`global_balance`): parámetros y resultado

> **Propuesta (2026-10-14), en revisión.** Versión acotada a la fase 0 de lo investigado en [balance-global.md](../investigacion/balance-global.md); lo que se dejó afuera está en [Fuera de esta versión](#fuera-de-esta-versión), con la etapa a la que va. Nada está implementado. Convenciones y tipos: los de [mission.md](mission.md#convenciones).

Etapa de cálculo ([ADR 0021](../adr/0021-etapas-de-calculo.md), contrato del [ADR 0022](../adr/0022-contrato-de-etapas-de-calculo.md)). Une las dos raíces del esquemático: la envolvente y los criterios de Misión, los flujos incidentes de Entorno y los equipos y modos operativos de Equipos. Con un **nodo único isotermo** en estacionario, con flujos promediados en la órbita, responde:

1. qué rango de temperatura tiene que respetar cada modo operativo, y qué equipos lo limitan;
2. cuánta área de radiador hace falta y en qué cara;
3. cuántos heaters hacen falta con esa área, por modo operativo;
4. qué no cierra (avisos).

No elige la arquitectura del TCS: eso es `tcs_concept`, que reevalúa alternativas con la misma función de `hestia_core`.

## Contexto que usa

Nada de esto se repite como parámetro.

| Etapa | Qué usa |
|---|---|
| Misión | Dimensiones de la envolvente (áreas de las caras), `mass` (aviso de masa), `uncertainty_margin`, `heater_power_budget`, `radiator_faces` |
| Entorno | Condiciones, modos de actitud y flujos promedio por condición × actitud × cara (solar, albedo e IR, en su mínimo y su máximo) |
| Equipos | Equipos (cantidad, masa, límites) y modos operativos con su disipación (la función del derivado de Equipos, [ADR 0026](../adr/0026-derivados-y-editores-propios-de-formularios.md)) |

## Modelo

Notación: caras `f` con área `A_f`; flujos incidentes medios del caso en cada cara: `S_f` (solar), `B_f` (albedo), `E_f` (IR); `Q` disipación del modo; `P` heaters; `r` la cara del radiador, de área `A`.

```
Rechazo neto del radiador por m²:  q_r(T) = ε_r σT⁴ − α_r (S_r + B_r) − ε_r E_r
Fuga del MLI por m²:               m_f(T) = κ [ε_o σT⁴ − α_o (S_f + B_f) − ε_o E_f],   κ = ε* / (ε_o + ε*)
Balance:                           Q + P = A q_r(T) + Σ_f (A_f − A·[f = r]) m_f(T)
```

### Rango de cada modo operativo

```
Equipo encendido en el modo:  [operating_min, operating_max]
Equipo apagado:               [switch_on_min, o non_operating_min, o operating_min;  non_operating_max, o operating_max]
Rango de diseño del modo:     [el mayor de los mínimos, el menor de los máximos]
Rango admisible:              [T_mín,d + u, T_máx,d − u]      (u = uncertainty_margin de Misión)
```

Los límites de Equipos son **límites de diseño** ECSS. Un modo con rango admisible vacío no dimensiona: se informa con los equipos en conflicto y un aviso.

### Casos

Un caso por cada combinación de condición de Entorno × modo de actitud compatible × modo operativo × lado:

- **Caliente:** flujos en su máximo, α EOL, `P = 0`, a `T_máx,adm` del modo.
- **Frío:** flujos en su mínimo, α BOL, a `T_mín,adm` del modo.

### Dimensionamiento

```
Área requerida (caso caliente):     A_req = [Q − Σ_f A_f m_f(T_c)] / [q_r(T_c) − m_r(T_c)]
Heaters con el área A (caso frío):  P = máx(0, A [q_r(T_f) − m_r(T_f)] + Σ_f A_f m_f(T_f) − Q)
Temperatura libre (P dado):         σT⁴ = [Q + P + A(α_r (S_r+B_r) + ε_r E_r) + κ Σ_f (A_f − A·[f=r]) (α_o (S_f+B_f) + ε_o E_f)]
                                          / [ε_r A + κ ε_o (A_tot − A)]
```

1. **Por cara candidata:** el área es el máximo de `A_req` sobre los casos calientes. Si el numerador es ≤ 0, no hace falta radiador (0); si el denominador es ≤ 0, la cara no rechaza calor a esa temperatura (no factible).
2. **Cara elegida:** la factible de menor área que entra en la cara. Si ninguna entra, la de menor área, con aviso. Para fijar una cara, se deja solo esa como candidata.
3. **Heaters por modo:** con el área elegida, el máximo de `P` sobre los casos fríos del modo; con margen, `P × (1 + power_margin)`. El total del punto de diseño es el del modo que más pide, frente a `heater_power_budget`.
4. **Temperaturas libres** de los casos que mandan, con el área elegida (fríos sin heaters), y su margen hasta el rango de diseño.

La evaluación de un caso (geometría, flujos, superficies, `Q`, cara y área → área, heaters y temperatura) es una función pública de `hestia_core`: la reusa `tcs_concept`.

## Parámetros

Formulario como Entorno: borrador, validación en seco, Aplicar, defaults de biblioteca con procedencia. Un valor vacío con preset significa «el del preset»: se resuelve al actualizar, y el resultado informa el valor y su fuente.

### 1. Radiador (`radiator`)

| Campo | Tipo | Unidad | Oblig. | Default |
|---|---|---|---|---|
| `candidate_faces` | `list[enum Face]` | — | no | Vacío: las `radiator_faces` de Misión (vacías: todas) |
| `coating` | `enum RadiatorCoating` | — | sí | `silvered_teflon` |
| `absorptance_bol` | `float` | — | no | Vacío: la del preset |
| `absorptance_eol` | `float` | — | no | Vacío: la del preset (si el preset no tiene, obligatorio) |
| `emittance` | `float` | — | no | Vacío: la del preset |

| `RadiatorCoating` | α BOL | α EOL | ε | Fuente |
|---|---|---|---|---|
| `silvered_teflon` (Teflon plateado, 5 mil) | 0,05 | 0,14 | 0,78 | Gilmore Tabla 4.1 (BOL, ε); THERME, LEO SSO a 4,5 años (EOL) |
| `osr` (espejo de cuarzo, 8 mil) | 0,05 | — | 0,80 | Gilmore Tabla 4.1 |
| `white_paint` (S13G-LO) | 0,20 | — | 0,85 | Gilmore Tabla 4.1 |
| `custom` | — | — | — | Todo obligatorio |

### 2. Aislación multicapa (`insulation`)

| Campo | Tipo | Unidad | Oblig. | Default |
|---|---|---|---|---|
| `effective_emittance` | `float` | — | sí | 0,03, el extremo alto de Gilmore cap. 5, p. 165 (0,015–0,030) |
| `outer_layer` | `enum OuterLayer` | — | sí | `aluminized_kapton` |
| `outer_absorptance_bol` | `float` | — | no | Vacío: la del preset |
| `outer_absorptance_eol` | `float` | — | no | Vacío: la del preset (si el preset no tiene, obligatorio) |
| `outer_emittance` | `float` | — | no | Vacío: la del preset |

| `OuterLayer` | α BOL | α EOL | ε | Fuente |
|---|---|---|---|---|
| `aluminized_kapton` (1 mil) | 0,38 | 0,48 | 0,67 | Gilmore Tabla 4.1; THERME (+0,10 en LEO SSO) |
| `beta_cloth` | 0,32 | — | 0,86 | Gilmore Tabla 4.1 |
| `custom` | — | — | — | Todo obligatorio |

### 3. Casos (`cases`)

| Campo | Tipo | Unidad | Oblig. | Default |
|---|---|---|---|---|
| `all_combinations` | `bool` | — | sí | Sí |
| `attitude_compatibility` | `map[ref(operating_modes), list[ref(attitude_modes)]]` | — | si `all_combinations` es no | — |

Qué modos de actitud puede tener cada modo operativo. Va acá porque el balance es la primera etapa que tiene en su contexto los modos operativos (Equipos) y los modos de actitud (Entorno). `tcs_concept` y `load_cases` la leen del contexto, no la redefinen.

- **`all_combinations`** («Evaluar todas las combinaciones de actitud y modo operativo»): cada modo operativo se evalúa en todos los modos de actitud de Entorno. Es el default porque no esconde casos; el resultado muestra qué combinación manda, así se puede restringir si no es realista.
- **Sin `all_combinations`**, la compatibilidad es explícita: cada modo operativo del contexto tiene su entrada con al menos una actitud. Como los campos de cada tipo de órbita en Entorno, `attitude_compatibility` solo se carga cuando corresponde (`not_allowed` si no).
- **Un modo operativo nuevo en Equipos** con la compatibilidad explícita queda sin actitudes: la validación lo pide (`required`) en lugar de suponer «todas».

### 4. Heaters (`heaters`)

| Campo | Tipo | Unidad | Oblig. | Default |
|---|---|---|---|---|
| `power_margin` | `float` (fracción) | — | sí | 0,25 (Gilmore cap. 15, Tabla 15.2 y p. 555) |

### Validaciones

- **Parámetros:** α y ε en (0, 1]; `effective_emittance` en (0, 1]; `power_margin` ≥ 0; caras candidatas sin repetir (`duplicate`) y dentro de las `radiator_faces` de Misión (`not_allowed`); los valores sin preset, obligatorios (`required`).
- **Compatibilidad:** `attitude_compatibility` solo sin `all_combinations` (`not_allowed`); en ese caso, cada modo operativo del contexto con al menos una actitud (`required`).
- **Referencias** (`invalid_reference`): modos operativos y modos de actitud del contexto.
- **Al actualizar:** `missing` y `context_invalid`, como en Entorno (Entorno sin resultado actual, o un formulario del contexto con problemas). Un modo sin rango o una cara no factible **no** hacen fallar la celda: son avisos del resultado.

## Resultado

| Parte | Contenido |
|---|---|
| `inputs_used` | Áreas de las caras, `u`, propiedades ópticas usadas con su fuente, disipación de cada modo |
| `ranges` | Por modo: rango de diseño y admisible, equipo que fija cada extremo, factible, equipos en conflicto |
| `faces` | Por cara candidata: factible, área requerida y caso que manda, fracción de la cara, entra o no |
| `design_point` | Cara, área, heaters (el modo que más pide) con margen, frente al presupuesto |
| `modes` | Por modo: caso caliente que manda (condición, actitud) y su temperatura libre; caso frío que manda, su temperatura libre sin heaters y los heaters con margen; margen hasta el rango de diseño en cada extremo |
| `warnings` | Código, mensaje y referencia. No hacen fallar la celda |
| `provenance` | Celdas y cambios del contexto, parámetros usados, proveedor y versión |

**Avisos:** `radiator_exceeds_face`, `no_feasible_face`, `empty_range` (por modo), `heater_budget_exceeded`, `equipment_mass_exceeds_mission` (Σ `quantity` × `mass` > `mass` de Misión), `duration_limited_mode` (un modo con `max_duration` se trata como estacionario, del lado conservador), `eol_default_out_of_scope` (el α EOL del preset es de LEO SSO hasta 4,5 años y la misión está fuera de eso).

## Vista de la celda *(diseño primero en `workspace.pen`)*

Dos pestañas, como Entorno.

**Parámetros:** las secciones del formulario en orden. Radiador, Aislación y Heaters salen del formulario generado; los campos vacíos muestran el valor del preset y su fuente. **Casos** es un editor propio, porque las opciones vienen del contexto y el formulario generado no puede armarlas:
- un interruptor «Evaluar todas las combinaciones de actitud y modo operativo», encendido por defecto, con una línea de ayuda;
- apagado, aparece la matriz de modos operativos (filas) × modos de actitud (columnas) con casillas, que arranca toda marcada; encenderlo de nuevo quita la matriz del borrador (se recupera con Descartar).

**Resultados:**
1. **Punto de diseño:** fila de indicadores con la cara y el área (m² y % de la cara), los heaters con margen frente al presupuesto y las temperaturas caliente y fría (°C).
2. **Avisos.**
3. **Rangos por modo:** una barra horizontal por modo, en °C, con el rango de diseño, el admisible y las temperaturas libres caliente y fría; los equipos que limitan cada extremo al costado; los modos sin rango, marcados.
4. **Caras candidatas:** área, fracción, si entra y caso que manda; la elegida resaltada.
5. **Modos:** casos que mandan, temperaturas y heaters.

## API y MCP

- Parámetros: endpoints y tools genéricos del artefacto (ADR 0019); el cuerpo suma `GlobalBalanceParameters` a la unión.
- Actualizar y leer: `update_cell` y `get_cell_result` genéricos. El resultado es chico: no hace falta leerlo por partes.

## Tests

- **Referencia de libro:** ejemplo POAM de Gilmore, cap. 15, pp. 555–560 (área de radiador y temperatura fría), con tolerancia y cita.
- **A mano:** radiador sin ambiente (solo emisión), MLI ideal (ε* → 0), sol sobre el radiador.
- **Energía:** el residuo del balance es nulo en cada solución.
- **Casos borde:** sin radiador necesario, cara que no rechaza, `Q = 0`, rango vacío, una sola cara, órbita sin eclipse.
- **Rangos:** límites faltantes, equipos apagados, intersección vacía.
- Revisión de `physics-reviewer`.

## Cambios en otras etapas

- **Equipos:** solo documentación. [equipment.md](equipment.md) dice que los límites son límites de diseño ECSS.
- **Editor propio para parámetros de una etapa de cálculo:** el ADR 0026 lo admite para etapas formulario; se amplía para los parámetros del balance.
- Misión y Entorno no cambian.

## Fuera de esta versión

| Tema | Va a |
|---|---|
| Transitorio de un nodo, constante de tiempo, LEOP, modos con duración máxima | `load_cases` |
| Temperaturas de sumidero por cara, elección de recubrimientos por cara, radiador repartido en varias caras | `tcs_concept` |
| Equipos con control propio | `tcs_concept` (el balance lista los equipos en conflicto) |
| Gradiente entre equipos y radiador | `discretization` y `couplings` |
| α EOL según órbita y vida (curvas de degradación) | Más adelante; hoy se carga a mano fuera de LEO |
| ε* del MLI como rango | Más adelante, si hace falta |
| Margen de madurez de la disipación | Más adelante: un campo global en el balance o la madurez por equipo en Equipos |
| Pares albedo ⇔ OLR, tiempo de promediado y corrección SZA | Cambio aparte de Entorno ([datos-entorno-y-balance.md](../investigacion/datos-entorno-y-balance.md)) |
| Incertidumbre de 15 K para la fase 0 | Default de Misión, si se decide |
| Presupuesto de heaters de supervivencia | Misión, si se decide |
