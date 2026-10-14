# Concepto TCS (`tcs_concept`): cómo se elige la arquitectura en la fase 0

**Fecha:** 2026-10-05
**Estado:** investigación para revisar antes de especificar la etapa. No es especificación ni ADR; nada de esto está implementado. Parte de lo propuesto en [balance-global.md](balance-global.md), que tampoco está implementado.

## Alcance y cómo leer

- Una sección por pregunta: primero la recomendación, después la práctica, las alternativas y las fuentes. Al final, la propuesta de parámetros y de resultado (coherente con el [ADR 0021](../adr/0021-etapas-de-calculo.md) y con las salidas del balance), lo que queda abierto y los supuestos para `physics-reviewer`.
- **Respaldo y opinión:** lo respaldado lleva su referencia entre corchetes, `[n, lugar]`, numerada como en [Fuentes](#fuentes). El criterio propio va marcado *(opinión)*. Los números de los ejemplos son cálculos propios y lo dicen.
- **Qué se leyó:** ECSS-E-ST-31C [1] y el curso de ESA sobre esa norma [2]; Gilmore 2.ª ed., caps. 3, 5, 6, 7, 8, 9, 11, 14 y 15 [3]; ECSS-E-HB-31-01, partes 8 (heat pipes) [4], 12 (louvers) [5], 15 (satélites existentes) [6] y 11 (calentamiento eléctrico) [7]; ECSS-E-ST-10C Rev.1, anexo L (informe de trade-off) [8]; el manual de ingeniería de sistemas de NASA, §6.8 [9]; la filosofía de márgenes de ESA para estudios de evaluación [10]; el resumen de las reglas GOLD de GSFC [11]; el apunte de diseño de TU Delft con las tablas de masa por subsistema de SMAD y SSE [12]; el capítulo térmico del estado del arte de satélites chicos de NASA [13]; un borrador de capítulo de NASA sobre correas térmicas [14] y una hoja de catálogo de termostatos [15]. Las partes 7, 9 y 10 del handbook se revisaron sin tomar valores. **No se consultaron** Karam ni SMAD en forma directa (SMAD llega a través de [12]): ver [Fuentes](#fuentes).
- **Copia local:** las fuentes bajadas quedan en `docs/investigacion/fuentes/` (ignorada por git), con el texto extraído al lado de cada PDF.
- «Práctica de la industria» es la documentada en normas, manuales y ejemplos publicados. Los procedimientos internos de cada empresa varían y no están al alcance.

## Resumen

1. **Qué se hace en la fase 0:** se definen y analizan *paramétricamente* una o pocas alternativas de control térmico, se evalúa la madurez de las tecnologías y se elige una línea base con su masa, su potencia y sus problemas abiertos [3, cap. 15, pp. 523–525]. Para la mayoría de los equipos alcanzan las técnicas estándar (recubrimientos, MLI, heaters chicos); el esfuerzo va a lo que tiene impacto de sistema: radiadores grandes o desplegables, heat pipes, baterías, equipos de alta densidad [3, cap. 15, pp. 523–524].
2. **La arquitectura base es casi siempre la misma** en un satélite mediano de tres ejes: MLI en el cuerpo, radiadores de α baja y ε alta, y heaters para los modos de baja disipación [3, cap. 3, pp. 72–73], [2, diap. 105]. Las alternativas del trade-off son variaciones de esa base: dónde y cómo va el radiador, si tiene control variable, qué equipos tienen control propio y cómo se lleva el calor de una cara a otra.
3. **Reglas de decisión:** casi ninguna tiene umbral publicado; lo que sí está publicado es el *mecanismo* (cuándo conviene cada tecnología). Hestia no necesita umbrales mágicos: genera las alternativas que las reglas habilitan, dimensiona cada una con la misma física del balance y compara números.
4. **Trade-off determinístico:** alternativas generadas por reglas más las del usuario; todas dimensionadas con `hestia_core` sobre todos los casos del balance; criterios calculados (masa, potencia, área, margen, cantidad de elementos activos) y criterios juzgados que entran como datos (TRL y puntajes con definición operativa); pesos del usuario. Resultado: matriz de decisión, ranking, frente de Pareto y sensibilidad a los pesos, como pide ECSS [8, anexo L]. Sin pesos, una regla lexicográfica por defecto: lo más simple que sea factible, después la menor masa y después la menor potencia.
5. **Masa y potencia:** estimación por componente con márgenes de madurez de ESA (5/10/20 %) [10]; el porcentaje paramétrico (4,3 % ± 3,1 % de la masa seca en 17 satélites [12]) solo como chequeo de rango. Heaters por modo operativo, con margen, contra el presupuesto de Misión.
6. **Iteración sin ciclos:** `tcs_concept` redimensiona por su cuenta cada alternativa con la misma función de `hestia_core` que el balance. Nada del concepto obliga a recalcular el balance; solo un cambio del *problema* (requisitos, equipos, órbita) va aguas arriba. Conviene corregir «Itera a 0.4» en el catálogo.
7. **Entrega a la fase 1:** un artefacto de arquitectura versionado (superficies por cara, radiadores, MLI, zonas de heaters, transporte de calor, equipos con control propio, presupuestos y supuestos), que `discretization` convierte en nodos.

## 1. Catálogo de tecnologías

### Recomendación

- **El catálogo es un dato versionado de `hestia_core`**, como los presets de recubrimientos del balance: cada parámetro con valor, rango y fuente. El resultado informa qué valor usó y de dónde salió. El usuario puede reemplazar cualquier valor.
- **Cada tecnología declara tres cosas:** cómo entra en el modelo de un nodo (qué cambia en el balance), cómo se dimensiona y cuánto pesa.
- **Primera versión:** recubrimientos, MLI, radiadores (estructural, montado al cuerpo, desplegable), heaters (operación y supervivencia), louvers, transporte entre caras con heat pipes de conductancia constante (CCHP) y control propio de equipos. **Después:** VCHP, heat pipes de lazo (LHP), PCM, correas y doublers. Las tres últimas necesitan la huella y la potencia de cada equipo, que es información de la fase 1 *(opinión)*.

### Qué resuelve cada una y cómo entra en Hestia

| Tecnología | Qué resuelve | Cuándo se usa (respaldo) | Herencia | Modelo en la fase 0 de Hestia *(opinión)* |
|---|---|---|---|---|
| Recubrimientos | Fijan α/ε de radiadores y superficies expuestas | Siempre; radiadores con α < 0,2 y ε > 0,8 [3, cap. 6, p. 207] | Estándar [2, diap. 74], [13, Tabla 7-2] | Presets del balance (α BOL/EOL, ε) por superficie |
| MLI | Aísla el cuerpo del ambiente | Diseño radiativo: el de casi todos los satélites [2, diap. 105], [3, cap. 3, p. 72] | Estándar | ε* (rango) y capa externa en lo que no es radiador; masa por m² |
| Radiador estructural | Rechaza calor desde un panel del cuerpo | El más común y simple [3, cap. 6, p. 209] | Estándar | Área en una cara; masa al TCS ≈ 0 |
| Radiador montado al cuerpo | Radiador a otra temperatura o donde no hay panel útil | [3, cap. 6, p. 209] | Estándar | Área en una cara; masa por m² (sin dato publicado) |
| Radiador desplegable | Más área de la que ofrece el cuerpo | Cuando el bus no alcanza [3, cap. 6, p. 211] | Volado; mecanismo | Área faltante y masa; ver abierto 7 |
| Heaters | Mantienen el mínimo en frío, reponen equipos apagados, precalientan | Cuando las variaciones exceden lo que tolera un equipo [3, cap. 7, p. 223] | Estándar [13, Tabla 7-4] | Potencia por modo y zonas con set points |
| Termostato / controlador de estado sólido / computadora | Control de heaters | Trade clave de la fase 0 [3, cap. 15, Tabla 15.2] | Estándar | Tipo de control por zona (regla en la sección 2) |
| Louvers | Radiador de emitancia variable sin potencia | Disipación interna que varía mucho [3, cap. 9, p. 331] | Larga [3, Tabla 9.1]; mecanismo | ε efectiva abierto/cerrado en función de T |
| CCHP | Transportar, esparcir o isotermizar | Fuente y sumidero separados; equipos de alta densidad [3, cap. 14, p. 501], [3, cap. 6, p. 209] | Estándar; vida 15–25 años [4, Tablas 9-6, 9-9] | Transporte entre caras: W·m requeridos y masa por metro |
| VCHP | Radiador de área activa variable | Cargas que varían mucho o minimizar heaters en frío [3, cap. 6, p. 209] | Volado (ATV, 40 VCHP [4, Fig. 9-25]) | Fracción activa mínima (sin default con fuente) |
| LHP | Transporte a distancia, con flexibles, tolerante a inclinación | Layouts complejos, radiadores desplegables [3, cap. 14, pp. 502–503] | Volado [2, diap. 90] | Usuario |
| PCM | Absorber pulsos; dimensionar el radiador por el promedio | Ciclos de trabajo cortos [3, cap. 11, pp. 381–382] | Volado; costo y complejidad de desarrollo [3, cap. 11, p. 381] | Usuario, con el criterio de ciclo crítico |
| Correas térmicas | Unir dos piezas desacopladas mecánicamente | Distancias cortas, ~30 cm o menos [14] | Estándar [13, Tabla 7-2] | Fase 1 |
| Doublers | Esparcir el calor de un equipo de alta densidad | Potencia por área alta en la base del equipo [3, cap. 8, pp. 290–291] | Estándar | Fase 1 (necesita la huella) |
| Lazos bombeados | Grandes potencias | Tripulados; en no tripulados preocupa la bomba en misiones largas [3, cap. 6, p. 214] | Limitada en satélites | Fuera de alcance |

### Parámetros de dimensionamiento

| Tecnología | Parámetro | Valor típico | Fuente |
|---|---|---|---|
| MLI | Masa por área | 0,25–0,50 kg/m² para 12–22 capas, con cables de puesta a tierra; hasta 2,2 kg/m² con cuatro mantas apiladas (BepiColombo) | [2, diap. 77] |
| MLI | Masa de las capas | Mylar aluminizado 0,25 mil: 9,3 g/m² por capa; red de Dacron: 6,3 g/m²; Kapton aluminizado 1 mil: 36 g/m² | [3, cap. 5, Tablas 5.3–5.4, pp. 173–174] |
| MLI | ε* | Teoría con 12 capas: 0,004; valor correlacionado 0,01–0,03; 0,015–0,030 en áreas medias | [2, diap. 77], [3, cap. 5, p. 165] |
| Radiador | Rechazo neto | 100–350 W/m² | [3, cap. 6, p. 208] |
| Radiador estructural | Masa al TCS | ≈ 0: el panel se carga a estructura; las pieles engrosadas y los doublers sí van al TCS | [3, cap. 6, p. 209] |
| Panel con heat pipes | Masa por área | ≈ 5 kg/m² (heat pipes + acabados; supuesto del ejemplo de PCM) | [3, cap. 11, p. 382] |
| Radiador desplegable | Masa por área | Hasta ~12 kg/m² con estructura y despliegue | [3, cap. 6, p. 208] |
| Radiador desplegable | Ejemplo (Alpha) | 1250 W a 36 °C; panel de 1,27 × 3,18 m; 21,7–22,8 kg (LHP 9,5 kg); 55–58 W/kg | [3, Tabla 6.1, p. 214] |
| Heaters | Banda muerta de termostato | No menos de 4 °C (riesgo de *dithering*) | [3, cap. 7, p. 225] |
| Heaters | Termostato | 5,4 g; 2 A a 30 V (Sensata M2, MIL-PRF-24236/20) | [15] |
| Heaters | Controlador de estado sólido | < 30 g; 0–100 W; 30 mW en reposo; ±0,25 °C | [3, Tabla 7.1, p. 226] |
| Heaters | Set points de ejemplo | Supervivencia −18 °C; control 13 °C | [3, cap. 7, pp. 229–230] |
| Heaters | Potencia de un satélite real (SPOT 1, plataforma) | 120 W en supervivencia, 50 W en los demás modos; propulsión: ~100 W y ~30 W | [6, §8.7.1] |
| Heaters | Masa por W, masa de termistores | **Sin fuente** en lo consultado | — |
| Louvers | ε efectiva | Abierto 0,39–0,71; cerrado 0,08–0,115 | [3, Tabla 9.2, p. 336] |
| Louvers | Relación abierto/cerrado | ~6 veces el calor rechazado | [3, cap. 9, p. 331] |
| Louvers | Diferencial cerrado → abierto | 10–18 °C pasivo; ~1 °C con heater y controlador | [3, cap. 9, p. 331], [3, Tabla 9.1] |
| Louvers | Masa por área (sin parasol) | 3,2–11,6 kg/m² (≈ 4,5 Swales); ATS 5,6, Helios 4,7, Mariner 4–8,6 | [3, Tabla 9.1], [5, §7.1] |
| Louvers | Área por conjunto | 0,02–0,6 m² | [3, Tabla 9.1] |
| CCHP Al/NH₃ | Capacidad garantizada en 0 g a 20 °C (con 20 % de margen del fabricante) | Ø11: 62 W·m; Ø12,2: 140; Ø14: 125; Ø19: 320; Ø22: 740 (a 80 °C: 28–725) | [4, Tabla 9-10] |
| CCHP Al/NH₃ | Masa por metro | 339–668 g/m (Thales); 140–575 g/m (EHP, Iberespacio) | [4, Tablas 9-6, 9-9, 9-11] |
| CCHP Al/NH₃ | Flujo máximo | Evaporador 7 W/cm² (EHP), hasta 10 W/cm² (Thales); condensador 5 W/cm² | [4, Tablas 9-6, 9-10] |
| CCHP | Longitud | Hasta 4 m | [4, Tablas 9-6, 9-10] |
| Transporte bifásico | Margen | ≥ 30 % de capacidad | [11] |
| VCHP (acero, malla) | Capacidad, masa, control | > 100 W·m; 160 g/m; ±0,4 °C en modo activo | [4, Tabla 9-8] |
| LHP | Potencia | 20–100 W en aplicaciones chicas; > 500 W; 24 kW demostrados; fuente hasta 5 m sobre el sumidero | [3, cap. 14, pp. 502–503] |
| PCM | Calor latente (alcanos C11–C28) | 141–253 kJ/kg, fusión entre −25 y 62 °C (n-hexadecano 17 °C, 237 kJ/kg; n-octadecano 28 °C, 244 kJ/kg) | [3, cap. 11, pp. 377–378] |
| PCM | Almacenamiento neto del dispositivo | 35 W·h/kg con encapsulado de alto rendimiento (≈ 126 kJ/kg, ≈ 7,9 g/kJ) | [3, cap. 11, p. 382] |
| Correas | Conductancia | G = kA/L; k: Cu 401, Al 237, grafito pirolítico 1700 W/(m·K); ejemplos de 0,41 W/K y ~0,5 W/K | [14] |
| Recubrimientos | α, ε, degradación | Ver la tabla del balance | [balance-global.md](balance-global.md#valores-típicos) |
| Recubrimientos | Masa por área | **Sin fuente** en lo consultado | — |

### Justificación y fuentes

- **Fase 0 = paramétrico, no diseño puntual:** «el ingeniero tiende a saltar a un diseño puntual en lugar de hacer análisis paramétricos; en general no conviene», porque los datos de entrada cambian rápido; muchas corridas con un modelo chico valen más que un modelo grande [3, cap. 15, pp. 524–525]. Es exactamente lo que puede hacer Hestia con un nodo.
- **Masa de MLI por componentes** (cálculo propio, ilustrativo): 20 capas × (9,3 + 6,3) g/m² ≈ 0,31 kg/m², más una capa externa de Kapton de 1 mil (36 g/m²), dan ≈ 0,35 kg/m² sin cintas, velcro ni costuras. Cae dentro del rango de ESA [2, diap. 77].
- **Quién paga la masa del radiador:** el panel estructural va a estructura; las pieles más gruesas o los doublers que se agregan para esparcir el calor van al TCS [3, cap. 6, p. 209]. Por eso la masa del TCS depende de la arquitectura y no se puede calcular en el balance.
- **Doublers frente a heat pipes:** pasado un punto, engrosar pieles o agregar doublers pesa demasiado y se usan heat pipes; Gilmore muestra un trade de un satélite de comunicaciones donde los heat pipes logran la misma temperatura con menos masa [3, cap. 6, p. 209, Fig. 6.3]. El dimensionamiento del doubler es un problema de aleta con la huella del equipo [3, cap. 8, pp. 290–296]: fase 1.
- **Louvers al Sol:** se usan sobre todo donde se evita la iluminación solar directa; al Sol hacen falta parasoles o un diseño de alta temperatura [3, cap. 9, pp. 332–334], y las palas especulares atrapan rayos solares [3, cap. 9, p. 340]. Por eso Hestia no debería proponer louvers en una cara iluminada sin un dato de α efectiva *(opinión)*.
- **Modelo lineal de louvers:** ε efectiva constante por debajo de T cerrado, constante por encima de T abierto y lineal en el medio [3, cap. 9, ec. 9.3–9.5]. Entra en el balance de un nodo reemplazando ε del radiador por ε(T).
- **VCHP:** el rango de control lo fija el volumen del reservorio de gas y la temperatura nominal la masa de gas [4, §8.2.1]. Ninguna fuente consultada da una fracción activa mínima típica: sin ella, la VCHP no se puede dimensionar en un nodo sin datos del usuario.
- **PCM, criterio cerrado:** con un radiador de `m_rad` kg/m² que rechaza `q_rad` W/m² y un PCM que almacena `Q_PCM` W·h/kg, el PCM conviene si el ciclo de trabajo del pulso es menor que `β' = m_rad Q_PCM / (q_rad Δt_ciclo)` [3, cap. 11, p. 381]. Con 5 kg/m², 300 W/m², 35 W·h/kg y una órbita de 1,5 h da β' = 0,39 (pulsos de menos de 35 min), que es el ejemplo de [3, p. 382]: sirve de test.
- **Correas, masa por conductancia** (derivación propia de G = kA/L y m = ρAL): `m = ρ G L² / k`. Para G = 1 W/K y L = 0,2 m, el conductor pesa 0,89 kg en cobre, 0,46 kg en aluminio y 0,05 kg en grafito pirolítico (sin terminales). Explica por qué las correas sirven solo para distancias cortas [14].
- **Heat pipes en ensayo:** los de ranuras axiales son muy sensibles a la gravedad en tierra [3, cap. 14, p. 490] y se ensayan nivelados; los LHP toleran inclinación [3, cap. 14, p. 503]. Afecta la verificabilidad, uno de los criterios cualitativos.
- **TRL:** Gilmore recomienda evaluar la madurez de cada tecnología con la escala de nueve niveles de NASA [3, cap. 15, p. 524, Tabla 15.1]. No se encontró una tabla de TRL por tecnología para satélites medianos; la de NASA es para satélites chicos (pasivos 7–9, heaters 7–9, lazos bombeados 4–5) [13, Tablas 7-2 y 7-4]. El TRL entra como dato editable del catálogo *(opinión)*.

## 2. Reglas de decisión

### Recomendación

Las reglas son **generadores** (qué alternativas vale la pena dimensionar) y **chequeos** (qué falla o qué avisar), evaluados sobre el resultado del balance, Equipos y Entorno. Ninguna regla elige por sí sola: la elección sale del trade-off (sección 3).

| # | Pregunta | Disparador, en salidas del balance | Qué hace Hestia | Respaldo |
|---|---|---|---|---|
| R1 | ¿Alcanza el control pasivo? | `A_pas / A_req ≥ 1` en la cara elegida, en todos los modos que no son de supervivencia | Alternativa sin heaters operativos; heaters de supervivencia si algún modo los pide | Radiador por el caliente y heaters por el frío con la misma área [3, cap. 15, p. 560]; OTS fue totalmente pasivo [6, §5.6] |
| R2 | ¿Hacen falta heaters? | Ventana < 1 (potencia P > 0 en algún caso frío) | Zonas de heaters con set points por modo; P × (1 + m_h) contra el presupuesto | [3, cap. 7, p. 223], [3, cap. 3, p. 73] |
| R3 | ¿Termostato o control electrónico? | Set point de la zona por debajo de 0 °C | Recomendar controlador de estado sólido o por computadora | Termostatos con fallas por hielo en los contactos; se recomiendan controladores bajo 0 °C [3, cap. 7, pp. 226–227] |
| R4 | ¿Radiador variable (louvers)? | Ventana < 1 **y** la cara del radiador sin Sol directo en los casos calientes que dimensionan | Alternativa con louvers. Cota: si `A_pas/A_req` < ε_cerrado/ε_abierto (≈ 0,12–0,26), los louvers solos no alcanzan y siguen haciendo falta heaters | [3, cap. 9, p. 331]; cota: cálculo propio con [3, Tabla 9.2] |
| R5 | ¿Radiador variable (VCHP)? | Igual que R4, con datos de la VCHP | Solo como alternativa del usuario (falta la fracción activa mínima) | [3, cap. 6, p. 209], [3, cap. 14, p. 502] |
| R6 | ¿Repartir el radiador? | `A_req` de la mejor cara > área utilizable de esa cara, u otra combinación de caras baja la potencia de heaters | Alternativa con radiador en varias caras (reparto en la sección 3) | [2, diap. 80 y 103] |
| R7 | ¿Desplegable? | Σ áreas utilizables de las caras permitidas < área requerida | Aviso y alternativa con el área faltante y su masa; o subir la temperatura del radiador | [3, cap. 6, p. 211] |
| R8 | ¿Heat pipes entre caras? | La disipación de los equipos montados en una cara supera lo que rechaza el radiador de esa cara | Transporte requerido ΔQ × L (W·m) con margen y perfil de catálogo | [3, cap. 14, p. 501], [3, cap. 6, p. 209], [11] |
| R9 | ¿Control propio de un equipo? | Equipo incompatible con el nodo (rango vacío) o limitante cuya exclusión mejora la ventana; propulsión siempre | Equipo como nodo aparte con radiador y heaters propios; incompatibles en todas las alternativas | [3, cap. 3, pp. 73–78, 82–83], [6, §8.7.1–8.7.2] |
| R10 | ¿Masa térmica o PCM? | τ / período bajo (aviso del balance), o pulsos de disipación con ciclo de trabajo < β' | Aviso; PCM como alternativa del usuario | [3, cap. 11, p. 381] |

**Orden de preferencia** cuando dos alternativas cumplen: la más simple y probada. Es la regla por defecto del trade-off ([sección 3](#3-trade-off)).

### Justificación y fuentes

- **Preferencia por lo simple:** una especificación típica del TCS pide «la tecnología más simple, más confiable y demostrada en vuelo, sin fallas de punto único» y un diseño predecible por análisis y verificable en tierra [3, cap. 15, p. 527]. SPOT 1 eligió su concepto con ese principio: «componentes simples y confiables de tecnología probada: control pasivo complementado con heaters» [6, §8.6]. ECSS pide predictibilidad y verificabilidad [1, §4.4.6] y capacidad de ajuste (*trimming*) para requisitos tardíos [1, §4.4.7]; ESA pide radiadores con margen de área para crecer y ajustar después del ensayo de balance térmico [2, diap. 103].
- **Tipos de diseño:** un diseño no aislado es posible cuando la disipación interna es chica frente a las cargas ambientales (CubeSats, PROBA); el diseño radiativo (MLI + radiadores) cuando la disipación es mayor, que es el caso de casi todos los satélites [2, diap. 104–105]. Para un satélite mediano Hestia parte del radiativo *(opinión)*.
- **Dónde va el radiador:** en caras sin Sol ni fuentes intensas, con máxima vista al espacio, lejos de propulsores y aberturas; los equipos disipativos detrás del radiador, agrupados por rango de temperatura pero repartidos para evitar puntos calientes [2, diap. 103]. En GEO, los radiadores ocupan el máximo de las caras norte y sur [2, diap. 80]. En Hestia todo esto se traduce en las temperaturas de sumidero por cara del balance: la regla vale para cualquier órbita sin casos especiales *(opinión)*.
- **Pasivo puro es posible:** ESA pidió para OTS un diseño pasivo, sin heat pipes ni heaters controlados automáticamente [6, §5.6]. IUE y Landsat D fueron pasivos salvo louvers en el compartimento cuya disipación y ángulo solar variaban [6, §4.6, §6.6].
- **Louvers frente a heaters:** se eligen cuando la disipación interna varía mucho por ciclos de trabajo; rechazan ~6 veces más abiertos que cerrados sin consumir potencia [3, cap. 9, p. 331]. La cota de R4 (cálculo propio): con el radiador a la sombra y sin carga ambiental, el louver cerrado reduce la emisión por ε_c/ε_o; con los pares medidos de [3, Tabla 9.2] eso va de 0,08/0,67 = 0,12 a 0,10/0,39 = 0,26.
- **VCHP:** se usan con cargas de equipos o ambientales muy variables, o para minimizar los heaters del caso frío [3, cap. 6, p. 209]; regulan bien sin heaters, y con control activo del reservorio usan menos potencia que calentar el equipo directamente [3, cap. 14, p. 502].
- **Heat pipes:** su aplicación más obvia es separar fuente y sumidero; también como «transformador térmico» (un equipo chico y potente sobre un radiador con heat pipes que esparcen el calor) y para reducir gradientes [3, cap. 14, p. 501]. Se usan cuando la conducción lateral de las pieles no alcanza [3, cap. 6, p. 209]. En una celda de un nodo, R8 es un chequeo de capacidad: los gradientes son de la fase 1 *(opinión)*.
- **Control propio, casos típicos:**
  - *Baterías:* radiador dedicado dimensionado algo por debajo del máximo en el peor caliente y heaters con termostato para el mínimo en frío; con NiH₂, rango de 0 a 20 °C; variantes con heat pipes, VCHP o louvers [3, cap. 3, p. 78]. En SPOT 1, compartimento desacoplado con su radiador y heaters [6, §8.7.2].
  - *Propulsión:* aislar conductivamente con soportes de baja conductancia, aislar radiativamente con MLI o acabados de baja ε y calentar, porque la hidracina se congela a 2 °C [3, cap. 3, pp. 73–75]; mismo esquema en OTS y SPOT [7, §4.2.3–4.2.4], [6, §8.7.1.3].
  - *Sensores y ópticas:* aislar conductiva y radiativamente y controlar con un heater proporcional cuando la estabilidad es estrecha [3, cap. 3, pp. 82–83]. Equipos no tiene requisitos de estabilidad: hoy no se pueden detectar automáticamente *(opinión)*.
- **Heaters de supervivencia:** set point más bajo, para gastar menos en modo seguro o lanzamiento [3, cap. 7, pp. 229–230]; en Milstar, tablas de set points distintas por modo del satélite [3, cap. 7, Tabla 7.3].
- **Umbrales sin fuente:** no se encontraron umbrales publicados de densidad de disipación para heat pipes, de ventana pasiva para louvers ni de τ para PCM. Las reglas de arriba usan cálculo en su lugar.

## 3. Trade-off

### Recomendación

**Práctica:** el trade-off de la fase 0 combina análisis paramétrico de cada alternativa (masa, volumen, área de radiador, potencia) con una evaluación de madurez [3, cap. 15, pp. 523–524]. Los trade-offs que se esperan cerrar son: cuánto pasivo y cuánto activo, control distribuido o centralizado en la computadora, controladores de estado sólido o termostatos, ubicación y configuración de los radiadores, selección de heat pipes [3, cap. 15, Tabla 15.2]. ECSS fija la forma del informe: criterios con sus pesos justificados y acordados, alternativas caracterizadas por madurez, desempeño y riesgo, tabla de evaluación por criterio, clasificación según los pesos y **análisis de sensibilidad** a los pesos [8, anexo L].

**En Hestia** *(opinión, sobre esa base)*:

1. **Alternativas.**
   - *Generadas por reglas* (sección 2), siempre en el mismo orden y con ids estables (`alt_baseline`, `alt_louvers`…):
     - `baseline`: el punto de diseño del balance (radiador fijo en la cara elegida, recubrimiento y MLI del balance, heaters donde la ventana < 1) más control propio de los equipos incompatibles, sin el cual no es factible.
     - `coatings`: la base con cada preset de recubrimiento de radiador que tenga α EOL.
     - `split_radiator` (R6), `louvers` (R4), `own_control` (R9, una por equipo limitante) y `deployable` (R7).
   - *Un cambio por vez sobre la base*, más una alternativa que combina los cambios que mejoran algún criterio sin empeorar la factibilidad. Es la poda de un «árbol de trade» [9, §6.8.1.2.2] y evita la explosión combinatoria.
   - *Del usuario:* cualquier composición explícita, incluidas VCHP, LHP y PCM.
2. **Dimensionamiento** con `hestia_core`, para cada alternativa y sobre **todos** los casos candidatos del balance, no solo los que dimensionaron la base (el caso que manda depende de las ópticas: [balance-global.md](balance-global.md#2-armado-de-casos-caliente-y-frío)). Da áreas por radiador, heaters por modo (operativos y de supervivencia), temperaturas, márgenes, transporte entre caras y nodos de control propio. Cuesta ~2600 evaluaciones cerradas por alternativa: con 20 alternativas, menos de un segundo con numpy *(estimación propia)*.
3. **Factibilidad** (requisito, no criterio): rangos admisibles cumplidos en todos los casos con los heaters dimensionados; áreas dentro de lo utilizable; transporte disponible en el catálogo. Los presupuestos de Misión, como criterio con aviso o como requisito, según un parámetro (abierto 9).
4. **Criterios.**

   | Criterio | Cómo se obtiene | Sentido |
   |---|---|---|
   | Masa del TCS con margen de madurez | Calculado (sección 4) | Menor |
   | Potencia de heaters, modos operativos (máximo, con margen) | Calculado | Menor |
   | Potencia de heaters en supervivencia | Calculado | Menor |
   | Fracción del área utilizable ocupada por radiadores | Calculado | Menor (deja margen de ajuste [1, §4.4.7]) |
   | Margen de diseño mínimo en los casos | Calculado | Mayor |
   | Elementos activos o con mecanismo (louvers, VCHP, desplegables, LHP) | Contado | Menor |
   | Zonas de heaters | Contado | Menor |
   | TRL mínimo de las tecnologías usadas | Dato del catálogo | Mayor |
   | Costo, riesgo, verificabilidad | Dato: puntaje por tecnología con definición operativa | Según escala |

5. **Normalización** de cada criterio entre las alternativas factibles (razón al mejor o mín–máx), con escalas de definición operativa para los puntajes, como pide NASA: «alto» tiene que significar un número repetible [9, §6.8.1.2.4].
6. **Método:** suma ponderada con los pesos del usuario. **Sin pesos**, regla lexicográfica: menos elementos activos o con mecanismo → menor masa con margen → menor potencia operativa. El orden sigue la preferencia por lo simple y probado [3, cap. 15, p. 527], [6, §8.6]; el orden entre masa y potencia es *(opinión)*.
7. **Siempre en el resultado:** la matriz de decisión con valores crudos y normalizados, el frente de Pareto (masa, potencia, elementos activos), el ranking, la **sensibilidad** (cuánto tiene que cambiar el peso de cada criterio para que cambie la primera; cerrado en una suma ponderada) y una comparación tipo Pugh contra la base (mejor, igual o peor por criterio, con bandas de tolerancia).
8. **Selección:** parámetro `selected_alternative`; vacío significa la primera del ranking. Elegir otra es aplicar un parámetro, con autor y, si es un agente, con justificación (ADR 0024). La arquitectura entregada a la fase 1 es la seleccionada.

### Qué se calcula y qué se juzga

| Se calcula (`hestia_core`) | Se juzga (entra como dato del usuario) |
|---|---|
| Áreas, potencias, temperaturas, márgenes, transporte, masas, factibilidad | Pesos de los criterios |
| Matriz normalizada, ranking, Pareto, sensibilidad | TRL y puntajes de costo, riesgo y verificabilidad por tecnología |
| Disparadores de las reglas y alternativas generadas | Alternativas propias; qué hacer con un presupuesto excedido |
| — | La selección final, si no es la primera del ranking |

El reparto masa/potencia no se compara en kilos equivalentes: ninguna fuente consultada da un factor de masa por W de potencia eléctrica. Queda a los pesos *(opinión)*.

### Alternativas de método

| Método | A favor | En contra |
|---|---|---|
| Matriz ponderada (suma ponderada) | Estándar [9, §6.8.1.2.3], [8, anexo L]; determinística; sensibilidad cerrada | Depende de los pesos y de la normalización; compensa un criterio malo con otros buenos |
| Pugh (contra una alternativa de referencia) | Simple, cualitativo, bueno para podar | Ordinal; las bandas de «igual» son arbitrarias |
| Lexicográfico con requisitos y deseos | Refleja la preferencia por lo simple sin pesos | Ignora diferencias chicas en el primer criterio |
| AHP | Pesos por comparación de pares, con chequeo de consistencia [9, §6.8.2] | Muchos juicios del usuario; más difícil de explicar y de reproducir a mano |
| Frente de Pareto | Sin pesos; muestra lo que se cambia por qué | No elige una sola alternativa |

Recomendado: matriz ponderada si hay pesos, lexicográfico si no, y Pareto y Pugh siempre como vistas *(opinión)*.

### Reparto del área entre caras

Con un nodo, el rechazo de cada cara es lineal en su área, así que repartir es un problema chico.

| Opción | A favor | En contra |
|---|---|---|
| Codicioso: llenar caras en orden de rechazo neto por m² en el peor caso caliente, hasta el área utilizable | Cerrado, en `hestia_core` (solo numpy) | No minimiza la potencia de heaters del caso frío |
| Programación lineal: mínima área (o masa) sujeta a todos los casos calientes, con la potencia del frío como objetivo secundario | Óptimo con varios casos y caras | Necesita un solver: SciPy vive en `hestia_adapters`, detrás de un Protocol |
| Áreas del usuario | Control total | Sin automatismo |

Recomendado: codicioso más override del usuario en la primera versión; programación lineal después *(opinión)*.

## 4. Masa y potencia del TCS en la fase 0

### Recomendación

- **Masa por componente**, con lo que el concepto ya calcula: área de MLI × kg/m², área de cada radiador × kg/m² según su montaje, área de louvers × kg/m², longitud de heat pipes × g/m, termostatos y controladores por zona × masa unitaria, PCM por energía. Cada componente con su **margen de madurez**: ≥ 5 % para ítems de catálogo, ≥ 10 % con modificaciones menores y ≥ 20 % para desarrollos nuevos [10, R-M1-4]. La categoría por tecnología es un parámetro con default *(opinión)*.
- **Comparación:** masa con margen de madurez ≤ `tcs_mass_budget`. El margen de sistema de ESA (20 %) se lleva a nivel de sistema, no en el presupuesto del TCS [10, R-M1-1 a R-M1-3].
- **Masa paramétrica solo como chequeo:** el resultado informa la masa del TCS como fracción de la masa del satélite y la compara con el rango histórico. Fuera de rango es un aviso, no un error.
- **Potencia:** heaters (promedio orbital) por modo operativo, operativos y de supervivencia por separado. Con margen `m_h` del balance, comparados con `heater_power_budget`. Más los heaters propios (control propio de equipos, reservorios de VCHP) y el consumo en reposo de los controladores. La potencia **instalada** (pico) sale de un ciclo de trabajo máximo: 70 % según GSFC [11]. Se informa; Misión no tiene presupuesto de pico.
- **Lo que no entra:** el arnés del TCS, que ESA cuenta a nivel de sistema (≥ 5 % de la masa seca, para todo el satélite) [10, R-M1-7], y la masa de heaters y termistores, sin dato en lo consultado. El resultado lo dice.

### Datos paramétricos

| Población | TCS, % de la masa seca | Fuente |
|---|---|---|
| 17 satélites (comunicaciones, navegación, meteorológicos, militares) | 4,3 promedio, desvío 3,1; de 0,48 (DSP 15) a 11,03 (GPS Blk 2) | [12, apéndice D, Tabla 1], de SMAD y SSE |
| 11 telecomunicaciones GEO | 5,0 promedio, desvío 1,1 | [12, apéndice D, Tabla 2] |
| 13 satélites chicos (< 500 kg) | 3,1 promedio (con ceros: TCS cargado en estructura) | [12, apéndice D, Tabla 3] |
| «Medianos a grandes», según SMAD | 8,5 (rango 2–15) | [12, apéndice D, Tabla 4] |
| OTS | 18,7 kg de 340,4 kg secos: 5,5 % (cálculo propio) | [6, Tabla 5-2] |
| SPOT 1 | 43 kg; del orden del 2,5 % de la masa total (cálculo propio, base húmeda) | [6, Tabla 8-2] |

- Las dos tablas de SMAD citadas por [12] no coinciden (4,3 % frente a 8,5 %): por eso no sirve como default de masa, solo como rango.
- En satélites pasivos la masa del TCS a veces se carga en estructura [12, apéndice D]: los porcentajes bajos no son comparables.
- **Misión tiene la masa total al inicio de vida, no la seca:** el chequeo paramétrico sobre esa masa da un porcentaje menor que el real (abierto 4).

### Alternativas

| Alternativa | A favor | En contra |
|---|---|---|
| Paramétrica (% de masa seca) | Disponible antes de cualquier concepto | Dispersión enorme (0,5–11 %); no distingue alternativas; tablas inconsistentes |
| Por componente | Distingue alternativas; usa lo que el concepto calcula; sigue el detalle que pide ECSS para el presupuesto [1, anexo F <9>] | Falta dato para algunos componentes (heaters, termistores, recubrimientos) |
| Ambas | Por componente para decidir, paramétrica para sanidad | — |

### Justificación y fuentes

- ECSS pide que la especificación del TCS asigne masa y potencia [1, §4.2.1 g], que el TCS defina sus presupuestos de masa, potencia, energía y telemetría [1, §4.4.2] y que la descripción del diseño los liste [1, anexo F <9>].
- Gilmore: la conclusión de los análisis de la fase de concepto es «el peso, el volumen y la potencia del subsistema térmico» [3, cap. 15, p. 524].
- **Hallazgo para el balance:** ESA aplica a la potencia de las unidades electrónicas márgenes de madurez de 5/10/20 % [10, R-P-1]. Es la fuente que faltaba para el punto abierto 10 del balance (margen de madurez de la disipación).

## 5. Iteración con el balance

### Recomendación

- **El concepto no necesita recalcular el balance.** Cada alternativa se redimensiona dentro de `tcs_concept` con la misma función de `hestia_core` que usa el balance, generalizada a varias superficies: radiadores en varias caras, cada uno con su recubrimiento y su control; MLI en el resto; equipos con control propio como nodos aparte. El balance queda como referencia: el problema térmico y la envolvente de un radiador fijo.
- **Qué toma el concepto del balance:** sus parámetros aplicados (compatibilidad actitud ↔ modo, casos propios, recubrimientos y MLI de base, margen de heaters, cp) y su resultado (rangos por modo, casos dimensionantes, punto de diseño, ventana, τ, sumideros), con la procedencia de la celda. Los flujos incidentes y la disipación los toma del contexto (Entorno, Equipos), igual que el balance.
- **Lo que sí va aguas arriba** son los cambios del *problema*: márgenes y presupuestos (Misión), equipos, límites y modos (Equipos), órbita y actitudes (Entorno), casos y compatibilidad (parámetros del balance). Se editan donde viven y desactualizan el concepto (ADR 0021).
- **Corregir el catálogo:** cambiar «Itera a 0.4» por algo como «redimensiona las alternativas sobre los casos del balance». La iteración clásica (cambiar el balance y volver) queda como edición aguas arriba o ramificación, igual que hoy (ADR 0009).

| Cambio en el concepto | ¿Cambia el resultado del balance? | Dónde se resuelve *(opinión)* |
|---|---|---|
| Otro recubrimiento del radiador o de la capa externa | Sí: área, heaters y caso que manda | En el concepto: cada alternativa reevalúa todos los casos |
| Radiador en varias caras | Sí: el balance supone una cara | En el concepto, con la función de varias superficies |
| Louvers o VCHP | Sí: ε o área variable | En el concepto |
| Equipos con control propio | Sí: salen de la intersección de rangos y su disipación pasa a su propio radiador | En el concepto (el balance ya tiene `separately_controlled_items` como «¿y si…?») |
| Otra especificación de MLI | Sí | En el concepto |
| Margen de incertidumbre, límites, modos, órbita | — (es el problema) | Aguas arriba |

### Alternativas

| Alternativa | A favor | En contra |
|---|---|---|
| Redimensionar en el concepto (recomendada) | Sin ciclos; un solo cálculo compartido; el trade-off ve todas las alternativas a la vez | El balance no muestra la arquitectura elegida (no es su trabajo) |
| Acción «llevar al balance»: copia recubrimiento, caras o equipos con control propio a los parámetros del balance | El balance refleja la elección | Edición aguas arriba que desactualiza el concepto que la originó; dos lugares con la misma decisión |
| Ramificar un balance por alternativa | Usa lo que ya existe (ADR 0009) | El trade-off queda repartido en celdas; hace falta un colector para comparar |

### Justificación y fuentes

- El grafo es acíclico y las iteraciones se resuelven editando aguas arriba o ramificando ([ADR 0009](../adr/0009-esquematico-de-proyecto.md), [workflow](../workflow-fases-0-1.md#pendientes)).
- El balance ya pedía que la evaluación de un caso fuera una función reutilizable de `hestia_core` porque el concepto iba a evaluar alternativas sobre sus casos ([balance-global.md](balance-global.md#6-qué-entrega-el-balance-a-concepto-tcs)). Esta investigación lo confirma y lo amplía: hay que reevaluar **todos** los casos, no solo los dimensionantes, porque el peor caso depende de las ópticas [balance-global.md, sección 2].
- En la industria el ciclo concepto ↔ balance existe porque las herramientas son modelos separados; en Hestia la misma función hace los dos trabajos *(opinión)*.

## 6. Qué entrega a la fase 1

### Recomendación

Un artefacto **`TcsArchitecture`** versionado, parte del resultado de `tcs_concept` (la alternativa seleccionada), con ids estables y prefijos como en el [ADR 0025](../adr/0025-ids-propuestos-por-el-cliente.md). Es lo que el anexo F de ECSS pide describir del concepto: pasivo o activo, ubicación de aislación y radiadores, heaters y su control, superficies activas [1, anexo F <5>], y lo que Gilmore pide documentar antes de la PDR: áreas de radiador, aislación, acabados con sus propiedades, heaters con tamaño y ubicación, heat pipes [3, cap. 15, p. 530].

| Parte | Contenido | Para qué la usa `discretization` *(opinión)* |
|---|---|---|
| `surfaces` | Por cara: zonas (radiador, MLI) con área y propiedades ópticas (α BOL/EOL, ε; o ε* y capa externa), con su fuente | Propiedades ópticas de los nodos externos |
| `radiators` | id (`rad_`), cara, área, recubrimiento, montaje (estructural, al cuerpo, desplegable), control (fijo; louvers con ε abierto/cerrado y temperaturas; VCHP), a quién sirve (cuerpo o un equipo) | Nodos de radiador y su control |
| `insulation` | ε* (mín./máx.), capa externa, masa por m², cobertura | Acoplamiento radiativo efectivo del cuerpo |
| `heater_zones` | id (`htz_`), destino (cuerpo, equipo, radiador, reservorio), propósito (operativo, supervivencia), set point de encendido y banda muerta por modo de heaters, potencia instalada y promedio por modo, tipo de control | Fuentes de calor con lógica de termostato en `load_cases` |
| `heat_transport` | id (`hp_`), tipo (CCHP, VCHP, LHP), de qué cara o equipo a qué radiador, longitud, W·m requeridos con margen, perfil de catálogo, cantidad | Conductores de alta conductancia |
| `own_control_items` | Equipo, radiador propio, zona de heaters propia, conductancia de acoplamiento al cuerpo | Nodos aparte y sus acoplamientos |
| `budgets` | Masa por componente con margen; potencia de heaters por modo | Referencia de los chequeos de la fase 1 |
| `assumptions` | Supuestos y puntos abiertos con código | Avisos que la fase 1 tiene que cerrar |

## Propuesta de parámetros

Formulario de parámetros como en Entorno y el balance ([ADR 0021](../adr/0021-etapas-de-calculo.md)): borrador, validación en seco, Aplicar, defaults de biblioteca con procedencia. Un valor vacío con preset significa «el del preset»; se resuelve al actualizar y el resultado informa el valor y su fuente.

Lo que viene del contexto no se repite como parámetro:
- **Misión:** envolvente, masa, márgenes, presupuestos, `radiator_faces`, `design_life`.
- **Entorno:** condiciones, actitudes, flujos por cara, período.
- **Equipos:** equipos con `location`, `subsystem`, límites y modos; la función de disipación.
- **Balance:** parámetros aplicados (recubrimientos y MLI de base, compatibilidad, casos propios, margen de heaters, cp) y resultado (rangos, casos, punto de diseño, ventana, τ, sumideros).

### 1. Alternativas (`alternatives`)

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `auto_generate` | `bool` | — | sí | *(opinión)* |
| `generators` | `list[enum Generator]` | — | todos | *(opinión)* |
| `user_alternatives` | `list[AlternativeSpec]` | — | vacía | — |

`Generator`: `coatings`, `split_radiator`, `louvers`, `own_control`, `deployable`. La base se genera siempre.

**`AlternativeSpec`:** `id` (`alt_`), `name`, `radiators: list[RadiatorSpec]`, `insulation` (vacío: la del balance), `own_control: list[OwnControlSpec]`, `heater_control` (`auto` \| `thermostat` \| `solid_state` \| `computer`; `auto` aplica R3), `transport` (`auto` \| `none`).

**`RadiatorSpec`:**

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `face` | `enum Face` | — | obligatorio | — |
| `area` | `float` | m² | vacío: automática | *(opinión)* |
| `coating` + `absorptance_bol/eol`, `emittance` | como el balance | — | presets del balance | [balance-global.md](balance-global.md#propuesta-de-parámetros) |
| `mounting` | `enum` (`structural` \| `body_mounted` \| `deployable`) | — | `structural` | *(opinión)* |
| `control` | `enum` (`fixed` \| `louvers` \| `vchp`) | — | `fixed` | — |
| `louver_emittance_open` | `float` | — | 0,67 | Intelsat CRL sobre Teflon plateado [3, Tabla 9.2] |
| `louver_emittance_closed` | `float` | — | 0,08 | Ídem |
| `louver_open_close_delta` | `float` (ΔT) | K | 10 | Ídem |
| `louver_open_temperature` | `float` | K | vacío: el máximo admisible del caso | *(opinión)* |
| `vchp_min_active_fraction` | `float` | — | obligatorio si `vchp` | Sin fuente |

**`OwnControlSpec`:** `item_id`, `radiator_face` (vacío: la `location` del equipo si es una cara; obligatorio si es `internal`), `radiator_coating` (vacío: el del radiador principal), `radiator_area` (vacío: automática), `coupling_conductance` (W/K; default 0, aislación ideal *(opinión)*, abierto 6).

### 2. Caras (`faces`)

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `usable_fraction` | `map[Face, float]` | — | 1,0 en todas (solo el límite geométrico, como el balance) | *(opinión)*; sin fuente para un valor menor |

### 3. Heaters (`heaters`)

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `survival_modes` | `list[ref(operating_modes)]` | — | vacía | — (abierto 3) |
| `max_duty_cycle` | `float` | — | 0,70 | [11] |
| `thermostat_dead_band` | `float` (ΔT) | K | 4 | Mínimo recomendado [3, cap. 7, p. 225] |

El margen de potencia `m_h` es el del balance: no se repite.

### 4. Transporte (`transport`)

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `heat_pipe_catalog` | `list[HeatPipeProfile]` | — | Los cinco perfiles de Thales (Ø11, 12,2, 14, 19, 22): W·m a 20 y 80 °C y g/m | [4, Tablas 9-10 y 9-11] |
| `transport_margin` | `float` | — | 0,30 | [11] |
| `path_length` | `enum` (`face_centers`) | — | distancia entre centros de caras | *(opinión)* |

### 5. Masa (`mass`)

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `mli_areal_mass` | `float` | kg/m² | 0,50 (extremo alto) | [2, diap. 77]; elegir el extremo alto es *(opinión)* |
| `radiator_areal_mass` | `map[Mounting, float]` | kg/m² | `structural` 0; `body_mounted` 5; `deployable` 12 | [3, cap. 6, pp. 208–209]; el 5 es el supuesto de [3, cap. 11, p. 382], usado *(opinión)* |
| `louver_areal_mass` | `float` | kg/m² | 5,4 | [3, Tabla 9.1], extremo alto de OSC |
| `thermostat_mass` | `float` | kg | 0,0054 | [15] |
| `controller_mass` | `float` | kg | 0,030 | [3, Tabla 7.1] |
| `pcm_specific_storage` | `float` | W·h/kg | 35 | [3, cap. 11, p. 382] |
| `maturity_category` | `map[Technology, enum (A_B \| C \| D)]` | — | MLI, radiadores y zonas de heaters: C; termostatos, controladores, heat pipes y louvers de catálogo: A_B; desplegables: D | Categorías y márgenes [10, R-M1-4]; la asignación es *(opinión)* |

### 6. Trade-off (`tradeoff`)

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `weights` | `map[enum Criterion, float]` | — | vacío: regla lexicográfica | [8, anexo L <5>] pide pesos justificados; el default es *(opinión)* |
| `technology_scores` | `map[Technology, Scores]` | — | TRL: vacío (dato del usuario); costo, riesgo y verificabilidad: vacíos (el criterio no se usa) | Sin fuente para defaults |
| `budget_policy` | `enum` (`criterion` \| `constraint`) | — | `criterion` | *(opinión)* |
| `pugh_reference` | `ref(alternatives)` | — | la base | *(opinión)* |
| `selected_alternative` | `ref(alternatives)` | — | vacío: la primera del ranking | *(opinión)* |

### Validaciones

- **Parámetros:** α, ε y ε* en (0, 1]; `louver_emittance_closed` < `louver_emittance_open` (`order`); fracciones en (0, 1]; masas, márgenes y Δ ≥ 0; ciclo de trabajo en (0, 1]; caras de radiador dentro de las permitidas por Misión (`not_allowed`); la suma de áreas fijadas por cara ≤ área utilizable; `vchp_min_active_fraction` obligatoria con `vchp` (`required`); catálogo de heat pipes no vacío.
- **Referencias** (`invalid_reference`): equipos, modos operativos y alternativas.
- **Al actualizar:** `missing` y `context_invalid` como en Entorno ([ADR 0022](../adr/0022-contrato-de-etapas-de-calculo.md)); el balance del contexto sin resultado actual es `context_invalid`. Una alternativa no factible **no** hace fallar la celda: es un resultado con su motivo. Que ninguna sea factible es un aviso *(opinión)*.

## Propuesta de resultado

### Qué calcula, en orden

1. Alternativas: la base, las generadas (con la regla que las habilitó) y las del usuario, en orden estable.
2. Por alternativa, sobre todos los casos candidatos del balance: rangos (sin los equipos con control propio), áreas (automáticas o fijas), heaters por modo, temperaturas, márgenes, nodos de control propio, transporte entre caras.
3. Factibilidad y motivos.
4. Masa por componente con margen, potencia por modo, chequeo paramétrico, comparación con los presupuestos.
5. Matriz de decisión, normalización, ranking (ponderado o lexicográfico), Pareto, sensibilidad, Pugh.
6. Arquitectura de la alternativa seleccionada.
7. Avisos.

### Partes

| Parte | Contenido |
|---|---|
| `inputs_used` | Valores del catálogo y presets usados con su fuente; celda y cambio del balance usados |
| `alternatives` | Especificación resuelta de cada alternativa, origen (`baseline`, generador y regla, `user`) |
| `sizing` | Por alternativa: radiadores (cara, área, rechazo neto, caso que manda), heaters por modo, temperaturas libres, margen de diseño, ventana, nodos de control propio, transporte por cara (ΔQ, W·m, perfil), factible y motivos |
| `budgets` | Por alternativa: masa por componente y con margen, potencia por modo (promedio con margen, instalada), fracción paramétrica, frente a `tcs_mass_budget` y `heater_power_budget` |
| `decision` | Criterios (crudos y normalizados), ranking, método usado (ponderado o lexicográfico), frente de Pareto, sensibilidad por criterio, Pugh contra la referencia |
| `architecture` | `TcsArchitecture` de la alternativa seleccionada ([sección 6](#6-qué-entrega-a-la-fase-1)) |
| `warnings` | Código, mensaje y referencia: ninguna factible, presupuesto excedido, louvers en cara iluminada, área de desplegable sin evaluar, valores sin fuente (heaters, termistores, recubrimientos), masa paramétrica fuera de rango |
| `provenance` | Celdas y cambios del contexto, parámetros, proveedor y versión ([ADR 0021](../adr/0021-etapas-de-calculo.md)) |

Todo es chico (decenas de alternativas, miles de filas): JSON en el `.hestia`, como Entorno.

## Lo que queda abierto

Cada punto con su recomendación; decidir antes de especificar.

1. **Una etapa con alternativas y selección** es un patrón nuevo en el contrato de las etapas de cálculo (resultado con varias soluciones y un parámetro que elige). Recomendado: un ADR al especificar, que fije también cómo la UI muestra la matriz y cómo el MCP la lee.
2. **Pesos por defecto.** Recomendado: ninguno, y regla lexicográfica (simple → masa → potencia). Alternativa: pesos iguales, más fácil de explicar pero sin respaldo.
3. **Presupuesto de supervivencia.** Ya abierto en el balance (punto 7) y acá se vuelve necesario: la potencia de supervivencia es un criterio. Recomendado: marcar modos operativos de supervivencia (en Equipos o como parámetro acá) y agregar un `survival_heater_power_budget` opcional en Misión.
4. **Masa seca en Misión.** Los porcentajes de masa del TCS son de masa seca; Misión tiene la total. Recomendado: agregar `dry_mass` opcional en Misión; sin ella, el chequeo paramétrico se hace sobre la total con aviso.
5. **Fracción utilizable por cara.** Sin fuente para un valor típico (paneles solares, antenas, sensores y propulsores comparten caras). Recomendado: default 1,0 (solo geometría) y aviso cuando los radiadores ocupan más de la mitad de una cara *(umbral: opinión)*.
6. **Acoplamiento de un equipo con control propio.** Sin fuente para un default de conductancia. Recomendado: 0 (aislación ideal) en la primera versión, con aviso; la fase 1 la calcula.
7. **Radiadores desplegables.** Entorno no modela apéndices, así que un panel desplegable no tiene flujos propios. Recomendado: en la primera versión, solo área faltante, masa y aviso; evaluarlo térmicamente cuando Entorno sume apéndices.
8. **VCHP, LHP y PCM.** Recomendado: solo como alternativas del usuario (falta la fracción activa mínima de la VCHP; LHP y PCM dependen de datos por equipo).
9. **Presupuestos como criterio o como requisito.** Recomendado: criterio con aviso (los presupuestos se negocian en la fase 0), con `budget_policy` para endurecerlos.
10. **Masa de heaters, termistores y recubrimientos.** Sin dato publicado en lo consultado. Recomendado: no incluirlas, decirlo en el resultado y buscar el dato en el tema 6 (satélites reales).
11. **Louvers en caras iluminadas.** Recomendado: no generarlos si la cara recibe Sol directo en algún caso caliente que dimensiona; como alternativa del usuario, con α efectiva obligatoria.
12. **Relación con `separately_controlled_items` del balance.** Recomendado: el balance lo conserva como «¿y si…?»; la arquitectura (qué equipos tienen control propio) la decide el concepto.
13. **Longitud de transporte.** Recomendado: distancia entre centros de caras (cota gruesa); la fase 1 la reemplaza por el recorrido real.
14. **Reparto de área entre caras.** Recomendado: codicioso en `hestia_core` más override; programación lineal después, por un Protocol con SciPy en `hestia_adapters`.
15. **Texto del catálogo.** Recomendado: reemplazar «Itera a 0.4» (sección 5).

## Supuestos de física para `physics-reviewer`

1. **Nodo con varias superficies:** el balance sigue lineal en las áreas y en σT⁴, así que las fórmulas cerradas del balance valen con sumas sobre radiadores. Verificar signos, la fuga del MLI en lo que queda de cada cara y el residuo de energía nulo.
2. **Louvers:** ε efectiva lineal entre T cerrado y T abierto [3, ec. 9.3–9.5], sin carga solar en la cara. Con ε(T) el balance deja de ser cerrado: raíz de una función monótona (bisección), con tolerancia explícita.
3. **Cota de R4** (ε_c/ε_o como límite de la ventana): vale sin cargas ambientales; cuantificar cuánto cambia con IR terrestre en LEO.
4. **VCHP:** radiador cuya área activa varía entre `f_min·A` y `A` manteniendo la temperatura de control.
5. **Control propio:** el equipo como nodo isotermo aparte con su radiador y sus heaters, acoplado al cuerpo por G; su disipación sale del nodo principal. Verificar conservación de energía entre los dos nodos y los casos con G = 0.
6. **Supervivencia:** heaters al mínimo admisible del modo (límites no operativos o de encendido de los equipos apagados) más u, con la misma convención del balance.
7. **Transporte entre caras:** ΔQ por cara con la `location` de Equipos, equipos internos repartidos por el nodo; Q·L con L geométrica; capacidad en 0 g frente a 1 g; no sumar dos veces el margen del fabricante (20 %) y el de diseño (30 %) sin decirlo.
8. **Reparto codicioso:** que no deje sin cumplir algún caso caliente cuando distintos casos iluminan distintas caras.
9. **Masas:** lineales en área y longitud; área de MLI = envolvente − radiadores (cota inferior: el MLI real también cubre tanques, líneas y equipos internos).
10. **PCM:** supuestos del criterio de ciclo crítico [3, cap. 11, p. 381] (pulso rectangular, radiador lineal). Test: β' = 0,39 con los datos del ejemplo de [3, p. 382].
11. **Correas:** `m = ρ G L² / k` sin terminales ni resistencia de contacto.
12. **Determinismo del trade-off:** orden estable de alternativas, empates resueltos por id, normalización sin divisiones por cero (todas iguales en un criterio), sensibilidad cerrada.
13. **Casos de referencia:** POAM de Gilmore (ya propuesto en el balance); el ejemplo de PCM [3, cap. 11, p. 382]; el radiador Alpha como chequeo de rechazo específico [3, Tabla 6.1].

## Fuentes

**Consultadas** (copia local en `docs/investigacion/fuentes/`)

1. ECSS-E-ST-31C. *Space engineering — Thermal control general requirements*. ECSS Secretariat, ESA-ESTEC, Noordwijk, 15 de noviembre de 2008. Usadas: §4.2.1 g (asignación de potencia y masa), §4.4.2 (presupuestos), §4.4.6 (predictibilidad y verificabilidad), §4.4.7 (flexibilidad), §4.4.9 (confiabilidad), anexo F <5> y <9> (descripción del diseño del TCS). <https://ecss.nl/standard/ecss-e-st-31c-thermal-control/>
2. ESA. *ECSS-E-ST-31 Standardisation Training Course 2023*, Rev. 1. ESA Space Standardization, 2023. Diapositivas 71–77 (medios de control; MLI: masa específica y ε*), 80 (radiadores en GEO), 89–90 (heat pipes y LHP), 92 (louvers), 102–105 (actividades de diseño, ubicación de radiadores, tipos de diseño). <https://ecss.nl/wp-content/uploads/2023/05/ESA_ECSS-E-ST-31_Standardisation_Training_Course_2023_Rev1.pdf>
3. Gilmore, D. G. (ed.). *Spacecraft Thermal Control Handbook, Volume I: Fundamental Technologies*, 2.ª ed. The Aerospace Press / AIAA, El Segundo, 2002. Capítulos usados:
   - cap. 3, Gilmore et al., «Thermal Design Examples», pp. 71–83;
   - cap. 5, Donabedian et al., «Insulation», p. 165 y Tablas 5.3–5.4 (pp. 173–174);
   - cap. 6, Gilmore, «Radiators», pp. 207–214, Fig. 6.3 y Tabla 6.1;
   - cap. 7, Gilmore, Lyra y Stultz, «Heaters», pp. 223–230, Tablas 7.1 y 7.3;
   - cap. 8, Gluck y Baturkin, «Mountings and Interfaces», pp. 290–296 (doublers);
   - cap. 9, Hardt, Karam y Eby, «Louvers», pp. 331–340, Tablas 9.1–9.2, ec. 9.1–9.5;
   - cap. 11, Bledjian, Hale, Hoover y O'Neill, «Phase-Change Materials», pp. 373–382;
   - cap. 14, Prager, Nikitkin y Cullimore, «Heat Pipes», pp. 490–503;
   - cap. 15, Gilmore y Collins, «Thermal Design Analysis», pp. 523–533 (Tablas 15.1 y 15.2) y p. 560.
4. ECSS-E-HB-31-01 Part 8A. *Space engineering — Thermal design handbook — Part 8: Heat Pipes*. ECSS Secretariat, ESA-ESTEC, 5 de diciembre de 2011. §8.1–8.2.1 (VCHP), cláusula 9 (sistemas existentes): Tablas 9-6 (EHP, aluminio), 9-8 (EHP, acero), 9-9 (Iberespacio), 9-10 y 9-11 (Thales Alenia Space), Fig. 9-25 (ATV). <https://ecss.nl/hbs/active-handbooks/>
5. ECSS-E-HB-31-01 Part 12A. *Space engineering — Thermal design handbook — Part 12: Louvers*. ECSS Secretariat, ESA-ESTEC, 5 de diciembre de 2011. §7.1 (tabla resumen: ATS, Helios, Mariner). <https://ecss.nl/hbs/active-handbooks/>
6. ECSS-E-HB-31-01 Part 15A. *Space engineering — Thermal design handbook — Part 15: Existing Satellites*. ECSS Secretariat, ESA-ESTEC, 5 de diciembre de 2011. §4.6–4.7 (IUE), Tabla 5-2 y §5.6 (OTS), Tabla 6-1 y §6.6 (Landsat D), Tabla 8-2 y §8.6–8.7 (SPOT 1). <https://ecss.nl/hbs/active-handbooks/>
7. ECSS-E-HB-31-01 Part 11A. *Space engineering — Thermal design handbook — Part 11: Electrical Heating*. ECSS Secretariat, ESA-ESTEC, 5 de diciembre de 2011. §4.2–4.4. <https://ecss.nl/hbs/active-handbooks/>
8. ECSS-E-ST-10C Rev.1. *Space engineering — System engineering general requirements*. ECSS Secretariat, ESA-ESTEC, 15 de febrero de 2017. §5.3.3 (análisis de trade-off) y anexo L (informe de trade-off, DRD). <https://ecss.nl/standard/ecss-e-st-10c-rev-1-system-engineering-general-requirements-15-february-2017/>
9. NASA. *NASA Systems Engineering Handbook*, NASA/SP-2016-6105 Rev 2. NASA, Washington, 2016. §6.8.1.2 (análisis de decisión: criterios, alternativas, árbol de trade, normalización con definiciones operativas, robustez del ranking). <https://ntrs.nasa.gov/citations/20170001761>
10. ESA SRE-PA y D-TEC. *Margin philosophy for science assessment studies*, SRE-PA/2011.097, Issue 1 Rev. 3. ESA-ESTEC, 15 de junio de 2012. R-M1-1 a R-M1-7 (masa), R-P-1 y R-P-3 (potencia), R-T-2 y R-T-3 (márgenes térmicos de sistemas criogénicos). <https://sci.esa.int/documents/34375/36249/1567260131067-Margin_philosophy_for_science_assessment_studies_1.3.pdf>
11. Peabody, H. L. y Peabody, S. A. S. «Gaps in Thermal Design Guidelines in the Goddard Space Flight Center GOLD Rules». ICES-2018-268, 48th International Conference on Environmental Systems, Albuquerque, julio de 2018. §I (regla térmica de GSFC-STD-1000 Rev. G: 70 % de ciclo de trabajo de heaters, 30 % de margen de transporte bifásico). <https://ntrs.nasa.gov/citations/20180004564>
12. Zandbergen, B. T. C. *AE1222-II: Aerospace Design & Systems Engineering Elements I — Part: Spacecraft (bus) design and sizing*, apunte del curso, versión 2013/2014. TU Delft. Apéndice D, Tablas 1–4 (distribución de masa por subsistema, de Wertz y Larson, *SMAD*; Fortescue et al., *Spacecraft Systems Engineering*; y MediaGlobe). <https://www.fisme.science.uu.nl/woudschotennatuurkunde/verslagen/Vrsl2013/lezingen/za-Zandbergen/Reader%201222%20-%20Spacecraft%20Design%20(total)_%202013-2014_v2.pdf>
13. NASA Small Spacecraft Systems Virtual Institute. *State-of-the-Art of Small Spacecraft Technology*, cap. 7 «Thermal Control», edición 2022. Tablas 7-2 (tecnologías pasivas) y 7-4 (activas), con TRL para satélites chicos. <https://www.nasa.gov/wp-content/uploads/2023/05/7.-soa-thermal-2022.pdf>
14. Bolton, D. A., Rodriguez-Ruiz, J. E. y Bae, D. «Thermal Straps», borrador de capítulo, NASA, 2024 (NTRS 20240006644). Ec. x.1–x.2 (conductancia), tabla de propiedades de materiales, ejemplos L'Ralph y MAIA. <https://ntrs.nasa.gov/citations/20240006644>
15. Sensata Technologies. *S-311-P641/02 Qualified M2 Series, Narrow Differential, ½" Hermetic Thermostat*, hoja de catálogo, 2021 (masa, corriente nominal, calificación MIL-PRF-24236/20). <https://www.flamecorp.com/PDF/Sensata/2021/G311P641-02_Series_Catalog_Sheets.pdf>

Revisadas sin tomar valores: ECSS-E-HB-31-01 partes 7 (aislaciones), 9 (radiadores) y 10 (PCM).

**No consultadas** (pendientes de verificar; no respaldan ningún valor de este informe)

- Karam, R. D. *Satellite Thermal Control for Systems Engineers*. AIAA, 1998. Sin acceso (ver [topics.md](topics.md#fuentes-accesibles)).
- Wertz, J. R. y Larson, W. J. (eds.). *Space Mission Analysis and Design*, 3.ª ed. Microcosm / Kluwer, 1999. Sus tablas de masa por subsistema llegan a través de [12]; conviene verificarlas en el original, sobre todo la discrepancia entre 4,3 % y 8,5 %.
- Fortescue, P., Stark, J. y Swinerd, G. *Spacecraft Systems Engineering*. Wiley. Citada a través de [12].
- ECSS-E-ST-10-02C, *Verification*: define las categorías de madurez A–D que usa [10]. Citada a través de [10].
- ECSS-E-ST-31-02C, *Two-phase heat transport equipment*. Mencionada en [2, diap. 88].
- AIAA S-120A, *Mass Properties Control for Space Systems*: márgenes de crecimiento de masa por subsistema y madurez, alternativa a [10].
- NASA RP-1358, *System Engineering "Toolbox" for Design-Oriented Engineers*: métodos de decisión, citada por [9].
- Gilmore, D. G. (ed.). *Spacecraft Thermal Control Handbook*, vol. II (criogenia): correas criogénicas, citada por [14].
