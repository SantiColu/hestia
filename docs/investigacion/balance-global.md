# Balance global (`global_balance`): concepto para la fase 0

**Fecha:** 2026-10-05
**Estado:** investigación para revisar antes de especificar la etapa. No es especificación ni ADR; nada de esto está implementado.

## Alcance y cómo leer

- Una sección por pregunta: primero la recomendación, después la práctica, las alternativas y las fuentes. Al final, la propuesta de parámetros y de resultado (coherente con el [ADR 0021](../adr/0021-etapas-de-calculo.md)), lo que queda abierto y los supuestos para `physics-reviewer`.
- **Respaldo y opinión:** lo respaldado lleva su referencia entre corchetes, `[n, lugar]`, numerada como en [Fuentes](#fuentes). El criterio propio va marcado *(opinión)*. Los números de los ejemplos son cálculos propios y lo dicen.
- **Qué se leyó:** ECSS-E-ST-31C [1], el curso oficial de ESA sobre esa norma [2], Gilmore 2.ª ed., caps. 2, 4, 5, 6, 7 y 15 [3], NASA/TM-2001-211221 [4], ECSS-E-HB-31-01 partes 7 y 5 [5, 6], NASA RP-1121 [7], el experimento en vuelo THERME de CNES [8] y el resumen de las reglas GOLD de GSFC [9]. **Karam no se pudo consultar** en esta sesión: figura en Fuentes como lectura pendiente y no respalda ningún valor.
- «Práctica de la industria» es la documentada en normas, manuales y ejemplos publicados. Los procedimientos internos de cada empresa varían y no están al alcance.

## Resumen

1. **Modelo:** nodo único isotermo, estacionario con flujos promediados en la órbita (inercia infinita) para dimensionar. Es lo que hacen los ejemplos publicados y lo que indica ESA para los casos extremos de la órbita operativa. El transitorio de un nodo (capacidad = masa × cp efectivo) sirve para verificar que el promedio vale (constante de tiempo frente al período) y para los eventos de duración acotada. La inercia nula no es una cota creíble para el cuerpo de un satélite mediano: no es caso de diseño.
2. **Casos:** el peor caso depende de las propiedades ópticas, de la cara del radiador, de la disipación y del rango admisible de cada modo, así que no se puede elegir antes. Se **evalúan todas las combinaciones** compatibles (condición × actitud × modo operativo), que en un nodo cuestan milisegundos. El caso caliente es el que exige más área de radiador; el frío, el que exige más potencia de heaters con esa área. Se suman los casos propios del usuario (modo seguro, LEOP).
3. **Ópticas:** radiador con α BOL/EOL y ε en una cara; MLI (ε* y capa externa) en el resto; todo cara por cara con los flujos de Entorno. Caliente con EOL y ambiente máximo; frío con BOL y ambiente mínimo.
4. **Rango y márgenes:** el rango a respetar es **por modo operativo**: intersección de los límites de diseño de los equipos encendidos (operativos) y apagados (no operativos y de encendido). La incertidumbre achica ese rango hacia adentro; aceptación y calificación van hacia afuera y no dimensionan.
5. **Radiador y heaters:** el área sola no alcanza. Área por cara candidata (fórmula cerrada), potencia de heaters del caso frío con esa área, ventana de área pasiva (dice si hacen falta heaters o un radiador variable) y avisos de área y de presupuesto. La masa del TCS depende de la arquitectura: va en `tcs_concept`.
6. **Para `tcs_concept`:** casos evaluados y dimensionantes, tabla por cara (área, rechazo neto, heaters), ventana pasiva, rangos por modo con equipos limitantes e incompatibles, constante de tiempo, temperaturas de sumidero, avisos y procedencia.

## 1. Modelo térmico sin inercia conocida

### Recomendación

- **Dimensionar con el estacionario de flujos promediados en la órbita** (inercia infinita). Cada caso es un balance algebraico: disipación media del modo + flujos absorbidos medios = emisión del radiador + fuga por el MLI (fórmulas en la [sección 3](#modelo-de-un-nodo)).
- **Informar siempre la constante de tiempo** `τ = C / G` del nodo, con `C = mass` (Misión) × `cp_eff` y `G` la conductancia radiativa linealizada al espacio, y compararla con el período orbital. Si τ no es mucho mayor que el período, el resultado avisa que el promedio deja de representar al nodo *(opinión: umbral a fijar, p. ej. τ ≥ 5 períodos)*.
- **Transitorio de un nodo** solo para lo que el promedio no responde:
  - la oscilación orbital del nodo en los casos dimensionantes (informativa), con los `orbit_profiles` de Entorno;
  - eventos de duración acotada: LEOP sin potencia, transiciones sin heaters, modos con `max_duration`. Ahí la capacidad manda.
- **Inercia nula:** no como caso de diseño del nodo. Lo que tiene de útil (cuán caliente o fría queda una superficie sin masa en cada cara) se entrega como **temperatura de sumidero** por cara, promedio y pico, el concepto de ECSS [1, §3.2.1.22]. Sirve para elegir caras y recubrimientos y, en la fase 1, para piezas externas livianas.
- **cp efectivo:** parámetro con default 900 J/(kg·K) y una banda de ±30 % *(opinión; no hay fuente de un cp «del satélite», ver abajo)*. El dimensionamiento no depende de C; la banda solo afecta τ y los transitorios, que se informan en sus dos extremos.

### Alternativas

| Alternativa | A favor | En contra |
|---|---|---|
| Estacionario promediado (inercia ∞) | Estándar en diseño conceptual; algebraico y cerrado; usa directamente los promedios por cara de Entorno; no depende de cp | No ve la oscilación en la órbita ni eventos cortos; pierde validez si τ se acerca al período (GEO, satélites chicos) |
| Estacionario instantáneo (inercia 0) | Cota simple con los picos de Entorno | Para el cuerpo de un satélite mediano es irreal: sobreestima la oscilación en órdenes de magnitud y sobredimensiona radiador y heaters |
| Transitorio de un nodo, C = m·cp | Da oscilación, τ y eventos de duración | Depende de cp (incierto) y supone toda la masa acoplada al radiador, así que subestima la oscilación del panel real |
| Las dos cotas (0 e ∞) como resultado | Fácil de explicar | La cota 0 no es creíble para el cuerpo y confunde; su información útil está mejor como temperatura de sumidero |

### Justificación y fuentes

- **ESA:** los casos extremos de la órbita operativa se calculan en estacionario; el transitorio es para lanzamiento, órbita de transferencia, evolución cíclica en la órbita y casos de falla [2, diap. 115].
- **Ejemplo publicado de diseño conceptual:** Gilmore dimensiona el radiador de un instrumento con la disipación media orbital máxima y los flujos medios orbitales máximos, y justifica el promedio por la capacidad térmica frente a los pulsos de disipación [3, cap. 15, p. 557, ec. 15.16]. El caso frío se resuelve con la misma área y los valores mínimos [3, cap. 15, p. 560, ec. 15.19–15.21].
- **Inercia:** las oscilaciones cortas del ambiente no afectan a componentes masivos y bien aislados, sí a los livianos expuestos como paneles solares y radiadores desplegables [3, cap. 2, p. 22]. El hardware tiene constantes de tiempo de minutos a pocos días [3, cap. 2, p. 25]. La guía de NASA resuelve el problema modelando solo el ciclo luz–sombra con albedo e IR acordes a la constante de tiempo del sistema [4, §4.2.2].
- **Orden de magnitud** (cálculo propio, ilustrativo): satélite de 500 kg con cp 900 J/(kg·K) (C = 450 kJ/K), envolvente de 1,2 × 1,2 × 1,5 m, radiador de 1,5 m² con ε = 0,8 y MLI con ε* = 0,02 en el resto, a 20 °C. Da G ≈ 7,8 W/K y τ ≈ 16 h (11 a 21 h con cp entre 600 y 1200), contra un período de ~1,6 h. Perder 100 W durante 35 min de eclipse baja el nodo ~0,5 K. En LEO el promedio describe bien al nodo; en GEO (período de 24 h) τ es comparable al período y el transitorio pasa a importar.
- **Por qué C sí importa en los eventos de duración:** el ejemplo de Gilmore exige sobrevivir 3,5 h sin potencia después del lanzamiento y dos órbitas sin potencia al salir del modo seguro [3, cap. 15, Tabla 15.5]. Eso es un transitorio puro y su resultado escala con C.
- **cp efectivo:** no se encontró una fuente con el cp efectivo de un satélite completo *(dato faltante)*. Referencias de materiales: aluminio ≈ 900 J/(kg·K) a temperatura ambiente [6, Fig. 4-1]; compuestos entre ~800 y ~1300 J/(kg·K) según fibra y matriz [6, Tabla 5-8]. El propelente líquido (p. ej. hidracina) tiene un cp varias veces mayor que el aluminio *(no verificado en esta investigación)*: un satélite con mucho propelente tiene más C. El default de 900 y la banda de ±30 % son *(opinión)*.

## 2. Armado de casos caliente y frío

### Recomendación

- **Enumerar, no elegir a priori.** Hestia arma un candidato por cada combinación compatible de:
  - condición de Entorno (extremas y propias);
  - modo de actitud compatible con el modo operativo (tabla de compatibilidad, parámetro; default: todas con todos *(opinión: no esconde casos)*);
  - modo operativo de Equipos.
- **Lado de cada candidato:** caliente = flujos máximos + α EOL; frío = flujos mínimos + α BOL. Con ε* se evalúan los dos extremos y se queda el peor. No hace falta cruzar BOL/EOL con mínimo/máximo: lo absorbido crece con los flujos y con α, así que el resultado es monótono *(opinión; a confirmar por `physics-reviewer`)*.
- **Cada candidato usa el rango admisible de su modo operativo** ([sección 4](#4-rango-común-de-temperatura-y-márgenes)). Por eso el modo de máxima disipación no es necesariamente el caliente: puede dimensionar otro con un límite superior más bajo.
- **Qué caso «es» el caliente o el frío:** el que dimensiona, por cara candidata del radiador:
  - caliente: el que exige **más área** de radiador;
  - frío: con esa área, el que exige **más potencia de heaters** (o, si ninguno la necesita, el de menor margen al límite inferior).
- **Casos propios:** el usuario agrega combinaciones explícitas (condición, actitud, modo operativo, ambiente mínimo o máximo, BOL o EOL) que se evalúan con el área dimensionada y, por defecto, también dimensionan.
- **Costo:** p. ej. 6 condiciones × 3 actitudes × 6 modos × 2 lados × 2 valores de ε* × 6 caras son ~2600 evaluaciones de fórmulas cerradas: milisegundos *(estimación propia)*.

### Casos estándar de la fase 0

| Caso | Qué combina | Rango que se verifica | Fuente | Cómo entra en Hestia *(opinión)* |
|---|---|---|---|---|
| Caliente operativo | Ambiente máximo, EOL, modo operativo y actitud que lo exigen | Operativos de los encendidos, no operativos de los apagados | [1, §4.2.1 d], [2, diap. 114] | Automático |
| Frío operativo | Ambiente mínimo, BOL, menor disipación | Ídem | [1, §4.2.1 d], [2, diap. 114] | Automático |
| Eclipse más largo | Condición de máximo eclipse | Ídem | [2, diap. 114] («during a long eclipse»), [1, §4.1.4 a.4] | Automático: ya es una condición extrema de Entorno |
| Supervivencia / modo seguro | Modo operativo «seguro» (pocos equipos encendidos), su actitud, solo heaters de supervivencia | No operativos y de encendido | [3, cap. 7, p. 230] (heaters de supervivencia con punto de ajuste más bajo), [3, cap. 15, Tabla 15.5] | Automático: es un modo operativo más de Equipos; su presupuesto de heaters es un tema abierto |
| LEOP | Separación hasta adquirir actitud y potencia, con poca o ninguna potencia, duración acotada | No operativos y de encendido | [1, §4.1.3], [2, diap. 115], [3, cap. 15, Tabla 15.5] | Caso propio transitorio (temperatura inicial y duración); versión posterior |
| Fallas (pérdida de actitud, de un heat pipe) | — | — | [2, diap. 115]; el rango calculado de ECSS las excluye [1, §3.2.1.3] | Fuera de la fase 0 |
| Tierra y prelanzamiento | Integración, transporte, plataforma | — | [1, §4.1.2] | Fuera de alcance (es diseño de GSE) |

### Justificación y fuentes

- **ECSS:** las fases de la misión se representan con un conjunto coherente de casos de diseño que cubre el rango extremo de condiciones; para los casos de dimensionamiento se usan los peores casos caliente y frío [1, §4.2.1 b–d]. El rango calculado sale de «una combinación apropiada de flujos externos, propiedades de materiales y perfiles de disipación», sin casos de falla [1, §3.2.1.3]. Un caso de diseño es justamente ese conjunto de parámetros [1, §3.2.1.37].
- **ESA:** caliente = EOL, irradiancia solar máxima, disipación máxima; frío = BOL, irradiancia mínima, disipación mínima; y advierte que el peor caso puede darse en otro momento, o en un eclipse largo [2, diap. 114].
- **Hay que correr combinaciones:** «puede hacer falta una cantidad de corridas para determinar exactamente cuál es la peor combinación de factores, como ángulo β, modo operativo, actitud y propiedades de superficie» [3, cap. 15, p. 537].
- **El peor caso depende de las ópticas:** NASA: «cuál resulta el caso extremo caliente o frío de un sistema depende de la emitancia de sus superficies y de su absortancia solar»; según esa relación, el extremo puede venir del albedo, de la IR o de un caso combinado [4, §4.2.3]. Gilmore: los acabados de radiador (α ~0,2, ε ~0,8) son mucho más sensibles a la IR terrestre que al albedo [3, cap. 2, p. 31]. Entorno ya lo asume: entrega condiciones, no casos ([environment.md](../etapas/environment.md)).
- **Advertencia sobre el ambiente:** Entorno combina albedo máximo con IR máxima (y mínimos con mínimos). Los datos de NASA muestran que albedo e IR están parcialmente correlacionados (albedo alto con IR baja) y dan pares por tiempo de promediado [4, §4.2.3, Tablas 4.2.3-1 a -3]; Gilmore discute el mismo punto [3, cap. 2, pp. 30–31]. Sumar los dos máximos es conservador. Corregirlo es tarea de Entorno (ver [Abierto](#lo-que-queda-abierto)).

## 3. Propiedades ópticas

### Recomendación

- **Radiador + MLI, cara por cara.** Un radiador de área A en una cara candidata, con α BOL y EOL y una ε; el resto de la envolvente (incluido lo que queda libre de esa cara) cubierto de MLI con ε* y una capa externa con α y ε propias. Cada cara usa sus flujos medios de Entorno (solar, albedo e IR por separado). Elegir recubrimientos cara por cara es arquitectura: es de `tcs_concept` y `discretization`.
- **BOL para el frío, EOL para el caliente** [2, diap. 59 y 114], con ε constante: la degradación sube α con poco o ningún efecto sobre ε [3, cap. 4, p. 143] (salvo erosión por oxígeno atómico del Teflon en LEO bajo [3, cap. 4, p. 154]).
- **ε* del MLI como rango** (mínimo y máximo); cada candidato se evalúa en los dos extremos y se queda el peor, porque el signo de su efecto depende de cada cara (una cara al Sol con la capa externa más caliente que el nodo calienta; una fría enfría).
- **Presets con fuente** que rellenan valores vacíos, como la tabla de albedo e IR de Entorno: el resultado informa el valor usado y su fuente.

### Modelo de un nodo

Notación: caras `f` (+X…−Z) con área `A_f` de la envolvente de Misión y `A_tot = Σ A_f`; flujos incidentes medios de la cara en el caso, de Entorno: `S_f` (solar), `B_f` (albedo), `E_f` (IR); `Q` disipación del modo operativo (la función de Equipos, [ADR 0026](../adr/0026-derivados-y-editores-propios-de-formularios.md)); `P` potencia de heaters; `r` la cara del radiador.

```
Rechazo neto del radiador por m²:   q_r(T) = ε_r σT⁴ − α_r (S_r + B_r) − ε_r E_r
Fuga del MLI por m²:                m_f(T) = κ [ε_o σT⁴ − α_o (S_f + B_f) − ε_o E_f],   κ = ε* / (ε_o + ε*)
Balance del nodo (T uniforme):      Q + P = A q_r(T) + Σ_f (A_f − A·[f = r]) m_f(T)
```

`m_f` sale de la definición de ε* entre el nodo y la capa externa [5, ec. 6-2] y de suponer la capa externa sin masa y en equilibrio radiativo *(derivación propia, a revisar)*. Como todo es lineal en los flujos y en `σT⁴`, el promedio orbital es exacto para un nodo de inercia infinita, y todo se resuelve en forma cerrada (ver [sección 5](#5-radiador-y-heaters)).

### Valores típicos

| Recubrimiento | α BOL | ε | α EOL (medido o recomendado) | Fuente |
|---|---|---|---|---|
| OSR, espejo de cuarzo 8 mil | 0,05–0,08 | 0,80 | Sube por contaminación; curva de diseño solo para GEO [3, Fig. 4.7]. Sin dato LEO en estas fuentes | [3, Tabla 4.1] |
| Teflon plateado 5 mil | 0,05–0,09 | 0,78 | LEO SSO: hasta 0,14 a los 4,5 años (Δα +0,02 a +0,04, HELIOS 2A) [8]. GEO: curva de diseño [3, Fig. 4.9] | [3, Tabla 4.1]; 0,08 / 0,81 [7] |
| Teflon aluminizado (SSM de aluminio) | 0,10–0,16 | 0,78 | LEO SSO: Δα hasta +0,12 a los 7 años, α hasta 0,28 (SPOT 5) [8] | [3, Tabla 4.1] |
| Pintura blanca S13G-LO | 0,20–0,25 | 0,85 | Puede pasar de ~0,20 a 0,70 en pocos años [3, cap. 4, p. 154] | [3, Tabla 4.1] |
| Pintura blanca Z93 | 0,17–0,20 | 0,92 | Curva [3, Fig. 4.10] | [3, Tabla 4.1]; 0,17 / 0,92 [7] |
| Pinturas blancas SG121FD y PCBE | 0,19–0,27 (en tierra) | — | LEO SSO: suben fuerte los 2 primeros años y se estabilizan en 0,43–0,52 [8] | [8] |
| Kapton aluminizado 1 mil (capa externa de MLI) | 0,38 | 0,67 | LEO SSO: Δα +0,09 a +0,10 en 4,5–7 años [8]. GEO: casi negro tras varios años [3, Fig. 4.11] | [3, Tabla 4.1] |
| Beta cloth (capa externa de MLI) | 0,32 | 0,86 | GEO: degrada mucho [3, cap. 4, p. 154] | [3, Tabla 4.1] |
| MLI, ε* efectiva | — | 0,015–0,030 en aplicaciones de área media; 0,005 en laboratorio; 0,05–0,30 en mantas muy chicas | — | [3, cap. 5, p. 165] |

- Los valores de tabla dependen del sustrato, el proceso y el espesor: ante la duda, medir [2, diap. 119]; ECSS exige usar propiedades confiables y sus valores degradados [1, §4.4.1 d].
- La degradación de la capa externa del MLI pesa poco en el balance, porque por la manta pasa poco calor [3, cap. 4, p. 154].
- El experimento THERME midió en vuelo tres satélites en SSO (SPOT 5, HELIOS 2A, DEMETER) [8]: es la mejor referencia encontrada para LEO.

### Defaults propuestos *(opinión sobre la elección; valores con su fuente)*

- **Radiador:** Teflon plateado 5 mil, el único recubrimiento con BOL y EOL LEO respaldados acá. α BOL 0,05 (extremo bajo de [3], conservador para el frío), α EOL 0,14 [8], ε 0,78 [3]. El α EOL tiene respaldo en LEO SSO hasta ~4,5 años: fuera de eso el resultado avisa. OSR y pinturas blancas, sin α EOL por defecto (obligatorio).
- **MLI:** ε* entre 0,015 y 0,030 [3]; capa externa de Kapton aluminizado 1 mil: α BOL 0,38 y ε 0,67 [3], α EOL = BOL + 0,10 [8], con el mismo aviso de alcance.

## 4. Rango común de temperatura y márgenes

### Recomendación

- **Rango por caso, según el modo operativo** (no la intersección global de todos los equipos):

  ```
  Equipo encendido en el modo:  [operating_min, operating_max]
  Equipo apagado:               [switch_on_min, o non_operating_min, o operating_min;  non_operating_max, o operating_max]
  Rango de diseño del caso:     [T_mín,d, T_máx,d] = [el mayor de los mínimos, el menor de los máximos]
  Rango admisible del cálculo:  [T_mín,d + u, T_máx,d − u]      (u = uncertainty_margin de Misión)
  ```

  Para los apagados se toma el mínimo de encendido si existe: cualquier equipo apagado puede tener que encenderse (p. ej. al salir del modo seguro) *(opinión, conservadora)*. Sin límites no operativos se usan los operativos, que según Equipos están contenidos en ellos *(opinión, conservadora)*.
- **Semántica de los límites de Equipos:** son los **límites de diseño** de ECSS (el requisito para el TCS). Si un proveedor da límites de calificación, se les restan los márgenes de calificación y de aceptación antes de cargarlos. Conviene escribirlo en [equipment.md](../etapas/equipment.md).
- **De qué lado va cada margen:**
  - incertidumbre `u`: hacia adentro del rango de diseño; la temperatura calculada ± u (la predicha) tiene que quedar dentro;
  - aceptación y calificación: hacia afuera del rango de diseño; fijan niveles de ensayo y no dimensionan nada en la fase 0. Si se quiere, se informan como rangos implicados por equipo, pero eso es más de `margins`.
- **Margen de diseño:** el resultado informa lo que sobra entre la predicción y el límite de diseño, en cada caso.
- **Equipos limitantes e incompatibles:** el resultado dice qué equipo fija el mínimo y el máximo de cada modo, y qué equipos dejan el rango vacío o son incompatibles con la temperatura del nodo. Son los candidatos a control propio (heater, radiador o aislación dedicados) y es la entrada más valiosa para `tcs_concept` *(opinión)*.
- **Equipos con control propio:** parámetro opcional para sacarlos de la intersección (siguen sumando su disipación) *(opinión)*.
- **Valor de u:** 15 K para la fase 0 *(recomendación con respaldo de [2], ver abajo)*; hoy Misión tiene 10 K por defecto.

### Justificación y fuentes

- **Definiciones** [1, §3.2.1.1–3.2.1.20, Fig. 3-1]:
  - **calculado:** el que da el análisis para el modo operativo, el no operativo y el encendido, en el peor caso;
  - **predicho:** el calculado ampliado por las incertidumbres;
  - **de diseño:** el requisito para el TCS; el calculado más las incertidumbres tiene que quedar dentro;
  - **de aceptación:** el de diseño más el margen de aceptación; es el extremo que el equipo puede alcanzar pero nunca superar;
  - **de calificación:** el de aceptación más el margen de calificación.
  - ECSS desaconseja llamar «rango operativo» al de diseño y acepta «límites operativos o no operativos» [1, §3.2.1.7, nota 2]: los nombres de Equipos ya coinciden.
- **Rangos por estado del equipo:** el rango de diseño se especifica para el modo operativo, el no operativo y la condición de encendido de cada equipo [1, §3.2.1.7]; la temperatura mínima de encendido está definida aparte [1, §3.2.1.16]. Eso respalda el rango por modo operativo y no la intersección global.
- **Valores de los márgenes:** ECSS no los fija: los define la autoridad de sistema [1, §4.2.1 e–f]. El curso de ESA da «usualmente 5 °C» para aceptación y para calificación [2, diap. 69, 121]: confirma los defaults de Misión, que hoy dicen «a verificar contra la norma».
- **Incertidumbre:**
  - ECSS: en general no se aplican incertidumbres menores que 10 K antes del ensayo de balance térmico [1, §4.5.2.1 c, nota]. Es un piso, no el valor de fase 0.
  - ESA: sin análisis de incertidumbre se recomienda 10 °C inicial [2, diap. 69]; valores típicos de ±15 K en fase 0/A y ±10 K en fase B/C [2, diap. 120].
  - Gilmore: el margen de incertidumbre usual de 10 °C equivale aproximadamente a una protección de 2σ contra exceder la temperatura predicha [3, cap. 2, pp. 29–30]. Sus criterios de evaluación del TCS piden 11 °C más allá de las predicciones de un modelo correlacionado con ensayos [3, cap. 15, Tabla 15.2]. GSFC pide 5 °C en las fases B/C [9].
  - Un nodo único es el modelo más grueso posible: 15 K de [2] es lo coherente *(opinión)*.
- **Margen de diseño:** «lo que queda entre el límite de diseño y la predicción; no está definido formalmente en ECSS y puede ser 0» [2, diap. 66].

## 5. Radiador y heaters

### Recomendación

Dimensionar solo el área y avisar si no entra **no alcanza**: falta la potencia de heaters, la elección de cara y saber si un radiador fijo puede con los dos extremos. Por cada cara candidata (las `radiator_faces` de Misión, o todas):

```
Área requerida (candidato caliente, P = 0, T_c = T_máx,d − u):
    A_req = [Q − Σ_f A_f m_f(T_c)] / [q_r(T_c) − m_r(T_c)]

Área pasiva máxima (candidato frío, P = 0, T_f = T_mín,d + u):
    A_pas = [Q − Σ_f A_f m_f(T_f)] / [q_r(T_f) − m_r(T_f)]

Heaters con el área fijada (candidato frío):
    P = máx(0,  A [q_r(T_f) − m_r(T_f)] + Σ_f A_f m_f(T_f) − Q)

Temperatura libre (cerrada):
    σT⁴ = [Q + P + A(α_r (S_r+B_r) + ε_r E_r) + κ Σ_f (A_f − A·[f=r]) (α_o (S_f+B_f) + ε_o E_f)]
          / [ε_r A + κ ε_o (A_tot − A)]

Constante de tiempo:
    τ = m · cp_eff / G,   G = 4σT³ [ε_r A + κ ε_o (A_tot − A)]
```

- **Área de la cara:** el máximo de `A_req` sobre los candidatos calientes. Si el denominador es ≤ 0, esa cara no puede rechazar calor a `T_c` (no factible); si el numerador es ≤ 0, no hace falta radiador (A = 0) *(casos borde, opinión)*.
- **Heaters:** con esa área, el máximo de `P` sobre los candidatos fríos, en W de promedio orbital (igual que `heater_power_budget` de Misión).
- **Ventana pasiva:** `A_pas` mínimo sobre los fríos. Si `A_req ≤ A_pas`, un radiador fijo sin heaters cumple ambos extremos; si no, la razón `A_pas / A_req` mide cuánto falta. Es el indicador de si hace falta control variable (louvers, VCHP) o heaters *(indicador propuesto, opinión; respaldo físico abajo)*.
- **Cara elegida:** la factible de menor área (desempate por menor potencia de heaters), o la que fije el usuario *(opinión)*. Una sola cara en la primera versión; repartir el radiador entre caras es de `tcs_concept`.
- **Avisos:** área mayor que la cara; ninguna cara permitida factible; potencia de heaters con margen mayor que el presupuesto; α EOL por defecto fuera de su respaldo (otra órbita o vida mayor).
- **Margen de heaters:** potencia instalada mínima = `P × (1 + m_h)`, con `m_h` = 25 % por defecto, comparada con el presupuesto. Ver el tema abierto sobre margen de temperatura o de potencia.
- **Masa del TCS:** no en el balance. Depende de la arquitectura: un radiador que es un panel estructural casi no suma masa al TCS y uno desplegable llega a ~12 kg/m² [3, cap. 6, p. 208]. El balance entrega las áreas de radiador y de MLI; `tcs_concept` estima la masa y la compara con `tcs_mass_budget`.
- **Masa de los equipos:** Σ `quantity` × `mass` ≤ `mass` de Misión, como aviso. Es la validación cruzada que el [ADR 0016](../adr/0016-contexto-de-celda-por-cadena.md) ubica donde se unen las raíces.

### Justificación y fuentes

- **Radiador por el caliente y heaters por el frío con la misma área:** ejemplo de Gilmore [3, cap. 15, p. 560]. Los radiadores sobredimensionados para las cargas de EOL hacen que el satélite corra más frío los primeros años y a veces necesite heaters [3, cap. 4, p. 143]: es el caso BOL frío.
- **Temperatura del radiador:** Gilmore lo dimensiona a 40 °C para dejar 10 °C de margen al límite de 50 °C [3, cap. 15, p. 560]. Es exactamente `T_c = T_máx,d − u`.
- **Sanidad:** la mayoría de los radiadores rechaza entre 100 y 350 W/m² [3, cap. 6, p. 208]. Sirve como chequeo de los tests, no como aviso *(opinión)*.
- **Control variable:** los heat pipes de conductancia variable se usan cuando las cargas varían mucho o para minimizar los heaters del caso frío [3, cap. 6, p. 209]. Eso respalda la ventana pasiva como entrada de `tcs_concept`.
- **Márgenes de heaters:**
  - Gilmore: los componentes con control activo necesitan al menos 25 % de autoridad de control, equivalente a los 11 °C de los pasivos [3, cap. 15, Tabla 15.2].
  - En el ejemplo POAM los heaters se dimensionan para 10 °C de margen al límite inferior **o** 25 % de exceso de capacidad [3, cap. 15, p. 555].
  - GSFC: 5 °C de margen, salvo los elementos controlados por heaters, con ciclo de trabajo máximo del 70 % [9]; eso equivale a ~43 % de exceso.
- **Presupuestos:** ECSS pide que la especificación del TCS asigne potencia eléctrica para calentar y masa al TCS [1, §4.2.1 g.7 y g.9].
- **Heaters de supervivencia:** tienen punto de ajuste más bajo que los operativos, para gastar menos [3, cap. 7, p. 230]. Por eso el modo seguro tiene su propio presupuesto en la práctica (tema abierto).

## 6. Qué entrega el balance a Concepto TCS

### Recomendación

| Salida | Para qué la usa `tcs_concept` |
|---|---|
| Casos evaluados, con los dimensionantes marcados (por qué y en qué cara) | Saber qué combinación manda; repetir el trade-off sobre los mismos casos sin recalcular Entorno |
| Tabla por cara: área requerida, fracción de la cara, rechazo neto en W/m², área pasiva máxima, potencia de heaters y casos que mandan en cada uno | Dónde van los radiadores, si alcanza una cara o hace falta repartir, desplegar o subir la temperatura |
| Punto de diseño: cara, área, heaters, heaters con margen frente al presupuesto | Línea base de la arquitectura |
| Ventana pasiva (`A_pas / A_req`) | Pasivo puro, heaters o radiador variable (louvers, VCHP) |
| Rangos por modo: de diseño y admisible, equipos limitantes, equipos incompatibles o con rango vacío | Qué equipos necesitan control propio |
| Temperaturas libres caliente y fría y margen de diseño por caso | Cuánto sobra o falta en cada extremo |
| Constante de tiempo, τ / período y oscilación orbital (en los extremos de C) | Si hace falta masa térmica, PCM o control activo; alerta en GEO |
| Temperaturas de sumidero por cara (promedio y pico), con el recubrimiento del radiador y la capa externa | Elegir recubrimientos por cara |
| Áreas de radiador y de MLI | Masa del TCS frente a `tcs_mass_budget` |
| Avisos | Lo que hay que resolver |
| Procedencia ([ADR 0021](../adr/0021-etapas-de-calculo.md)) | Trazabilidad |

**Diseño del cálculo** *(opinión)*: la evaluación de un caso (geometría, flujos, recubrimientos, Q, cara y área → temperaturas, área, potencia) tiene que ser una función de `hestia_core` reutilizable, porque `tcs_concept` va a evaluar alternativas (otro recubrimiento, louvers, otra cara) sobre los casos que el balance marcó como dimensionantes. Eso evita que los dos cálculos diverjan.

## Propuesta de parámetros

Formulario de parámetros como en Entorno ([ADR 0021](../adr/0021-etapas-de-calculo.md)): borrador, validación en seco, Aplicar, defaults de biblioteca con procedencia. Un valor vacío con preset significa «el del preset», que se resuelve al actualizar y el resultado informa con su fuente (mismo criterio que la tabla de albedo e IR de Entorno).

Lo que viene del contexto no se repite como parámetro:
- **Misión:** dimensiones y masa de la envolvente, márgenes, presupuestos, `radiator_faces` y `design_life`.
- **Entorno:** condiciones, modos de actitud, flujos, perfiles, tipo de órbita y período.
- **Equipos:** equipos, límites, modos operativos y la función de disipación.

### 1. Radiador (`radiator`)

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `candidate_faces` | `list[enum Face]` | — | Vacío: las `radiator_faces` de Misión (vacías: todas) | Misión |
| `selected_face` | `enum Face` | — | Vacío: automática (la factible de menor área) | *(opinión)* |
| `coating` | `enum RadiatorCoating` | — | `silvered_teflon` | *(opinión)* |
| `absorptance_bol` | `float` | — | Vacío: la del preset (Teflon plateado: 0,05) | [3, Tabla 4.1], extremo bajo |
| `absorptance_eol` | `float` | — | Vacío: la del preset (Teflon plateado: 0,14; OSR y pintura blanca: obligatorio) | [8] |
| `emittance` | `float` | — | Vacío: la del preset (Teflon plateado: 0,78) | [3, Tabla 4.1] |

`RadiatorCoating`: `silvered_teflon` (5 mil), `osr` (cuarzo 8 mil: α BOL 0,05, ε 0,80 [3]), `white_paint` (S13G-LO: α BOL 0,20, ε 0,85 [3]), `custom` (todo obligatorio).

### 2. Aislación multicapa (`insulation`)

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `effective_emittance_min` | `float` | — | 0,015 | [3, cap. 5, p. 165] |
| `effective_emittance_max` | `float` | — | 0,030 | [3, cap. 5, p. 165] |
| `outer_layer` | `enum OuterLayer` | — | `aluminized_kapton` (1 mil) | *(opinión)* |
| `outer_absorptance_bol` | `float` | — | Vacío: la del preset (0,38) | [3, Tabla 4.1] |
| `outer_absorptance_eol` | `float` | — | Vacío: la del preset (0,48 = BOL + 0,10) | [8] |
| `outer_emittance` | `float` | — | Vacío: la del preset (0,67) | [3, Tabla 4.1] |

`OuterLayer`: `aluminized_kapton`, `beta_cloth` (α BOL 0,32, ε 0,86 [3]; α EOL obligatorio), `custom`.

### 3. Casos (`cases`)

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `attitude_compatibility` | `map[ref(operating_modes), list[ref(attitude_modes)]]` | — | Vacío: todas las actitudes con todos los modos | *(opinión)* |
| `custom_cases` | `list[CustomCase]` | — | Vacía | — |

**`CustomCase`:** `id`, `name`, `condition_id` (condición de Entorno: extremas, con ids semánticos como `max_eclipse`, o propias), `attitude_mode_id`, `operating_mode_id`, `environment` (`min` \| `max`), `properties` (`bol` \| `eol`), `sizing` (`bool`, default sí). Más adelante: `duration` e `initial_temperature` para transitorios (LEOP).

### 4. Rangos y heaters (`limits`)

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `off_lower_limit` | `enum` (`switch_on` \| `non_operating`) | — | `switch_on` | *(opinión, conservador)* |
| `separately_controlled_items` | `list[ref(items)]` | — | Vacía | *(opinión)* |
| `heater_power_margin` | `float` (fracción) | — | 0,25 | [3, cap. 15, Tabla 15.2 y p. 555] |

### 5. Modelo térmico (`thermal_model`)

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `effective_specific_heat` | `float` | J/(kg·K) | 900 | *(opinión)*; aluminio [6, Fig. 4-1] |
| `specific_heat_uncertainty` | `float` (fracción) | — | 0,3 | *(opinión)* |

### Validaciones

- **Parámetros:** α y ε en (0, 1]; `effective_emittance_min` > 0 y ≤ `effective_emittance_max` (`order`); cp > 0; margen de heaters ≥ 0; incertidumbre de cp en [0, 1); caras candidatas dentro de las permitidas por Misión (`not_allowed`); `selected_face` entre las candidatas; los obligatorios de presets sin valor (`required`).
- **Referencias** (`invalid_reference`), contra el contexto: modos operativos, modos de actitud, condiciones y equipos.
- **Al actualizar:** `missing` y `context_invalid` como en Entorno ([ADR 0022](../adr/0022-contrato-de-etapas-de-calculo.md)). Un modo sin rango admisible o una cara no factible **no** hacen fallar la celda: son resultados con aviso *(opinión)*.

## Propuesta de resultado

### Qué calcula, en orden

1. Disipación de cada modo operativo, con la función de Equipos ([ADR 0026](../adr/0026-derivados-y-editores-propios-de-formularios.md)).
2. Rango de diseño y admisible de cada modo ([sección 4](#4-rango-común-de-temperatura-y-márgenes)).
3. Candidatos: condición × actitud compatible × modo operativo, caliente y frío, cada uno con los dos ε*; más los casos propios.
4. Por cara candidata: área requerida, área pasiva, heaters con el área y casos que mandan.
5. Cara elegida y punto de diseño.
6. Temperaturas libres, márgenes de diseño, τ y temperaturas de sumidero.
7. Oscilación orbital de los casos dimensionantes (transitorio de un nodo con los perfiles de Entorno, en los dos extremos de C).
8. Avisos.

### Partes

| Parte | Contenido |
|---|---|
| `inputs_used` | Disipación por modo, áreas de las caras, C y su banda, u, propiedades ópticas usadas con su fuente (valor de preset o cargado) |
| `ranges` | Por modo operativo: rango de diseño, rango admisible, equipo que fija cada extremo, factible o no, equipos en conflicto; intersección global informativa |
| `cases` | Por candidato y caso propio: origen (`hot`, `cold`, `custom`), condición, actitud, modo, lado, BOL/EOL, ε* usada, Q, flujos absorbidos por cara; por cara candidata: área requerida (caliente) o heaters y temperatura libre (frío); τ; si dimensiona |
| `faces` | Por cara candidata: factible, área requerida y caso que manda, fracción de la cara, rechazo neto (W/m²), área pasiva y caso que manda, heaters y caso que manda |
| `design_point` | Cara, área, heaters, heaters con margen frente al presupuesto, ventana pasiva, temperaturas libres caliente y fría |
| `sink_temperatures` | Por condición × actitud × cara: sumidero del radiador y de la capa externa, promedio y pico |
| `dynamics` | τ, τ / período, oscilación orbital de los casos dimensionantes en los extremos de C |
| `warnings` | Código, mensaje y referencia (área, factibilidad, presupuesto, masa de equipos, rango vacío, τ corta, defaults fuera de alcance) |
| `provenance` | Celdas y cambios del contexto, parámetros usados, proveedor y versión ([ADR 0021](../adr/0021-etapas-de-calculo.md)) |

Todo es chico (decenas a miles de filas): JSON en el `.hestia`, como Entorno.

## Lo que queda abierto

Cada punto con su recomendación; decidir antes de especificar.

1. **Semántica de los límites de Equipos.** Recomendado: son límites de diseño ECSS; documentarlo en `equipment.md`. Alternativa: un campo por equipo que diga si son de diseño, aceptación o calificación, y derivar.
2. **Incertidumbre por defecto de Misión.** Recomendado: 15 K para la fase 0 [2], con 10 K como piso [1]. Hoy es 10 K. ¿Una sola política para las fases 0 y 1, o un valor por fase?
3. **Margen de heaters: de temperatura, de potencia o ambos.** ECSS pide que la predicción quede dentro del rango de diseño; Gilmore y GSFC tratan el margen de los equipos controlados por heaters como margen de potencia **en lugar** del de temperatura [3, 9]. Recomendado: heaters calculados para mantener `T_mín,d + u` y además informar la potencia con `m_h` = 25 % frente al presupuesto (conservador, doble). Alternativa GSFC: sin `u` en el lado frío controlado y 70 % de ciclo de trabajo.
4. **Recubrimiento por defecto y alcance del α EOL.** Recomendado: Teflon plateado con α EOL 0,14 por defecto y aviso fuera de LEO o con vida mayor que ~4,5 años. Alternativa estricta: α EOL siempre obligatorio.
5. **Compatibilidad actitud ↔ modo operativo.** Recomendado: por defecto todas con todos, y el resultado muestra qué combinación dimensiona para que el usuario la restrinja. Alternativa: exigirla.
6. **Modos con duración máxima** (`max_duration`). Recomendado para la primera versión: tratarlos como estacionarios (conservador) y avisar si dimensionan. Después: transitorio desde el modo previo (un caso propio con modo previo, duración y temperatura inicial). Ídem LEOP.
7. **Presupuesto de heaters de supervivencia.** Misión tiene un solo `heater_power_budget`. ¿Se agrega uno de supervivencia o modo seguro, o se marca qué modos operativos son de supervivencia?
8. **Límite inferior de los equipos apagados:** mínimo de encendido (recomendado) o no operativo.
9. **Equipos con control propio** fuera de la intersección: ¿se incluye en la primera versión?
10. **Margen de madurez de la disipación** (equipos nuevos frente a heredados). No se encontró fuente en esta investigación. ¿Va por equipo en Equipos, global en el balance, o no va?
11. **Gradiente entre equipos y radiador.** Un nodo lo ignora; la incertidumbre de fase 0 lo cubre en parte *(opinión)*. ¿Se agrega un ΔT explícito? Sin fuente para un default.
12. **Albedo e IR correlacionados y tiempo de promediado (Entorno).** Hoy Entorno suma máximos con máximos (conservador). Opciones: pares de NASA por tipo de caso (dominado por albedo, por IR o combinado) [4]; el balance informa τ para elegir el tiempo de promediado. Recomendado como default de Entorno: los valores de 90 min, conservadores frente a las τ de horas de un satélite mediano *(opinión)*.
13. **Paneles solares montados en el cuerpo:** una cara con celdas (α alto y parte de la energía convertida) no entra en el modelo radiador + MLI. ¿Primera versión o después?
14. **Avisos en el contrato del resultado.** Hoy los problemas hacen fallar la celda; el balance necesita `warnings` que no fallen. Afecta el contrato común de etapas de cálculo ([ADR 0022](../adr/0022-contrato-de-etapas-de-calculo.md)): probablemente pida un ADR.
15. **Umbral de τ / período** para el aviso de validez del promedio (constante con nombre en `hestia_core`).

## Supuestos de física para `physics-reviewer`

1. **Nodo isotermo:** toda la masa y los equipos a una temperatura; el radiador a la temperatura del nodo (sin gradiente ni eficiencia de aleta).
2. **Promedio orbital exacto con inercia infinita:** con T constante, el balance es lineal en los flujos y en σT⁴, así que los promedios de Entorno bastan. Verificar que la capa externa del MLI sin masa no rompe esa linealidad.
3. **Superficies grises y difusas:** absorbido = α (solar + albedo) + ε · IR; el albedo tiene espectro solar.
4. **MLI:** ε* constante con la temperatura (Gilmore da una correlación que depende de la temperatura media [3, cap. 5, p. 168]); capa externa sin masa; la expresión cerrada de `m_f`. Contrastar con [5, ec. 6-2].
5. **Geometría:** caja convexa sin sombras propias ni intercambio con paneles o apéndices (limitaciones de Entorno); el radiador ve solo espacio y Tierra.
6. **Monotonía:** caliente = flujos máximos + α EOL y frío = flujos mínimos + α BOL dan los extremos. Revisar la condición σT⁴ > E_r en un radiador frío que mira a la Tierra a baja altura.
7. **ε*:** evaluar los dos extremos y quedarse con el peor es suficiente.
8. **Fórmulas cerradas** (`A_req`, `A_pas`, `P`, temperatura libre): signos, unidades y residuo de energía nulo en la solución.
9. **Casos borde:** área ≤ 0, denominador ≤ 0 (cara que no rechaza), sin eclipse (SSO crepuscular), Q = 0, rango vacío, una sola cara candidata.
10. **Apilado de peores casos** (EOL + perihelio + albedo e IR máximos + disipación máxima): conservador; cuantificar cuánto frente a los pares de NASA.
11. **τ linealizada** `G = 4σT³(...)` y transitorio a régimen periódico: integrador, paso, tolerancia de convergencia y sensibilidad a C.
12. **Lógica del rango:** intersección por modo y reglas de respaldo para límites faltantes.
13. **Caso de referencia:** el ejemplo POAM de Gilmore [3, cap. 15, pp. 555–560] da área de radiador y temperatura fría con todos sus datos. Sirve de test con tolerancia y cita, leyendo los números del libro (la copia consultada tiene la ecuación 15.20 parcialmente ilegible).

## Fuentes

**Consultadas**

1. ECSS-E-ST-31C. *Space engineering — Thermal control general requirements*. ECSS Secretariat, ESA-ESTEC, Noordwijk, 15 de noviembre de 2008. Usadas: §3.2.1.1–3.2.1.20 y Fig. 3-1 (rangos y márgenes), §3.2.1.22 (temperatura de sumidero radiativo), §3.2.1.37 (caso de diseño), §4.1.1–4.1.4 (fases de la misión), §4.2.1 (casos de diseño, temperaturas y márgenes, asignación de potencia y masa), §4.4.1 d (propiedades degradadas), §4.5.2.1 c (incertidumbres). <https://ecss.nl/standard/ecss-e-st-31c-thermal-control/>
2. ESA. *ECSS-E-ST-31 Standardisation Training Course 2023*, Rev. 1. ESA Space Standardization, 2023. Diapositivas 59, 66, 69, 114, 115, 119, 120 y 121. <https://ecss.nl/wp-content/uploads/2023/05/ESA_ECSS-E-ST-31_Standardisation_Training_Course_2023_Rev1.pdf>
3. Gilmore, D. G. (ed.). *Spacecraft Thermal Control Handbook, Volume I: Fundamental Technologies*, 2.ª ed. The Aerospace Press / AIAA, El Segundo, 2002. Capítulos usados:
   - cap. 2, Clawson, Tsuyuki, Anderson, Justus, Batts, Ferguson y Gilmore, «Spacecraft Thermal Environments», pp. 22–31;
   - cap. 4, Gilmore, Stuckey y Fong, «Thermal Surface Finishes», pp. 143–155: Tabla 4.1 (p. 144) y Figs. 4.7, 4.9, 4.10 y 4.11;
   - cap. 5, Donabedian, Gilmore, Stultz, Tsuyuki y Lin, «Insulation», pp. 165–168;
   - cap. 6, Gilmore, «Radiators», pp. 207–209;
   - cap. 7, Gilmore, Lyra y Stultz, «Heaters», p. 230;
   - cap. 15, Gilmore y Collins, «Thermal Design Analysis»: Tabla 15.2 (pp. 532–533), pp. 536–537 y ejemplo POAM, pp. 553–560 (Tabla 15.5, ec. 15.16–15.21).
4. Anderson, B. J., Justus, C. G. y Batts, G. W. *Guidelines for the Selection of Near-Earth Thermal Environment Parameters for Spacecraft Design*. NASA/TM-2001-211221, Marshall Space Flight Center, octubre de 2001. §4.2.2 y §4.2.3 (Tablas 4.2.3-1 a 4.2.3-3). <https://ntrs.nasa.gov/citations/20020004360>
5. ECSS-E-HB-31-01 Part 7A. *Space engineering — Thermal design handbook — Part 7: Insulations*. ECSS Secretariat, ESA-ESTEC, 5 de diciembre de 2011. Ec. [6-2] (definición de la emitancia efectiva). <https://ecss.nl/hbs/active-handbooks/>
6. ECSS-E-HB-31-01 Part 5A. *Space engineering — Thermal design handbook — Part 5: Structural Materials: Metallic and Composite*. ECSS Secretariat, ESA-ESTEC, 5 de diciembre de 2011. Fig. 4-1 (aluminio) y Tabla 5-8 (compuestos). <https://ecss.nl/hbs/active-handbooks/>
7. Henninger, J. H. *Solar Absorptance and Thermal Emittance of Some Common Spacecraft Thermal-Control Coatings*. NASA RP-1121, Goddard Space Flight Center, abril de 1984. Tablas de pinturas blancas (p. 8) y de películas y cintas (pp. 15–16). <https://ntrs.nasa.gov/citations/19840015630>
8. Remaury, S., Nabarra, P., Bellouard, E. y d'Escrivan, S. (CNES). «In-flight thermal coatings ageing on the THERME experiment». 11th International Symposium on Materials in a Space Environment (ISMSE-11), 2009. Tablas 2 a 7 y §5.1. <http://esmat.esa.int/materials_news/isme09/pdf/10-In-flight/Remaury%20Paper.pdf>
9. Peabody, H. L. y Peabody, S. A. S. «Gaps in Thermal Design Guidelines in the Goddard Space Flight Center GOLD Rules». ICES-2018-268, 48th International Conference on Environmental Systems, Albuquerque, julio de 2018. §I, con la cita textual de la regla térmica de GSFC-STD-1000 Rev. G (2016). <https://ntrs.nasa.gov/citations/20180004564>

**No consultadas** (pendientes de verificar; no respaldan ningún valor de este informe)

- Karam, R. D. *Satellite Thermal Control for Systems Engineers*. Progress in Astronautics and Aeronautics, vol. 181. AIAA, Reston, 1998. Según su índice publicado, la parte 1 trata la especificación de temperaturas, la 5 el análisis térmico del satélite (soluciones analíticas aproximadas y transitorios) y la 7 los ensayos con márgenes de temperatura: conviene contrastar con este informe las secciones 1 y 4.
- GSFC-STD-1000 Rev. G, *Rules for the Design, Development, Verification, and Operation of Flight Systems*, Goddard Space Flight Center, 2016. Citada a través de [9].
