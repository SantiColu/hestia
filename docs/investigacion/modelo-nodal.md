# Modelo nodal (`discretization`, `couplings`): cómo se arma un TMM de prediseño

**Fecha:** 2026-10-06
**Estado:** investigación para revisar antes de especificar las etapas (tema 2 de [topics.md](topics.md)). No es especificación ni ADR; nada de esto está implementado. Parte de lo que usa (el balance y el concepto TCS, con su `TcsArchitecture`) tampoco está implementado.

## Alcance y cómo leer

- Una sección por pregunta: primero la recomendación, después la práctica, las alternativas y las fuentes. Al final: la propuesta de parámetros y de resultado de las dos etapas (coherente con el [ADR 0021](../adr/0021-etapas-de-calculo.md) y con lo que entrega `tcs_concept`), lo que queda abierto y los supuestos para `physics-reviewer`.
- **Respaldo y opinión:** lo respaldado lleva su referencia entre corchetes, `[n, lugar]`, numerada como en [Fuentes](#fuentes). El criterio propio va marcado *(opinión)*. Los números que calculé yo dicen *(cálculo propio)*; los leídos de una figura, *(digitalizado)*.
- **Qué se leyó:** ECSS-E-ST-31C, anexos A y B [1]; el curso de ESA sobre esa norma [2]; el **handbook de análisis térmico ECSS-E-HB-31-03A** (2016) [3], que no estaba en la copia local y resultó la fuente más directa para este tema; Gilmore 2.ª ed., caps. 3, 4, 5, 6, 8, 15 y 16 [4]; ECSS-E-HB-31-01, partes 1 (factores de vista) [5], 4 (conducción, cláusula 5) [6], 5 (materiales) [7], 8 (heat pipes) [8] y 15 (satélites existentes) [9]; la filosofía de márgenes de ESA [10]; las tablas de masa por subsistema de TU Delft [11]; el borrador de NASA sobre correas [12]; un informe CDF de ESA [13]; un artículo sobre el análisis no lineal de redes térmicas [14]; un artículo de NASA sobre conducción en núcleos de honeycomb [15]; la documentación de pyViewFactor [16] y el resumen de un artículo sobre el cp de celdas de ion-litio [17]. **No se consultaron** los apéndices de Gilmore (la copia online no los tiene), Siegel y Howell ni Swann y Pittman: ver [Fuentes](#fuentes).
- **Copia local:** todo lo bajado quedó en `docs/investigacion/fuentes/` (ignorada por git), con el texto extraído al lado.
- «Práctica de la industria» es la documentada en normas, manuales y ejemplos publicados. Los procedimientos internos de cada empresa varían y no están al alcance.

## Resumen

1. **Qué modelo es:** el TMM de prediseño de la industria es una red de parámetros concentrados: nodos (difusivos, aritméticos y de borde), conductores lineales y radiativos, y fuentes [1, §3.2.1.38], [4, cap. 15, pp. 539–552]. En la fase A es **grueso**: la mayoría de los ítems no se modelan aparte, van con la estructura; en la fase B los críticos se modelan explícitamente; en C/D, todos [3, §6.1]. La regla es el **mínimo de nodos** que verifica el diseño [4, cap. 15, p. 535], con un error de discretización 5 a 10 veces menor que la incertidumbre [3, §4.5.2].
2. **Discretización automática en Hestia:** reglas deterministas sobre la envolvente, la arquitectura del concepto y Equipos: un nodo por panel de cara (con la zona de radiador aparte), un nodo aritmético por capa externa de MLI, un nodo por equipo (es su punto de referencia de temperatura), una plataforma interna, los radiadores propios, un nodo de vapor por heat pipe y el espacio. Para un satélite mediano con 25 equipos son ~45 nodos *(cálculo propio)*. El usuario decide subdivisiones, agrupamientos, montajes y nodos extra; todo con ids estables derivados de los ids de origen.
3. **Capacidad:** `C = Σ m·cp` por nodo. Equipos con su masa; la masa sin asignar (Misión − equipos − TCS − propelente − arnés) va a la estructura, repartida por área, y se compara con el 17–23 % de masa seca típico [11]. El total de masa del modelo tiene que cerrar contra Misión [3, §5.2].
4. **Conductancias:** con fórmulas cerradas y valores de catálogo con fuente: contacto equipo–panel 90 W/(m²·K) sin relleno y ~390 con RTV para un perímetro abulonado [4, cap. 8, p. 271, Fig. 8.21]; esparcimiento en el panel con la fórmula del anillo [4, cap. 15, Fig. 15.14], [3, §4.5.2]; aisladores de 50–400 K/W [4, cap. 8, p. 312]; heat pipes con conductancias por metro de evaporador y condensador de catálogo [8, Tablas 9-6 y 9-10]; MLI como conductor radiativo σε*A [3, A.1.3]. Incertidumbres de prediseño: ±50 % en lineales y MLI, ±10 % en radiativos internos, ±20 % en externos [3, Tabla 6-1].
5. **Radiación:** dos cavidades, externa e interna [3, §4.7.6]. Afuera, con la envolvente convexa y sin apéndices, cada superficie ve solo el espacio: exacto y cerrado. Adentro, factores de vista cerrados entre las seis paredes [5, ec. 4-36 y §4.3.2.3], equipos como objetos chicos y factores de Gebhart con numpy. **pyViewFactor** calcula bien factores de vista entre polígonos planos (error < 10⁻⁵ contra el analítico), pero la obstrucción es binaria por par de caras y no hace reflexiones, especularidad ni flujos orbitales [16]: sirve, en `hestia_adapters`, recién cuando Hestia tenga geometría (apéndices, posiciones de equipos).
6. **Ópticas:** las de cada cara salen de `TcsArchitecture.surfaces` (radiador con α BOL/EOL y ε; MLI con ε* y capa externa); el interior, pintura negra (ε 0,89) [4, cap. 4, pp. 141, 144]. La red guarda BOL y EOL; `load_cases` elige según el caso [3, §4.7.3].
7. **Verificación antes de resolver:** chequeos de topología de ECSS (nodos o grupos aislados, conductores nulos o negativos, capacidades nulas, masa total) [3, §5.2], conectividad de cada nodo con el espacio, suma y reciprocidad de factores de vista [5, ec. 4-6], cavidad interna sin flujos externos [3, §4.7.6], áreas y masas contra la arquitectura, y la **prueba de colapso**: con conductancias internas muy grandes, la red tiene que reproducir el balance de un nodo.
8. **Entrega:** un artefacto versionado `ThermalNetwork` (nodos, superficies, conductores lineales y radiativos con su clase de incertidumbre, mapa de fuentes) que `load_cases` completa con flujos y disipaciones por caso y `solution` resuelve.

## 1. Discretización

### Recomendación

- **Nivel de detalle:** el de una fase A tardía o B temprana *(opinión)*: los equipos se modelan explícitamente porque Equipos ya los tiene con sus límites, y la estructura queda gruesa (un nodo por panel). Es lo que ECSS describe para la fase B: «modelo global donde los ítems críticos se modelan explícitamente» [3, §6.1]; Hestia los modela todos porque cada fila de Equipos ya trae su rango de temperatura, y cada uno necesita un nodo para verificarlo (observabilidad del punto de referencia de temperatura, TRP) [3, §4.5.3].
- **Discretización automática por reglas** sobre Misión (envolvente), `TcsArchitecture` y Equipos, siempre en el mismo orden y con ids derivados de los ids de origen:

  | Regla | Nodos que genera | Tipo | De dónde sale |
  |---|---|---|---|
  | D1. Panel por cara | Un nodo por cara de la envolvente (6) | Difusivo | Misión (envolvente) |
  | D2. Zona de radiador | Si una cara tiene radiador estructural en parte de su área, el panel se parte en dos nodos: zona de radiador y resto | Difusivo | `TcsArchitecture.radiators` (`mounting: structural`) |
  | D3. Radiador montado al cuerpo | Un nodo por radiador `body_mounted`, con su masa | Difusivo | `radiators`, `budgets` |
  | D4. Capa externa de MLI | Un nodo por zona de MLI de cada cara (la capa externa) | Aritmético (sin capacidad) | `insulation`, `surfaces` |
  | D5. Equipos | Un nodo por fila de Equipos (con `quantity` > 1, un nodo con la masa total: los ítems están siempre en el mismo modo) | Difusivo | Equipos |
  | D6. Plataforma interna | Un nodo si hay equipos `internal` | Difusivo | Equipos (`location`) |
  | D7. Control propio | El equipo sigue en su nodo (D5); su radiador propio, un nodo; su MLI propia, un nodo aritmético | Difusivo / aritmético | `own_control_items` |
  | D8. Heat pipes | Un nodo de vapor por línea de transporte | Aritmético | `heat_transport` |
  | D9. Espacio | Un nodo de borde a 0 K (o 3 K) | Borde | — |
  | D10. Nodos del usuario | Bordes (p. ej. un panel solar a temperatura dada) y difusivos extra (p. ej. un tanque que no está en Equipos) | Cualquiera | Parámetros |

- **Tamaño resultante** *(cálculo propio)*: 6 o 7 paneles (con una zona de radiador), 6 capas de MLI, 1 plataforma, 25 equipos, 2 radiadores propios, 2 nodos de vapor y el espacio dan ~45 nodos. Resolver eso en estacionario o en transitorio cuesta milisegundos con numpy y SciPy.
- **Lo que decide el usuario** (parámetros, con autor y procedencia como todo):
  - **subdivisión por cara** (n × m celdas; default 1 × 1), para ver gradientes en un panel con mucha potencia;
  - **agrupamientos** de equipos en un nodo (p. ej. un grupo de tarjetas idénticas), y la **celda** de una cara subdividida donde va cada equipo;
  - **montaje** de cada equipo: el panel de su `location` (default), la plataforma interna u otro nodo;
  - **nodos extra** (D10) y sus acoplamientos;
  - **reparto de la masa** de estructura (ver sección 2).
- **Ids estables y legibles** *(opinión)*: derivados del origen, p. ej. `pnl_px`, `pnl_px_rad`, `mli_px`, `itm_<id del equipo>`, `rad_<id del radiador>`, `hp_<id del transporte>`, `plt_internal`, `space`. Como los ids de origen no cambian (ADR 0025), los parámetros que refieren nodos sobreviven a una nueva discretización. Además, un número entero por nodo con la jerarquía tipo / subconjunto / secuencia que sugiere ECSS [1, anexo A <5>], para exportar a otras herramientas.
- **Aviso de panel no isotermo:** para cada panel de un nodo, Hestia calcula el parámetro de aleta de Gilmore y avisa si el panel isotermo sobreestima el rechazo (ver justificación). No subdivide solo: la subdivisión es decisión del usuario *(opinión)*.

### Cómo se hace en la práctica

- **Definición:** un TMM es una representación numérica con nodos de capacidad concentrada acoplados por conductores radiativos, conductivos y convectivos [1, §3.2.1.38]; un nodo es un volumen con una temperatura y propiedades representativas [1, §3.2.1.39]. La ecuación de cada nodo es `C dT/dt = Σ G (Tj − Ti) + Σ R σ (Tj⁴ − Ti⁴) + Q` [2, diap. 113 y 122].
- **Tres tipos de nodo:** difusivo (capacidad finita), aritmético (capacidad nula: superficies, capas de MLI, piezas livianas) y de borde (temperatura fija: espacio, paneles solares con temperatura impuesta) [4, cap. 15, pp. 540–541]. Los aritméticos deberían ser pocos frente al total y requieren cuidado en transitorios [4, cap. 15, pp. 540, 544].
- **Cuántos nodos:** no hay un número de la industria; hay un criterio:
  - el modelo tiene que tener el mínimo de nodos necesario para verificar el diseño [4, cap. 15, p. 535], y en un estudio de concepto valen más muchas corridas paramétricas con un modelo chico que pocas con uno grande [4, cap. 15, p. 525];
  - la discretización alcanza cuando las salidas clave dejan de depender de ella; idealmente la variación es 5 a 10 veces menor que la incertidumbre aplicada. Más fino es contraproducente: más datos, más errores y una «ilusión de precisión», porque los errores de los datos de entrada no se recuperan refinando [3, §4.5.2];
  - en el diseño conceptual, con la configuración poco clara, se usan modelos más simples, con conductores de esparcimiento basados en un camino circular para compensar la malla gruesa [3, §4.5.2].
- **Por fase** [3, §6.1]:

  | Fase | Modelo | Incertidumbre típica |
  |---|---|---|
  | A | Modelo global grueso; la mayoría de los ítems van con la estructura | ±15 K |
  | B | Modelo global con los ítems críticos explícitos | ±10 K |
  | C/D | Modelo detallado, todos los ítems explícitos | ±8 K antes del ensayo de balance, ±5 K después |

  El curso de ESA da lo mismo: ±15 K en fase 0/A y ±10 K en B/C [2, diap. 120]. En la fase 0 se dimensiona con un nodo: en el estudio CDF de ATHENA, el módulo de servicio se dimensionó como un bloque a 20 °C con 500 W de disipación, de donde salieron 2,4 m² de radiador y 411 W de heaters [13, §11.2, pp. 181–182].
- **Modelos reales (detallados, no de prediseño):**
  - IUE: 165 nodos los instrumentos, 186 el resto del satélite y 250 la zona de propulsión [9, §4.8, p. 25];
  - SPOT 1: 260 nodos la plataforma; propulsión en tres modelos de 110, 100 y 40 nodos; baterías en un modelo de 36 nodos para la temperatura media y modelos de 105 y 250 para los gradientes [9, §8.8.1–8.8.2, pp. 92–93]; la telemetría de carga útil en modelos de 13, 35 y 200 nodos, reducidos e integrados en uno global [9, §8.8.4, p. 95];
  - Olympus-1 (satélite grande de comunicaciones): dos modelos de 185 y 195 nodos con 850 conductores cada uno; **al menos un nodo por unidad electrónica** y varios en las críticas (los TWT); a veces un modelo local de varios nodos se reducía a conductores equivalentes en el modelo final [9, §9.6, pp. 106–107].
- **Qué fija ECSS:** la especificación de modelos define los subconjuntos, los nodos de interfaz, el número máximo de nodos por subconjunto, la numeración, la jerarquía del modelo (satélite, subsistema, conjunto, unidad) y las reglas de modelado por tipo de ítem (cuántos nodos por equipo disipativo, MLI, cañerías, heat pipes) [1, anexo A <4>–<6>]. La descripción del modelo lista nodos con su capacidad, área y disipación, y los acoplamientos [1, anexo B <5>].
- **Organización:** dividir el modelo en módulos y usar grupos desde el principio; los grupos facilitan los reportes de flujos de calor [3, §4.4].
- **Ubicación de los equipos:** en un satélite de tres ejes, los equipos de mucha disipación van montados en las paredes, con camino conductivo directo al radiador; los montados en plataformas internas irradian su calor a las paredes [4, cap. 3, p. 73]. Es exactamente lo que dice `location` en Equipos: una cara o `internal`.

### Alternativas

| Alternativa | A favor | En contra |
|---|---|---|
| Discretización por reglas sobre la arquitectura (recomendada) | Reproducible; un cambio en Equipos o el concepto rehace la red sola; el usuario solo decide excepciones | Las reglas no conocen la geometría real (posiciones, plataformas) |
| Red armada a mano por el usuario | Total control, como en ESATAN | No reproducible ni automatizable; mucho trabajo para una fase de prediseño |
| Malla de la envolvente (n × n por cara) con pyViewFactor | Gradientes en paneles, factores de vista generales | Sin posiciones de equipos, la malla no agrega información; más nodos sin más precisión [3, §4.5.2] |
| Un nodo por subsistema (fase A pura) | Mínimo | No verifica los límites de cada equipo, que es para qué existe la fase 1 |

### Justificación y fuentes

- **Un nodo por equipo:** Equipos ya da límites por fila, y `margins` va a verificar márgenes por equipo y por caso (catálogo del workflow). Sin un nodo por fila, esa etapa no tiene qué verificar. Olympus usaba al menos un nodo por unidad [9, §9.6, p. 106]. Que el equipo sea isotermo es el supuesto de la fase B *(opinión)*.
- **Un nodo por panel:** el panel de honeycomb conduce bien entre caras a través del núcleo de aluminio y lateralmente sobre todo por las pieles [4, cap. 6, p. 209]. Con un nodo por panel se pierde el gradiente lateral, que es justamente el «gradiente equipo–radiador» que el balance dejó para la fase 1 ([datos-entorno-y-balance.md](datos-entorno-y-balance.md#42-gradiente-entre-equipos-y-radiador)). Por eso el conductor de esparcimiento (sección 3) y la opción de subdividir.
- **Cuánto se equivoca un panel isotermo** *(cálculo propio con [4, cap. 6, ec. 6.5–6.7, pp. 218–219])*: Gilmore da la efectividad de una aleta radiante en función de `ξ = σ L² T³ (ε₁ + ε₂) / (k t)`, con L la mitad de la distancia entre fuentes, k y t la conductividad y el espesor. Para un panel de aluminio con pieles de 2 × 0,5 mm (k = 167 W/(m·K)), ε = 0,8 de un lado, 20 °C y L = 0,5 m, ξ ≈ 1,7 y la efectividad es ≈ 0,44 contra un sumidero a 0 K; con L = 0,25 m, ξ ≈ 0,43 y ≈ 0,68. Gilmore muestra que un radiador de mínima masa queda con efectividad ~0,5 [4, cap. 6, pp. 219–220]. Un panel de un nodo equivale a suponer efectividad 1, aunque el calor entre por la zona de los equipos: el aviso señala cuándo eso se aleja mucho de la realidad.
- **MLI aritmético:** la MLI tiene capacidad muy chica y suele modelarse con nodos aritméticos; conviene que el patrón de nodos de la MLI siga al de la superficie que cubre, para no crear acoplamientos artificiales [3, A.1.2–A.1.3].
- **Heat pipes con nodo de vapor:** el patrón clásico es la pared discretizada en el eje y el vapor en un nodo aritmético, con coeficientes de evaporación y condensación; así la conductancia no depende de la longitud. La alternativa (una barra de conductividad muy alta) la hace depender de la longitud [3, A.2.3]. Con muchos heat pipes en un panel, alcanza con aumentar la conductividad del panel en el modelo global [3, A.2.2].
- **Aritméticos y transitorio:** fuentes grandes en nodos aritméticos con conductores radiativos producen oscilaciones [4, cap. 15, p. 552], y una dispersión grande de conductancias (factor ~1000) puede frenar o desestabilizar los solvers [3, §4.5.2]. Es tema de `solution` (tema 3), pero conviene que la red lo informe.

## 2. Capacidad y masa por nodo

### Recomendación

- **Capacidad por nodo:** `C = Σ mᵢ cᵢ` sobre lo que el nodo representa [4, cap. 15, ec. 15.3, p. 544], con cp constante a temperatura ambiente en la primera versión *(opinión: las propiedades dependen de T, pero puede suponerse constante en un rango limitado [3, §4.5.5])*. Los aritméticos y bordes, sin capacidad.
- **Equipos:** masa = `quantity × mass` de Equipos; cp por subsistema con default.
- **Masa sin asignar** (la estructura y lo que nadie cargó):

  `m_estructura = m_Misión − Σ m_equipos − m_TCS − m_propelente − m_arnés`

  - `m_TCS`: de `TcsArchitecture.budgets` (masa por componente sin margen de madurez *(opinión: el margen es incertidumbre de presupuesto, no masa física)*). Los radiadores montados al cuerpo van a su nodo; la MLI, al panel que cubre (su capa externa es un nodo aritmético, sin capacidad); lo demás (heaters, termostatos), al nodo que calientan.
  - `m_propelente`: parámetro (o `m_Misión − dry_mass`, si Misión suma la masa seca: abierto 2). Va al nodo del tanque: un equipo de propulsión elegido por el usuario o un nodo extra.
  - `m_arnés`: fracción de la masa seca, default 5 % [10, R-M1-7], repartida con la estructura *(opinión: el arnés está distribuido)*.
  - La estructura se reparte entre los paneles proporcionalmente al área y una fracción a la plataforma interna (default: proporcional a su área, contada como una placa del tamaño de la mayor sección de la envolvente) *(opinión)*.
- **Chequeos:**
  - `m_estructura` > 0; si no, la celda falla (`mass_overrun`): los equipos pesan más que el satélite.
  - Fracción de estructura entre 10 % y 35 % de la masa seca; fuera de eso, aviso *(umbral: opinión sobre los datos de [11]: 17,1 ± 3,6 % en 11 GEO, 20,9 ± 3,2 % en 17 satélites, 23,3 % en 13 chicos)*.
  - Σ masa de los nodos = masa de Misión, para que el modelo y el presupuesto no diverjan [3, §5.2].
- **Defaults de cp:**

  | Qué | cp (J/(kg·K)) | Fuente |
  |---|---|---|
  | Estructura de aluminio (Al 6061) | 963 (entre ambiente y 373 K) | [7, Al-1Mg-0,6Si, p. 104] |
  | Equipos electrónicos | 900 (aluminio) | *(opinión: sin fuente para el cp de una unidad; ver abajo)* |
  | Baterías de ion-litio | 1000 | 960 ± 20 a 2,75 V y 1040 ± 20 a 3,75 V en una celda 18650 [17] (solo el resumen) |
  | Hidracina líquida | 3084 (298 K) | [datos-entorno-y-balance.md, T8](datos-entorno-y-balance.md#t8-calor-específico) |
  | Compuestos | 750–1300 según fibra y matriz | [datos-entorno-y-balance.md, T8](datos-entorno-y-balance.md#t8-calor-específico) |

- **Incertidumbre de la capacidad** guardada en cada nodo: ±25 % equipos, ±15 % estructura [3, Tabla 6-2], para que `sensitivity` la use.

### Alternativas

| Alternativa | A favor | En contra |
|---|---|---|
| Resto de masa a la estructura, por área (recomendada) | Cierra contra Misión; usa solo datos que existen | El reparto real depende del diseño estructural |
| Masa de estructura por fracción típica (~21 %) | No depende de que Misión y Equipos sean coherentes | No cierra la masa; dispersión ±3 % [11] |
| Masa de cada panel cargada por el usuario | Exacta si se conoce | En prediseño casi nunca se conoce |
| Arnés como nodo propio | Visible | Está distribuido; un nodo concentrado no tiene sentido físico *(opinión)* |

### Justificación y fuentes

- **ECSS pide seguir la masa:** mantener controlada la masa total representada en el modelo y que no difiera mucho de la del presupuesto del sistema [3, §5.2]. La regla de resto lo garantiza por construcción.
- **Datos de masa:** la estructura es en promedio el 20,9 % (desvío 3,2) de la masa seca en 17 satélites grandes, 17,1 % (3,6) en 11 GEO y 23,3 % en 13 chicos; el arnés aparece explícito solo en los chicos, con 5,4 % de promedio, y en los demás puede estar cargado en potencia o en manejo de datos [11, apéndice D, Tablas 1–3, pp. 184–185]. ESA pide considerar al menos 5 % de arnés [10, R-M1-7].
- **cp de los equipos:** no se encontró un cp efectivo de unidades electrónicas en lo consultado. El handbook de ECSS asigna a la capacidad de equipos una incertidumbre de ±25 % y a la de estructuras ±15 % [3, Tabla 6-2], lo que sugiere que en la práctica se estima con márgenes grandes. El default de aluminio es *(opinión)*.
- **Por qué la capacidad pesa poco en LEO:** el balance mostró que la constante de tiempo del satélite es de horas frente a un período de ~1,6 h ([balance-global.md](balance-global.md#1-modelo-térmico-sin-inercia-conocida)); en el TMM, la capacidad importa en los transitorios de nodos livianos (paneles, radiadores, MLI) y en los eventos de duración acotada. ECSS pide cuidar la capacidad de lo liviano y expuesto [3, §4.5.4].

## 3. Conductancias

### Recomendación

Todo conductor lineal se calcula con una fórmula cerrada y datos con fuente, y guarda su **clase** (contacto, esparcimiento, aislador, heat pipe, correa, junta de paneles, usuario) y su **incertidumbre** para `sensitivity`.

| Conductor | Fórmula | Default | Fuente |
|---|---|---|---|
| Equipo → panel (contacto) | `G = h · A_huella` | `h` = 90 W/(m²·K) sin relleno; ≈ 390 con RTV (perímetro abulonado, 26,6 cm²/tornillo, placas delgadas). Default: con relleno | [4, cap. 8, p. 271] (90,8); [4, Fig. 8.21] *(digitalizado, ±10 %)*; uso de RTV en paneles de pieles delgadas [4, cap. 8, p. 284] |
| Esparcimiento en el panel | `G = 2π k t / ln(r_o / r_i)`, con `t` la suma de las pieles, `r_i = √(A_huella/π)` y `r_o = √(A_celda/π)` | Pieles de Al 6061 de 2 × 0,5 mm, k = 167 W/(m·K) | Fórmula: [4, cap. 15, Fig. 15.14, p. 547]; uso en modelos conceptuales: [3, §4.5.2]; k: [7, p. 104]; pieles de 0,4–1,2 mm: [4, cap. 8, p. 274] |
| Equipo → nodo en serie | `1/G = 1/G_contacto + 1/G_esparcimiento` | — | [4, cap. 15, ec. 15.9, p. 548] |
| Celdas de un panel subdividido | `G = k t w / L` | — | [4, cap. 15, ec. 15.7, p. 546] |
| Junta entre paneles | En serie: conducción del centro de cada panel al borde + junta | Junta: un tornillo 10-32 cada 0,1 m, 0,527 W/K por tornillo (superficies grandes y delgadas) | [4, cap. 8, Tabla 8.4, p. 265]; el paso de 0,1 m es *(opinión, sin fuente)* |
| Aislador (control propio, propulsión) | `G = 1/R` | R = 200 K/W (rango 50–400) | [4, cap. 8, pp. 310–312] |
| Heat pipe | Nodo de vapor; `G_e = h_e L_e`, `G_c = h_c L_c` | `h_e` = 60 W/(m·K), `h_c` = 85 W/(m·K) (los mínimos de dos catálogos) | [8, Tabla 9-6, p. 92], [8, §9.4.1, p. 112]; patrón: [3, A.2.3] |
| Correa | `1/G = Σ Lᵢ/(kᵢ Aᵢ)` (terminales y tramo flexible) | Solo del usuario | [12, ec. x.1–x.2] |
| MLI (panel → capa externa) | Radiativo: `σ ε* A (T₁⁴ − T₂⁴)` | ε* de la arquitectura (0,015–0,030) | [3, A.1.3 b], [4, cap. 5, p. 165] |
| MLI de un equipo o tanque chico | Ídem | ε* = 0,05–0,30 | [4, cap. 5, p. 165] |

**Huella del equipo:** Equipos no tiene dimensiones. Mientras no las tenga (abierto 1), `discretization` estima la huella como la cara de un cubo de la masa del equipo con una densidad de 1000 kg/m³ *(opinión, sin fuente)* y avisa en cada equipo que usa la estimación.

**Incertidumbres de prediseño** que se guardan por clase [3, Tabla 6-1]:

| Clase | Incertidumbre |
|---|---|
| MLI (radiativa y conductiva) | ±50 % (+100 / −50 % en MLI muy compleja) |
| Radiativos externos | ±20 % |
| Radiativos internos | ±10 % |
| Lineales | ±50 % |
| Cargas externas | ±20 % |
| Cargas internas grandes / chicas | ±20 % / ±40 % |

### Valores típicos con fuente

| Interfaz | Valor | Condición | Fuente |
|---|---|---|---|
| Junta abulonada, por tornillo (TRW) | 0,21–3,51 W/K en superficies chicas y rígidas; 0,105–1,054 W/K en grandes y delgadas (de 2-56 a 1/4-28) | Aluminio en vacío | [4, cap. 8, Tabla 8.4, p. 265] |
| Junta abulonada, resistencia máxima (Lockheed Martin) | 12,6 a 0,09 K/W por tornillo, según tamaño y espesor de placa | Aluminio desnudo en vacío, acero torqueado | [4, cap. 8, Tablas 8.5–8.6, p. 266] |
| Perímetro abulonado, sin relleno | 20–130 W/(m²·K) según área por tornillo (16–58 cm²); < 115 en general; 90,8 a 26,6 cm²/tornillo | Placas delgadas (2,4 mm medio) | [4, cap. 8, p. 271, Fig. 8.21] *(rango digitalizado)* |
| Perímetro abulonado, sin relleno, placas gruesas | 284–398 W/(m²·K) | 7,94 mm, 16 tornillos 8-32, −34 a 71 °C | [4, cap. 8, Tabla 8.8, p. 273] |
| Con junta de grafito (Calgraph) | 506–705 W/(m²·K); mejora de 1,5–1,9 | Placas gruesas | [4, cap. 8, Tabla 8.13, p. 283] |
| Con RTV | 150–480 W/(m²·K) | Perímetro abulonado | [4, cap. 8, p. 283, Fig. 8.21] |
| Panel de honeycomb | Sin datos generales: no más que la curva sin relleno de la Fig. 8.21 | Pieles finas: resistencia de constricción alta | [4, cap. 8, p. 275] |
| Contacto Al-Al en vacío (probeta) | ~2 000 a ~20 000 W/(m²·K) entre ~0,5 y 8 MPa | Al 2024-T4, cilindros | [6, Fig. 5-8, p. 51] *(digitalizado)* |
| Correlación de Fletcher y Gyorog | Error medio 24 % | Metales en vacío | [6, §5.1.1.1, pp. 44–46] |
| Aisladores | 50–400 K/W en equipos de más de 20 kg; > 400 K/W (2 kg sobre varillas de fibra de vidrio); 218 K/W (seis tubos de G-10); > 300 K/W (8,4 kg sobre conos) | Varios | [4, cap. 8, pp. 311–312] |
| Materiales de aisladores | Ti-6Al-4V 6–8 W/(m·K); acero 304L 12–16; fibra de vidrio-epoxi < 1–2; PEEK 0,25 | — | [4, cap. 8, Tabla 8.18, p. 310] |
| Heat pipe, evaporador / condensador | > 120 / > 85 W/(m·K) (EHP, 0 g, > −20 °C); > 60 / > 100 W/(m·K) (Thales) | Aluminio-amoníaco, ranuras axiales | [8, Tabla 9-6, p. 92; §9.4.1, p. 112] |
| Correas | Ejemplos de 0,41 y ~0,5 W/K | Cu, Al, grafito pirolítico | [12] |
| Pieles y núcleo de honeycomb | Pieles 0,4–1,2 mm; el núcleo conduce «bastante bien» entre pieles, lo lateral va por las pieles | Aluminio | [4, cap. 8, p. 274], [4, cap. 6, p. 209] |
| Núcleo de honeycomb, conductividad efectiva (Swann y Pittman) | Mediciones en un núcleo de titanio difieren 17–61 % de la correlación estándar | 300–500 K | [15, resumen] |

### Órdenes de magnitud *(cálculo propio, ilustrativo)*

- **Contacto:** huella de 0,2 × 0,2 m: 3,6 W/K sin relleno y 15,6 W/K con RTV. Con 50 W, salto de 14 K y de 3,2 K.
- **Esparcimiento:** pieles de 2 × 0,5 mm de aluminio, de r = 0,1 m a 0,4 m: 0,76 W/K. Si los 50 W atravesaran todo el anillo, el salto sería ~66 K. Es una cota superior (en la realidad el panel va irradiando a medida que se aleja), pero muestra por qué, bajo los equipos de mucha disipación, se engrosan las pieles o se agregan doublers o heat pipes [4, cap. 6, p. 209].
- **Pieles entre celdas:** 1 m de ancho y 0,5 m entre centros: 0,33 W/K.
- **MLI:** linealizada a 20 °C, `4σT³ε*` = 0,11 W/(m²·K) con ε* = 0,02, frente a 4,6 W/(m²·K) de un radiador con ε = 0,8 al espacio.
- **Heat pipe:** 0,3 m de evaporador y 0,3 m de condensador: 11 W/K (Thales) a 15 W/K (EHP).
- **Aislador:** 200 K/W es 0,005 W/K: aislado frente a todo lo anterior.

### Alternativas

| Alternativa | A favor | En contra |
|---|---|---|
| Coeficiente por área × huella (recomendada) | Lo que hace la práctica con valores de diseño probados [4, cap. 16, p. 599]; un número con fuente | Necesita la huella |
| Correlaciones de contacto (Fletcher y Gyorog, Thomas y Probert) | Física | Piden presión, rugosidad, planitud: datos que no existen en prediseño; ±24 % aun con ellos [6, §5.1.1] |
| Conductancia por tornillo × número de tornillos | Tabla con fuente [4, Tabla 8.4] | Ignora la constricción en placas delgadas, que domina [4, cap. 8, p. 271] |
| G total del usuario por equipo | Exacto si viene del proveedor | Sin automatismo |

### Justificación y fuentes

- **Valores genéricos en prediseño:** cuando faltan los parámetros de los modelos de contacto, los ingenieros eligen valores aproximados que funcionaron en diseños anteriores [4, cap. 16, p. 599]. El contacto es difícil de caracterizar y poco reproducible aun en ensayo [2, diap. 117].
- **La constricción manda en placas delgadas:** en un perímetro abulonado, los coeficientes sin relleno son chicos (< 115 W/(m²·K)) por la resistencia de las placas entre tornillos, no por el contacto en el tornillo [4, cap. 8, p. 271]. En honeycomb, las pieles finas aumentan la constricción; sin datos, no usar valores mayores que la curva sin relleno [4, cap. 8, p. 275]. Para pieles finas, se recomienda RTV y la curva superior [4, cap. 8, p. 284]. Por eso el default con relleno: es lo recomendado para los paneles de un satélite mediano *(opinión sobre la elección)*.
- **Conservador para qué:** una conductancia baja calienta al equipo en el caso caliente; una alta lo enfría en el frío. No hay un único lado conservador: se resuelve con la incertidumbre de ±50 % en `sensitivity` [3, Tabla 6-2: contacto por similitud ±50 %, con ensayo ±25 %].
- **Esparcimiento:** ECSS sugiere conductores de esparcimiento de camino circular cuando la malla es gruesa [3, §4.5.2]; la fórmula del anillo es la del conductor entre nodos cilíndricos de Gilmore [4, cap. 15, Fig. 15.14]. Juntarlas es *(opinión)*.
- **Aisladores:** sobre 20 kg no hace falta aislación conductiva extrema porque dominan las fugas por MLI y cables [4, cap. 8, p. 312].
- **MLI:** tres formulaciones: lineal con k(T), radiativa con ε* (válida en un rango corto de T) y las dos en paralelo (rango amplio); k* y ε* son empíricos y salen de ensayos. La práctica de reemplazar la superficie por una emitancia equivalente se desaconseja salvo en cálculos a mano, porque no capta flujos externos ni reflexiones [3, A.1.3]. Hestia usa la radiativa con la capa externa como nodo aritmético: es la misma física que el balance ([balance-global.md](balance-global.md#modelo-de-un-nodo)), así el modelo de un nodo es un caso particular de la red.
- **Heat pipes:** conductancias de evaporador y condensador por metro de catálogo [8]; verificar después que el transporte integrado a lo largo del heat pipe no supere el `QL` del catálogo a la temperatura de operación [3, A.2.4]. Ese chequeo es de `solution` y usa el perfil y el margen que ya eligió el concepto.

## 4. Acoplamientos radiativos y factores de vista

### Recomendación

- **Dos cavidades,** externa e interna, como recomienda ECSS para evitar intercambios espurios entre el interior y el espacio [3, §4.7.6].
- **Cavidad externa, exacta y cerrada:** con la envolvente convexa y sin apéndices (lo que modela Entorno hoy), cada superficie externa solo ve el espacio (F = 1). Conductor radiativo al espacio: `R = ε A`. Los flujos absorbidos por cara los arma `load_cases` con los flujos incidentes de Entorno: no hace falta un trazador de rayos.
- **Cavidad interna, cerrada con aproximación de objetos chicos** *(opinión sobre el método)*:
  1. factores de vista entre las seis paredes internas con las fórmulas de rectángulos paralelos [5, ec. 4-36, p. 35] y perpendiculares con un borde común [5, §4.3.2.3, p. 37];
  2. cada equipo como un objeto chico de área `A_e` (la caja estimada menos la huella), que ve las paredes en proporción a su área, sin contar la pared donde está montado; reciprocidad para el camino inverso y las filas de las paredes reescaladas para que cada fila sume 1;
  3. **factores de Gebhart** con las emitancias, por álgebra lineal: `B = (I − F·(I − E))⁻¹ · F · E`, y conductor radiativo `R_ij = εᵢ Aᵢ B_ij`.
- **Precisión que se declara:** ±10 % en los internos y ±20 % en los externos [3, Tabla 6-1]; factores de vista simples ±10 %, complejos ±50 % [3, Tabla 6-2].
- **pyViewFactor** en `hestia_adapters`, detrás de un Protocol `ViewFactorProvider` de `hestia_core`, **cuando haya geometría** (apéndices, plataformas o posiciones de equipos). No en la primera versión.

### Qué puede hacer pyViewFactor y qué no

Versión 1.1.0 (mayo de 2026), licencia MIT, Python ≥ 3.10, depende de numpy, SciPy, numba (opcional) y pyvista [16].

| Puede | No puede |
|---|---|
| Factor de vista entre dos polígonos planos por integración de doble contorno (núcleo semianalítico SA-30), incluso caras que se tocan o son coplanares | Reflexiones: no calcula factores de Gebhart ni radiosidades (Hestia tiene que hacerlo) |
| Validado contra el analítico de rectángulos perpendiculares: error relativo < 10⁻⁵ en relaciones de aspecto de 0,25 a 4 | Obstrucción parcial: el chequeo es binario por par de caras: un rayo entre centroides (modo normal) o todos los rayos entre vértices (modo estricto). Un par parcialmente tapado vale todo o nada; hay que refinar la malla |
| Matriz N × N en paralelo con numba; visibilidad por orientación; obstrucción con BVH | Superficies especulares (OSR, SSM, Teflon plateado son especulares) |
| Importar geometría (`stl`, `vtk`, `obj`) vía pyvista | Flujos solares, de albedo e IR, órbita, sombras: nada del entorno espacial |
| — | Superficies curvas exactas (cilindros y tanques van facetados) |

Se diseñó para térmica urbana y de edificios [16]: sirve para la parte geométrica pura. Para un satélite con apéndices especulares, la práctica es el trazado de rayos Monte Carlo [3, guía 4-16], [4, cap. 15, pp. 594–595].

### Alternativas

| Método | Precisión | A favor | En contra |
|---|---|---|---|
| Fórmulas cerradas + álgebra de factores de vista | Exacta en geometrías simples; se usa para prediseño y para verificar los programas [4, cap. 15, p. 550] | Determinística, sin dependencias, testeable contra tablas | Solo geometrías del catálogo [5] |
| Integración de contorno (pyViewFactor) | Exacta sin obstrucción; binaria con obstrucción | Polígonos arbitrarios | Lo de la tabla de arriba |
| Integración adaptativa con obstrucción parcial (View3D, de NIST) | Controlada por un factor de convergencia | Obstrucción parcial | En C, sin binding Python; licencia no verificada |
| Monte Carlo (lo que usan ESARAD, THERMICA, Thermal Desktop) | Estadística: se verifica con suma por fila, reciprocidad y variando semillas y rayos [3, §5.5] | Especularidad, transparencia, sombras, flujos | Ruido; costo ~N² en superficies [3, §4.7.6]; no hay una biblioteca abierta madura encontrada |
| Emitancia efectiva de dos superficies (Hottel) | Ignora reflexiones secundarias [4, cap. 15, ec. 15.15, p. 551] | Cálculo a mano | No sirve para una cavidad con muchas superficies |

### Justificación y fuentes

- **Qué calcula el modelo geométrico:** acoplamientos radiativos y factores de vista, y los flujos ambientales [2, diap. 112], [1, §3.2.1.8]. Granularidad: «tan detallado como haga falta, tan simple como se pueda» [2, diap. 112].
- **Gris-difuso:** el supuesto de los códigos clásicos es temperatura y flujo uniformes en cada superficie, propiedades independientes de la longitud de onda y emisión y reflexión difusas; con eso, los factores de vista y el método de Gebhart dan los factores de intercambio [4, cap. 15, pp. 592–593]. Todos los códigos usan la aproximación semigris en dos bandas (solar e IR) [4, cap. 15, p. 595], [3, §4.7.5]. Adentro del satélite solo importa el IR [3, §4.7.6].
- **Pintura negra:** la mayoría de las superficies internas se pintan de negro para aumentar la emitancia y el intercambio radiativo entre equipos [4, cap. 4, pp. 139, 141]; las cajas electrónicas también [4, cap. 3, p. 71]. Por eso el intercambio interno es fuerte y la aproximación de objetos chicos alcanza en prediseño *(opinión)*.
- **Arneses y rugosidad:** si no se modelan, pueden justificarse emitancias efectivas más altas en cavidades internas [3, §4.7.3].
- **Factores de vista de prueba** *(cálculo propio con [5, ec. 4-36 y §4.3.2.3])*: en un cubo, cara opuesta 0,1998 y cada adyacente 0,2000; en una caja de 1,2 × 1,2 × 1,5 m, desde una cara de 1,2 × 1,2 la opuesta 0,1464 y cada adyacente 0,2134. Las dos filas suman 1, como exige la regla de la cavidad [5, ec. 4-6, p. 13]: son tests directos.
- **Gebhart:** Gilmore lo nombra como el método para pasar de factores de vista a factores de intercambio [4, cap. 15, p. 593]; la forma matricial es la estándar y la escribí yo: hay que verificarla (supuesto 4).

## 5. Propiedades ópticas por nodo

### Recomendación

- **Externas, de la arquitectura:** cada superficie externa de la red viene de una zona de `TcsArchitecture.surfaces`:
  - zona de radiador → superficie del nodo del panel (o del radiador montado) con α BOL, α EOL y ε del recubrimiento;
  - zona de MLI → superficie del nodo aritmético de la capa externa, con α BOL, α EOL y ε de la capa; ε* (mínimo y máximo) en el conductor panel → capa.
- **Internas:** pintura negra en paneles, plataforma y equipos, ε = 0,89 (Chemglaze Z306) [4, cap. 4, Tabla 4.1, p. 144]; override por equipo (p. ej. un equipo con acabado de baja ε para desacoplarlo) y por pared.
- **La red guarda BOL y EOL; no elige.** `load_cases` toma EOL para los calientes y BOL para los fríos, como el balance [3, guía 4-15], [2, diap. 114]. La ε se toma constante (la degradación sube α con poco efecto sobre ε: [balance-global.md](balance-global.md#3-propiedades-ópticas)).
- **Louvers:** la superficie del radiador guarda ε abierto y cerrado y sus temperaturas (las del concepto); `solution` resuelve ε(T). VCHP y desplegables quedan fuera de la primera versión, como en el concepto.

### Justificación y fuentes

- ECSS pide elegir las propiedades según el caso (BOL o EOL) y justificarlas con el ambiente de la misión; recomienda THERME como referencia de envejecimiento [3, §4.7.3], que es la fuente de los EOL de LEO del balance.
- La pintura negra y las superficies de α alta en general casi no se degradan en el espacio; si cambian, α baja unos puntos por blanqueo UV [4, cap. 4, p. 154]. Adentro no hay UV: BOL = EOL *(opinión)*.
- Mantener las ópticas como datos de superficie (no mezcladas en un conductor) permite que `load_cases` cambie BOL/EOL y el extremo de ε* sin rehacer la red *(opinión)*.

## 6. Verificación del modelo

### Recomendación

`couplings` corre estos chequeos al terminar y los devuelve en el resultado. Los marcados **error** dejan la celda `failed`; los demás son avisos *(la división es opinión)*.

| Chequeo | Qué verifica | Nivel | Fuente |
|---|---|---|---|
| Nodos aislados | Nodo sin conductores | Error | [3, guía 5-1] |
| Grupos aislados y conexión al espacio | Todo nodo tiene un camino de conductores hasta un nodo de borde; si no, el estacionario no está definido | Error | [3, guía 5-2]; [14, §3.2, p. 24] |
| Conductores nulos o negativos | G ≤ 0 | Error | [3, guía 5-4] |
| Capacidades nulas o negativas | Difusivo con C ≤ 0 | Error | [3, guía 5-5] |
| Conductores paralelos del mismo tipo | Dos lineales (o dos radiativos) entre el mismo par | Aviso (se suman) | [3, guía 5-3] |
| Dispersión de conductancias | max/min > 1000 | Aviso para `solution` | [3, §4.5.2] |
| Factores de vista | Cada fila de la cavidad interna suma 1; reciprocidad `Aᵢ Fᵢⱼ = Aⱼ Fⱼᵢ` | Error si falla más allá de una tolerancia | [5, ec. 4-6], [3, guía 5-13] |
| Cavidad interna sin flujos externos | Ningún nodo interno tiene superficie externa ni conductor radiativo al espacio | Error | [3, §4.7.6] |
| Masa | Σ masa de los nodos = masa de Misión; fracción de estructura en rango | Error / aviso | [3, §5.2]; [11] |
| Áreas | Σ áreas externas = área de la envolvente; radiadores y MLI = los de la arquitectura | Error | *(opinión)* |
| Fuentes | Cada equipo tiene nodo; cada zona de heaters tiene nodos con pesos que suman 1 | Error | *(opinión)* |
| Panel isotermo | Parámetro de aleta ξ por panel | Aviso | [4, cap. 6, ec. 6.7] |
| Estimaciones sin fuente | Huellas estimadas, juntas por default | Aviso | — |

**Contra el balance de la fase 0** (en `solution`, porque necesita casos):

- **Prueba de colapso** *(opinión; es el test de regresión más fuerte que tiene la red)*: con los conductores lineales y los radiativos internos multiplicados por un factor grande (p. ej. 10⁶; los de la MLI y los externos no cambian), las mismas cargas y las mismas ópticas, la temperatura de la red tiende a la del modelo de un nodo del balance. Como la red usa la misma física de la capa externa de la MLI que el balance, el límite tiene que coincidir con la tolerancia del solver.
- **Comparación en cada caso dimensionante:** temperatura media de la red ponderada por capacidad y su dispersión frente a la del balance; potencia de heaters y calor rechazado. La diferencia es el gradiente que el balance no veía (el `radiator_gradient` abierto en [datos-entorno-y-balance.md](datos-entorno-y-balance.md#42-gradiente-entre-equipos-y-radiador)). Como referencia de magnitudes aceptables pueden servir los criterios de ECSS para un modelo reducido frente al detallado: TRP con promedio < 2 K y desvío individual < 3 K, flujo total del satélite < 10 %, potencia de heaters < 10 % [3, §7.3.4] *(usarlos acá es opinión: no fueron hechos para comparar con un modelo de un nodo)*.
- **Balance de energía** de cada solución: Σ entradas = Σ salidas (SINDA usa típicamente 1 % del sistema y 0,5 % por nodo [4, cap. 15, p. 585]). Es criterio de `solution` (tema 3).
- **Sensibilidad a la discretización** (opcional): repetir con paneles 2 × 2 y verificar que las salidas clave cambian 5 a 10 veces menos que la incertidumbre [3, §4.5.2].

### Justificación y fuentes

- **Topología:** muchos problemas de los modelos térmicos vienen de una topología mal definida; ECSS pide como mínimo identificar y justificar nodos y grupos aislados, conductores paralelos, nulos o negativos y capacidades nulas o negativas [3, §5.2].
- **Conectividad:** la matriz del sistema linealizado es irreducible si el grafo de la red es conexo; un modelo que se parte en dos redes desconectadas equivale a dos satélites separados [14, §3.2, p. 24]. Si una parte conexa no llega a ningún borde, no tiene por dónde perder calor: el estacionario no existe *(derivación propia)*.
- **Revisión de flujos:** ECSS recomienda mirar el estacionario como red de flujos entre grupos, separando radiación y conducción, para detectar conductores erróneos [3, §5.3]. Hestia puede entregar ese cuadro por grupo en `solution`.
- **Un error grosero no lo detecta ningún análisis de incertidumbre:** solo la revisión, la comparación con proyectos anteriores o el ensayo [3, §6.3]. La comparación con el balance es la «comparación con algo anterior» que Hestia tiene a mano *(opinión)*.
- **ECSS-E-ST-31C** pide presentar los chequeos del TMM y del GMM [1, anexo B <6>] y, en la documentación, la precisión de los acoplamientos radiativos y los criterios de convergencia [1, anexo B <8>].

## 7. Qué entrega a `load_cases` y `solution`

### Recomendación

- **`discretization`** entrega la red **sin conductores**: nodos con capacidad y masa, superficies con ópticas, montajes (qué equipo va sobre qué nodo y con qué huella), adyacencias de paneles, mapa de fuentes y los chequeos de masa. **`couplings`** agrega los conductores y entrega la red completa, `ThermalNetwork`. Así cada etapa tiene un resultado que se puede mirar y cuestionar por separado, como piden los anexos de ECSS (nodos por un lado, acoplamientos por otro [1, anexo B <5> c]) *(opinión sobre el corte)*.
- **`load_cases`** toma `ThermalNetwork`, Entorno y Equipos y arma cada caso: flujos absorbidos por superficie externa (incidente de Entorno × α o ε, con BOL/EOL y el extremo de ε* del caso), disipación por nodo (el modo de cada equipo, con margen de madurez en los calientes), heaters por zona y temperaturas de borde. **`solution`** resuelve.
- **Formato:** JSON versionado en el `.hestia`, como Entorno; con ~50 nodos y ~200 conductores es chico. Unidades SI; conductores radiativos como área de intercambio (m²): `Q = σ R (Tᵢ⁴ − Tⱼ⁴)`.

### `ThermalNetwork` v1

| Parte | Contenido |
|---|---|
| `nodes` | `id`, `number` (entero), `name`, `kind` (`diffusion` \| `arithmetic` \| `boundary`), `group` (`structure`, `mli`, `equipment`, `radiator`, `heat_pipe`, `boundary`, `user`), `origin` (cara, `item_id`, `radiator_id`, `transport_id`, parámetro), `mass` (kg, desglosada por origen), `capacity` (J/K), `capacity_uncertainty`, `boundary_temperature` (K, solo bordes), `trp_of` (`item_id` si es el TRP de un equipo) |
| `surfaces` | `id`, `node_id`, `cavity` (`external` \| `internal`), `face` (externas), `area` (m²), `absorptance_bol`, `absorptance_eol`, `emittance`, `role` (`radiator` \| `mli_outer` \| `wall` \| `equipment`), control (louvers: ε abierto y cerrado y temperaturas) |
| `linear_conductors` | `id`, `from`, `to`, `conductance` (W/K), `class` (`contact`, `spreading`, `in_plane`, `panel_joint`, `isolator`, `heat_pipe`, `strap`, `user`), `inputs` (huella, h, k, t, R… con su fuente), `uncertainty` (fracción) |
| `radiative_conductors` | `id`, `from`, `to`, `exchange_area` (m²), `class` (`external`, `internal`, `mli`), `uncertainty`; los de MLI con `effective_emittance_min/max` para que `load_cases` elija el extremo |
| `sources` | Mapa de lo que `load_cases` necesita: `item_id` → `node_id`; zona de heaters (`htz_`) → nodos con pesos; superficie externa → cara de Entorno |
| `heat_transport` | Por heat pipe: nodo de vapor, nodos de evaporador y condensador, longitud, `QL` máximo del perfil y margen (del concepto) para el chequeo de capacidad en `solution` |
| `checks` | Resultado de cada chequeo de la sección 6 |
| `warnings` | Código, mensaje y referencia |
| `provenance` | Celdas y cambios del contexto, parámetros, proveedor y versión ([ADR 0021](../adr/0021-etapas-de-calculo.md)) |

### Justificación y fuentes

- Es la estructura de un TMM: nodos con capacidad, área y disipación, conductores conductivos, radiativos y convectivos, y fuentes [1, anexo B <5> c], [4, cap. 15, pp. 539–552]. Los flujos ambientales por superficie y por caso son entrada aparte, como los calcula un GMM en un número de posiciones orbitales [1, anexo B <4> d y <8>], [3, §4.5.5].
- Los modelos se entregan con casos de prueba y resultados de referencia [1, anexo A <8>], [3, guías 7-2 y 7-3]: en Hestia, los tests de `hestia_core` con casos de referencia (tema 3) cumplen ese papel.
- **Exportación:** ECSS sugiere ESARAD o THERMICA para el GMM y ESATAN para el TMM [1, anexo A <7>]. Hestia termina en Siemens NX; una exportación de la red (o de su geometría) a NX queda abierta (abierto 12).

## Propuesta de parámetros

Formulario de parámetros como en Entorno y el balance ([ADR 0021](../adr/0021-etapas-de-calculo.md)): borrador, validación en seco, Aplicar, defaults de biblioteca con procedencia. Un valor vacío con preset significa «el del preset»; se resuelve al actualizar y el resultado informa el valor y su fuente.

Lo que viene del contexto no se repite:
- **Misión:** envolvente (dimensiones y caras), masa.
- **Equipos:** equipos con `quantity`, `mass`, `location`, `subsystem`, límites y modos.
- **Concepto TCS:** `TcsArchitecture` de la alternativa seleccionada (`surfaces`, `radiators`, `insulation`, `heater_zones`, `heat_transport`, `own_control_items`, `budgets`, `assumptions`).
- **Entorno y balance:** no los usa `discretization` (son de `load_cases` y `solution`), salvo el cp efectivo del balance como referencia de comparación.

### `discretization`

**1. Estructura (`structure`)**

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `face_subdivision` | `map[Face, {u: int, v: int}]` | — | 1 × 1 en todas | *(opinión)* |
| `split_radiator_zone` | `bool` | — | sí | *(opinión)*; patrón de MLI igual al de la superficie [3, A.1.2] |
| `panel_material` | `enum` (`aluminium_honeycomb` \| `custom`) | — | `aluminium_honeycomb` | *(opinión)* |
| `facesheet_thickness` | `float` | m | 0,0005 (cada piel; dos pieles) | Rango 0,4–1,2 mm [4, cap. 8, p. 274]; el valor es *(opinión)* |
| `facesheet_conductivity` | `float` | W/(m·K) | 167 | Al 6061-T6 [7, p. 104] |
| `structure_specific_heat` | `float` | J/(kg·K) | 963 | Al 6061 [7, p. 104] |
| `internal_platform` | `enum` (`auto` \| `none` \| `forced`) | — | `auto` (si hay equipos `internal`) | *(opinión)* |
| `internal_platform_area` | `float` | m² | vacío: la mayor sección de la envolvente | *(opinión)* |

**2. Masa (`mass`)**

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `propellant_mass` | `float` | kg | 0 (o `mass − dry_mass` si Misión la tiene; abierto 2) | — |
| `propellant_node` | `ref(items)` \| `ref(user_nodes)` | — | obligatorio si `propellant_mass` > 0 | — |
| `propellant_specific_heat` | `float` | J/(kg·K) | 3084 | Hidracina a 298 K ([T8](datos-entorno-y-balance.md#t8-calor-específico)) |
| `harness_fraction` | `float` | — | 0,05 de la masa seca | [10, R-M1-7] |
| `structure_split` | `enum` (`by_area`) \| `map[node, float]` | — | `by_area` | *(opinión)* |

**3. Equipos (`equipment`)**

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `groups` | `list[{id, name, items: list[ref(items)]}]` | — | vacía (un nodo por fila) | *(opinión)* |
| `mounting` | `map[ref(items), {host: node_ref, cell: int?}]` | — | el panel de su `location`; `internal` → plataforma | [4, cap. 3, p. 73] |
| `footprint_area` | `map[ref(items), float]` | m² | vacío: cara de un cubo de densidad `box_density` | *(opinión, sin fuente; abierto 1)* |
| `box_density` | `float` | kg/m³ | 1000 | *(opinión, sin fuente)* |
| `specific_heat` | `map[enum Subsystem, float]` + override por equipo | J/(kg·K) | 900; `power` 1000 (baterías) | 900: *(opinión)*; 1000: [17] |
| `internal_emittance` | `float` + override por equipo | — | 0,89 | Chemglaze Z306 [4, cap. 4, Tabla 4.1] |

**4. Nodos del usuario (`user_nodes`)**: lista de `{id (usr_), name, kind, mass, specific_heat, boundary_temperature, mounting}`. Para tanques que no están en Equipos, apéndices como bordes (abierto 3) o una masa concentrada conocida.

**Validaciones:** subdivisiones ≥ 1; masas, áreas, espesores, conductividades y cp > 0; fracciones en [0, 1); referencias a equipos, nodos y celdas válidas (`invalid_reference`); un equipo en un solo grupo (`duplicate`); `propellant_node` obligatorio con propelente (`required`). **Al actualizar:** `missing` y `context_invalid` como en Entorno; `mass_overrun` si la masa sin asignar es negativa (la celda falla con el detalle por término).

### `couplings`

**1. Montaje de equipos (`mounting`)**

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `interface` | `enum` (`bare` \| `filled`) + override por equipo | — | `filled` | Recomendado para pieles finas y honeycomb [4, cap. 8, p. 284] |
| `contact_coefficient` | `map[interface, float]` | W/(m²·K) | `bare` 90; `filled` 390 | [4, cap. 8, p. 271]; [4, Fig. 8.21] *(digitalizado)* |
| `item_conductance` | `map[ref(items), float]` | W/K | vacío (calculada) | — |
| `spreading` | `bool` | — | sí | [3, §4.5.2]; fórmula [4, cap. 15, Fig. 15.14] |

**2. Paneles (`panels`)**

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `joint_bolt_pitch` | `float` | m | 0,1 | *(opinión, sin fuente)* |
| `joint_bolt_conductance` | `float` | W/K | 0,527 | 10-32, superficies grandes y delgadas [4, cap. 8, Tabla 8.4] |
| `joint_conductance` | `map[edge, float]` | W/K | vacío (calculada) | — |

**3. Aisladores y control propio (`isolation`)**

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `isolator_resistance` | `float` + override por equipo | K/W | 200 | Rango 50–400 [4, cap. 8, p. 312]; el valor es *(opinión)* |
| `item_mli_effective_emittance_min/max` | `float` | — | 0,05 / 0,30 | Mantas muy chicas [4, cap. 5, p. 165] |

El acoplamiento de un equipo con control propio que viene del concepto (`coupling_conductance`) se usa si está; si no, el aislador.

**4. Heat pipes (`heat_pipes`)**

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `evaporator_coefficient` | `float` | W/(m·K) | 60 | Mínimo de los catálogos [8, §9.4.1] |
| `condenser_coefficient` | `float` | W/(m·K) | 85 | Mínimo de los catálogos [8, Tabla 9-6] |
| `evaporator_length` | `map[transport, float]` | m | vacío: √huella de cada equipo servido | *(opinión)* |
| `condenser_length` | `map[transport, float]` | m | vacío: lado del radiador servido | *(opinión)* |

**5. Radiación (`radiation`)**

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `internal_method` | `enum` (`closed_form_box` \| `view_factor_provider`) | — | `closed_form_box` | *(opinión)*; fórmulas [5] |
| `wall_emittance` | `map[Face, float]` | — | 0,89 | [4, cap. 4, Tabla 4.1] |
| `space_temperature` | `float` | K | 0 (o 3) | *(opinión: abierto 9)* |
| `view_factor_tolerance` | `float` | — | 10⁻⁶ (cerradas); 10⁻³ (proveedor) | *(opinión)* |

**6. Usuario (`user_conductors`)**: lista de conductores lineales (`G` o correa con `k`, `A`, `L`) y radiativos (`exchange_area`) entre nodos cualesquiera, con `class: user` e incertidumbre.

**7. Incertidumbres (`uncertainty`)**: `map[class, float]` con los valores de [3, Tabla 6-1] como default (lineales 0,5; MLI 0,5; internos 0,1; externos 0,2).

**Validaciones:** coeficientes, conductancias, resistencias, longitudes y emitancias > 0 (ε y ε* ≤ 1); `item_mli_effective_emittance_min` ≤ `max` (`order`); referencias a nodos de la discretización (`invalid_reference`); `view_factor_provider` sin proveedor disponible → `not_allowed`. **Al actualizar:** los chequeos de error de la sección 6 dejan la celda `failed` con su código (`isolated_node`, `disconnected_group`, `non_positive_conductance`, `view_factor_sum`, `internal_external_leak`, `area_mismatch`).

## Propuesta de resultado

### `discretization`, en orden

1. Nodos por las reglas D1–D10, en orden estable (caras +X…−Z, después equipos en el orden de Equipos, después usuario).
2. Masas: equipos, TCS, propelente, arnés, estructura (resto) y su reparto; capacidades.
3. Superficies externas (por zona de cada cara) e internas (paredes, plataforma, equipos), con ópticas.
4. Montajes y huellas (con la marca «estimada» donde corresponde); adyacencias entre paneles y celdas.
5. Mapa de fuentes.
6. Chequeos de masa y áreas; avisos (huellas estimadas, fracción de estructura fuera de rango, parámetro de aleta).

| Parte | Contenido |
|---|---|
| `nodes`, `surfaces`, `sources` | Como en `ThermalNetwork` (sin conductores) |
| `mounts` | `item` → `host`, celda, huella (m²), si es estimada |
| `adjacency` | Pares de paneles o celdas con la longitud del borde común (m) |
| `mass_budget` | Misión, Σ equipos, TCS por componente, propelente, arnés, estructura; fracción de estructura sobre masa seca |
| `checks`, `warnings`, `provenance` | Como siempre |

### `couplings`, en orden

1. Conductores lineales por clase, con sus entradas y fuente.
2. Factores de vista de la cavidad interna, Gebhart y conductores radiativos internos; externos al espacio; MLI.
3. Heat pipes (nodo de vapor y conductores) y conductores del usuario.
4. Chequeos (sección 6).
5. Resumen por grupo: G total entre grupos, conductancia linealizada al espacio por cara (a una temperatura de referencia), para leer la red sin abrirla *(opinión)*.

Resultado: `ThermalNetwork` v1 completo, más `view_factors` (la matriz interna, para mostrarla y testearla), `summary`, `checks`, `warnings` y `provenance`.

## Lo que queda abierto

Cada punto con su recomendación; decidir antes de especificar.

1. **Dimensiones de los equipos.** Sin ellas, la huella (contacto) y el área radiante son estimaciones sin fuente. Recomendado: sumar `dimensions` opcional (largo × ancho × alto) a los equipos en Equipos; mientras tanto, la estimación por cubo con aviso por equipo.
2. **Masa seca y propelente.** El concepto ya propuso `dry_mass` opcional en Misión ([concepto-tcs.md](concepto-tcs.md#lo-que-queda-abierto), abierto 4). Recomendado: hacerlo y derivar el propelente como `mass − dry_mass`; el nodo del tanque lo elige el usuario.
3. **Apéndices (paneles solares, antenas).** Entorno no los modela, así que no tienen flujos ni factores de vista. Recomendado: primera versión sin apéndices, con la opción de un nodo de borde a temperatura fija y un conductor radiativo del usuario; modelarlos cuando Entorno sume apéndices, y ahí entra pyViewFactor (o Monte Carlo, por la especularidad).
4. **Juntas entre paneles.** No hay valor típico con fuente para la junta completa. Recomendado: el default por tornillos con aviso; pedir el dato al revisar satélites reales (tema 6).
5. **Cavidad interna con equipos.** La aproximación de objetos chicos es criterio propio. Recomendado: usarla en la primera versión y validarla (supuesto 3) contra pyViewFactor en una caja con cajas adentro en un test de desarrollo, como Skyfield para Entorno (oráculo, nunca de runtime).
6. **Posición de los equipos en la cara.** Equipos no la tiene. Recomendado: no modelarla; con una cara subdividida, el usuario elige la celda y, si no la elige, el equipo se reparte en partes iguales entre celdas, con aviso.
7. **Zonas de heaters «del cuerpo».** En el concepto, una zona puede calentar «el cuerpo» (un nodo). Recomendado: repartirla entre los paneles por área, con aviso, y que el usuario la reasigne.
8. **Corte entre las dos etapas.** Recomendado: el de este informe (nodos y masas en una, conductores en la otra). Alternativa: una sola etapa `thermal_network`; más simple, pero mezcla dos revisiones distintas y el catálogo ya tiene dos.
9. **Temperatura del espacio:** 0 K o 2,7 K. Recomendado: 0 K, como el balance; la diferencia es despreciable a temperatura ambiente *(opinión)*.
10. **Propiedades dependientes de la temperatura.** Recomendado: constantes en la primera versión, con aviso si la solución sale del rango de validez del dato [3, guía 4-10].
11. **Arnés como conductor.** Las fugas por cables pueden dominar en equipos aislados [4, cap. 8, p. 312]. Recomendado: no modelarlo en la primera versión, decirlo en los supuestos y dejarlo como conductor del usuario.
12. **Exportación a Siemens NX.** Recomendado: decidir el formato cuando se especifique la salida de la fase 1; guardar desde ahora los números enteros de nodo y los grupos.
13. **Subdivisión automática.** Recomendado: no subdividir solo; avisar con el parámetro de aleta. Si la experiencia muestra que el aviso se ignora, evaluar una regla automática con umbral explícito.
14. **Incertidumbres por clase en el resultado.** Recomendado: guardarlas ya (son datos de ECSS) aunque `sensitivity` llegue después.

## Supuestos de física para `physics-reviewer`

1. **Capa externa de MLI aritmética** con conductor radiativo σε*A al panel y emisión al espacio con su ε: la misma física que el balance. Verificar que el modelo colapsado reproduce el balance de un nodo (prueba de colapso) con la tolerancia del solver.
2. **Envolvente convexa:** cada superficie externa ve solo el espacio (F = 1) y ninguna otra cara. Vale sin apéndices.
3. **Objetos chicos en la cavidad interna:** cada equipo ve las paredes en proporción a su área (sin su pared de montaje); reciprocidad y reescalado de las filas de las paredes. Cuantificar el error contra un cálculo con geometría (pyViewFactor) en casos con equipos grandes frente a la pared.
4. **Gebhart matricial:** `B = (I − F(I − E))⁻¹ F E` y `R_ij = εᵢ Aᵢ B_ij`; verificar reciprocidad de R, que Σⱼ B_ij = 1 en una cavidad cerrada, y el caso de dos placas paralelas infinitas contra [4, cap. 15, ec. 15.11].
5. **Factores de vista cerrados:** ec. 4-36 y §4.3.2.3 de [5]; tests con el cubo (0,1998 / 0,2000) y la caja de 1,2 × 1,2 × 1,5 m (0,1464 / 0,2134), con suma 1.
6. **Contacto en serie con esparcimiento:** la fórmula del anillo con toda la potencia atravesándolo es una cota superior del salto; cuantificar contra una aleta radiante (Gilmore, ec. 6.2) en un caso típico.
7. **Panel de un nodo:** pieles en paralelo, núcleo sin resistencia transversal; el parámetro de aleta (ec. 6.7 de Gilmore) como indicador, fuera de su rango (ξ > 2) solo cualitativo.
8. **Heat pipe:** vapor isotermo; G = h·L en evaporador y condensador; sin límite de transporte en la red (el límite se chequea en `solution`).
9. **Masas:** resto a la estructura; capacidad por nodo `Σ m cp` con cp constante; arnés distribuido con la estructura; propelente en un nodo.
10. **Conectividad:** red conexa con al menos un borde ⇒ estacionario único y estable [14]; verificar el argumento para la red con conductores radiativos linealizados.
11. **Linealización para chequeos y resúmenes:** `4σT³` a una temperatura de referencia, solo para informar; la solución usa T⁴.
12. **Casos de referencia:** POAM (la red de [4, cap. 15, Tabla 15.7, p. 564], ~15 nodos con conductores lineales y radiativos listados) como test de `solution` (tema 3); el cubo y la caja para factores de vista.

## Fuentes

**Consultadas** (copia local en `docs/investigacion/fuentes/`)

1. ECSS-E-ST-31C. *Space engineering — Thermal control general requirements*. ECSS Secretariat, ESA-ESTEC, Noordwijk, 15 de noviembre de 2008. Usadas: §3.2.1.8 (GMM, p. 11), §3.2.1.38–3.2.1.39 (TMM y nodo térmico, p. 16), §4.5.2.1 c–f (p. 32), §4.9.4 (p. 40), anexo A (especificación del modelo matemático, DRD, pp. 44–46) y anexo B (descripción de los modelos, DRD, pp. 47–49). <https://ecss.nl/standard/ecss-e-st-31c-thermal-control/>. Local: `fuentes/ecss/ECSS-E-ST-31C.pdf`.
2. ESA. *ECSS-E-ST-31 Standardisation Training Course 2023*, Rev. 1. ESA Space Standardization, 2023. Diapositivas 112 (GMM), 113 (TMM y conductores), 114 (casos extremos), 117 (conductancia de contacto), 120 (incertidumbres por fase) y 122 (ecuación de balance por nodo). Local: `fuentes/ecss/ESA-ECSS-E-ST-31-training-2023-rev1.pdf`.
3. ECSS-E-HB-31-03A. *Space engineering — Thermal analysis handbook*. ECSS Secretariat, ESA-ESTEC, 15 de noviembre de 2016. Usadas: §4.4 (p. 20), §4.5.2–4.5.5 (pp. 21–23), §4.7.3 (p. 26), §4.7.5–4.7.6 (pp. 27–28), §5.2–5.3 (pp. 32–34), §5.5 (p. 35), §6.1 (pp. 36–37), §6.3 (pp. 39–40), Tablas 6-1 y 6-2 (pp. 40–41), §7.3 (pp. 53–57) y anexo A.1–A.4 (MLI, heat pipes, materiales en capas, unidades electrónicas, pp. 58–65). <https://ecss.nl/wp-content/uploads/2016/11/ECSS-E-HB-31-03A15November2016.pdf>. Local: `fuentes/ecss/ECSS-E-HB-31-03A-2016.pdf`.
4. Gilmore, D. G. (ed.). *Spacecraft Thermal Control Handbook, Volume I: Fundamental Technologies*, 2.ª ed. The Aerospace Press / AIAA, El Segundo, 2002. Capítulos usados:
   - cap. 3, Gilmore et al., «Thermal Design Examples», pp. 71 y 73;
   - cap. 4, Gilmore, Stuckey y Fong, «Thermal Surface Finishes», pp. 139, 141, 154 y Tabla 4.1 (p. 144);
   - cap. 5, Donabedian et al., «Insulation», p. 165;
   - cap. 6, Gilmore, «Radiators», p. 209 y pp. 218–220 (ec. 6.2–6.8, Fig. 6.12);
   - cap. 8, Gluck y Baturkin, «Mountings and Interfaces», pp. 247–248, 265–266 (Tablas 8.4–8.6), 271–275 (Figs. 8.21–8.25, Tabla 8.8), 283–284 (Tabla 8.13) y 310–312 (Tabla 8.18, Figs. 8.60–8.62);
   - cap. 15, Gilmore y Collins, «Thermal Design Analysis», pp. 525, 535, 539–552 (fundamentos de modelado, ec. 15.3–15.15, Figs. 15.13–15.17), 564 (POAM, Tabla 15.7), 585 y 592–595;
   - cap. 16, Mantelli y Yovanovich, «Thermal Contact Resistance», p. 599.

   Local: `fuentes/gilmore-2ed/capitulos/`.
5. ECSS-E-HB-31-01 Part 1A. *Space engineering — Thermal design handbook — Part 1: View factors*. ECSS Secretariat, 5 de diciembre de 2011. §4.1 (ec. 4-1 a 4-6, pp. 12–13), §4.3.2.1 (ec. 4-36, p. 35), §4.3.2.3 (pp. 37–38) y §5.1 (superficies especulares, p. 103). Local: `fuentes/ecss-e-hb-31-01/partes/part01.pdf`.
6. ECSS-E-HB-31-01 Part 4A. *Space engineering — Thermal design handbook — Part 4: Conductive heat transfer*. ECSS Secretariat, 5 de diciembre de 2011. Cláusula 5: §5.1 (pp. 43–50, correlaciones de Fletcher y Gyorog y de Thomas y Probert), Fig. 5-8 (p. 51) y §5.3.6.1 (p. 146). Local: `fuentes/ecss-e-hb-31-01/partes/part04.pdf`.
7. ECSS-E-HB-31-01 Part 5A. *Space engineering — Thermal design handbook — Part 5: Structural materials: metallic and composite*. ECSS Secretariat, 5 de diciembre de 2011. Al-4,3Cu-1,5Mg-0,6Mn (2024, densidad, p. 85), Al-1Mg-0,6Si (6061: densidad, cp y conductividad, p. 104), Ti-6Al-4V (densidad, p. 151). Local: `fuentes/ecss-e-hb-31-01/partes/part05.pdf`.
8. ECSS-E-HB-31-01 Part 8A. *Space engineering — Thermal design handbook — Part 8: Heat pipes*. ECSS Secretariat, 5 de diciembre de 2011. Tabla 9-6 (EHP, p. 92), §9.4.1 y Tabla 9-10 (Thales Alenia Space, pp. 111–112). Local: `fuentes/ecss-e-hb-31-01/partes/part08.pdf`.
9. ECSS-E-HB-31-01 Part 15A. *Space engineering — Thermal design handbook — Part 15: Existing satellites*. ECSS Secretariat, 5 de diciembre de 2011. §4.8 (IUE, p. 25), §8.8.1–8.8.4 (SPOT 1, pp. 92–95), §9.6 (Olympus-1, pp. 106–107). Local: `fuentes/ecss-e-hb-31-01/partes/part15.pdf`.
10. ESA SRE-PA y D-TEC. *Margin philosophy for science assessment studies*, SRE-PA/2011.097, Issue 1 Rev. 3. ESA-ESTEC, 15 de junio de 2012. R-M1-7 (arnés ≥ 5 % de la masa seca, p. 4). Local: `fuentes/esa/ESA-SRE-PA-2011-097-margin-philosophy-1.3.pdf`.
11. Zandbergen, B. T. C. *AE1222-II: Aerospace Design & Systems Engineering Elements I — Part: Spacecraft (bus) design and sizing*, versión 2013/2014. TU Delft. Apéndice D, Tablas 1–3 (pp. 184–185), con datos de Wertz y Larson (*SMAD*), Fortescue et al. (*SSE*) y MediaGlobe. Local: `fuentes/otros/zandbergen-reader-1222-spacecraft-design-2013.pdf`.
12. Bolton, D. A., Rodriguez-Ruiz, J. E. y Bae, D. «Thermal Straps», borrador de capítulo, NASA, 2024 (NTRS 20240006644). Ec. x.1–x.2 y sección de resistencia de interfaz. Local: `fuentes/nasa/NASA-STCH-thermal-straps-2024.pdf`.
13. ESA. *ATHENA CDF Study Report*, CDF-150(A), noviembre de 2014. §11.2 (control térmico del módulo de servicio, pp. 181–182). <https://www.cosmos.esa.int/documents/400752/400864/ATHENA+-+CDF+Study+Report.pdf>. Local: `fuentes/esa/ESA-CDF-150A-ATHENA-2014.pdf`.
14. Gaite, J. «Nonlinear analysis of spacecraft thermal models». arXiv:1010.4707, Universidad Politécnica de Madrid, 2010. §3.2 (irreducibilidad de la red, p. 24) y §4 (condensación de nodos, p. 27). <https://arxiv.org/abs/1010.4707>. Local: `fuentes/otros/arxiv-1010.4707-gaite-nonlinear-spacecraft-thermal-models.pdf`.
15. Daryabeigi, K. «Heat Transfer in Adhesively Bonded Honeycomb Core Panels». AIAA 2001-2825, 35th AIAA Thermophysics Conference, Anaheim, junio de 2001. Resumen y modelo de Swann y Pittman (pp. 1–2). NTRS 20010066875. Local: `fuentes/nasa/AIAA-2001-2825-daryabeigi-honeycomb.pdf`.
16. Bogdan, M., Walther, E. et al. (AREP). *pyViewFactor*, versión 1.1.0 (25 de mayo de 2026), licencia MIT. Descripción en PyPI (<https://pypi.org/project/pyviewfactor/>), documentación «Implementation / Visibility» y «Examples / Analytical validation» (<https://arep-dev.gitlab.io/pyViewFactor/>), consultadas el 2026-10-06. Artículo de referencia: Bogdan, Walther, Alecian y Chapon, «Calcul des facteurs de forme entre polygones», IBPSA France 2022 (no leído).
17. Maleki, H., Al Hallaj, S., Selman, J. R., Dinwiddie, R. B. y Wang, H. «Thermal properties of lithium-ion battery and components». *Journal of the Electrochemical Society*, 146 (3), 1999. doi:10.1149/1.1391704. **Solo el resumen** (OSTI 345380, <https://www.osti.gov/biblio/345380>).

Datos tomados de los informes anteriores (con sus fuentes): cp de la hidracina y de compuestos ([datos-entorno-y-balance.md](datos-entorno-y-balance.md#t8-calor-específico)); ε* y ópticas de recubrimientos ([balance-global.md](balance-global.md#valores-típicos)); `TcsArchitecture` ([concepto-tcs.md](concepto-tcs.md#6-qué-entrega-a-la-fase-1)).

Revisadas sin tomar valores: el curso de ESA de 2017 (`ECSS-Training-L2-E31-Thermal-2017-10.pdf`, mismo contenido que [2] en este tema); ECSS-E-HB-31-01 parte 2 (cavidades).

**No consultadas** (pendientes de verificar; no respaldan ningún valor de este informe)

- Gilmore, *Spacecraft Thermal Control Handbook*, vol. I, 2.ª ed., apéndice B (conductancia de núcleos de honeycomb, citado en [4, cap. 6, p. 209]) y apéndice C (rellenos de interfaz, citado en [4, cap. 8, p. 275]). La copia online no tiene los apéndices.
- Swann, R. T. y Pittman, C. M. *Analysis of effective thermal conductivities of honeycomb-core and corrugated-core sandwich panels*. NASA TN D-714, 1961. Citada por [15].
- Siegel, R. y Howell, J. R. *Thermal Radiation Heat Transfer*. Citada por [4, cap. 15] y [5] para el método de Gebhart y los factores de vista.
- Walton, G. N. *Calculation of obstructed view factors by adaptive integration*. NISTIR 6925, NIST, 2002 (View3D). Identificada; licencia del programa no verificada.
- Pérez-Grande, I. et al., modelo de dos nodos de un satélite chico, citado por [14].
- ECSS-E-ST-31-04, intercambio de modelos térmicos (STEP-TAS): relevante para la exportación a NX (abierto 12).
- Herramienta de reducción de modelos de ESA (TMRT), citada por [3, §7.3.5.3].
- Karam, R. D. *Satellite Thermal Control for Systems Engineers*. AIAA, 1998. Sigue sin acceso.
