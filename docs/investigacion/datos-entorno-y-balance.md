# Datos para Entorno y el balance global: albedo e IR, constante solar, degradación EOL y huecos del balance

**Fecha:** 2026-10-05
**Estado:** investigación para revisar (tema 4 de [topics.md](topics.md)). No es especificación ni ADR; nada de esto está implementado.

## Alcance y cómo leer

- Una sección por pregunta: primero la recomendación, después cómo se usa en la práctica, los datos y lo que queda sin respaldo. Al final: tablas listas para cargar, propuesta de cambios, decisiones abiertas, supuestos para `physics-reviewer` y fuentes.
- **Respaldo y opinión:** lo respaldado lleva su referencia entre corchetes, `[n, lugar]`, numerada como en [Fuentes](#fuentes). *(opinión)* marca criterio propio; *(cálculo propio)* marca números que calculé y no salen de una fuente; *(digitalizado)* marca valores leídos de una figura midiendo píxeles, con su incertidumbre.
- **Verificación de las tablas de albedo e IR:** cada número de NASA/TM-2001-211221 [1] se comparó contra la imagen de la página y, por separado, contra el texto de Gilmore [2], que reproduce las mismas tablas. Coinciden los 252 pares (2 niveles × 2 lados × 3 tipos × 7 tiempos × 3 bandas). Las tablas de la sección final se generaron por script desde esos datos, sin transcribir a mano. No queda OCR dudoso en ellas.
- **Figuras:** las de Gilmore cap. 4 son legibles renderizando la página como imagen; lo ilegible era el texto extraído. Se digitalizaron calibrando contra el marco y las marcas de los ejes; cada tabla dice su incertidumbre y qué tramos son dudosos.
- **Copias locales:** todo lo consultado quedó en `docs/investigacion/fuentes/` (fuera de git).

## Resumen

1. **Albedo e IR:** cargar las tablas completas de NASA (3 bandas × 7 tiempos de promediado × 3 tipos × frío y caliente, a 3,3σ y a 2σ). Entorno pasa a entregar **seis pares albedo ⇔ OLR** (tres por lado) en lugar de mínimos y máximos independientes; el balance evalúa los tres pares de cada lado y se queda con el peor, así Entorno sigue sin conocer α/ε. Default: 90 min y 3,3σ. Banda por la latitud máxima del trazo (una SSO cae en la alta). Corrección por ángulo cenital solar con el polinomio de NASA en cada muestra de la órbita.
2. **Constante solar:** 1361 W/m², pero la fuente es **ECSS-E-ST-10-04C Rev.1 (2020)**, Tabla 6-2. La versión 2008 da 1366,1 y NASA/Gilmore 1367. Cambiar la cita y sacar «a verificar».
3. **Degradación EOL:** α EOL = α BOL + Δα(vida, régimen), con curvas de diseño digitalizadas de Gilmore y datos de vuelo (THERME, LDEF, MISSE, SCATHA, OTS). Hay default en LEO y GEO para casi todos los recubrimientos pedidos, hasta 7–10 años. Sin default: MEO (degrada varias veces más rápido y no hay curvas largas), GEO más allá de ~9 años, SG121FD y PCBE fuera de LEO, y beta cloth en cualquier órbita.
4. **Huecos del balance:** margen de madurez de la disipación con la filosofía de ESA (5 %, 10 % y 20 % por equipo según su categoría), aplicado solo a los casos calientes. Para el gradiente equipo–radiador no hay fuente. cp efectivo: regla de mezcla por masas; hidracina líquida 3,08 kJ/(kg·K) a 298 K. Los 90 min como default tienen respaldo indirecto.
5. **Excentricidad:** con e = 0,01, modelar la órbita como circular al perigeo sobreestima ~2 % los flujos terrestres medios y ~1 % el eclipse, errores del orden de la incertidumbre de los datos de albedo e IR. El umbral 0,01 es defendible.

## 1. Albedo e IR terrestre

### Recomendación

- **Tablas completas de NASA como biblioteca** [1, Tablas 4.2.3-1 a 4.2.3-3 y A-1]. Reemplazan la banda única provisoria de `DESIGN_VALUE_BANDS`. Son las mismas que Gilmore publica como Tablas 2.1 a 2.4 [2, cap. 2, pp. 26–29]. Valores en la tabla T1.
- **Pares, no extremos independientes.** Cada lado (frío y caliente) tiene tres pares albedo ⇔ OLR: extremo de albedo, extremo de OLR y combinado [1, §4.2.3]. Entorno entrega los seis, con flujos por cara para cada uno. El balance evalúa los tres pares de cada lado en cada candidato y se queda con el peor. Entorno sigue sin conocer α/ε y el balance mantiene su regla de enumerar en vez de elegir *(opinión; respaldo abajo)*.
- **Banda por la latitud máxima del trazo**, `φ_máx = mín(i, 180° − i)`: hasta 30° baja, más de 30° hasta 60° media, más de 60° alta [1, §4.2.2]. Una SSO (i ≈ 97–99°) llega a ~82° y cae en la alta *(opinión fundada abajo)*. Hoy `design_value_band` pliega la inclinación a [0, π]: hay que plegarla a [0, π/2].
- **Tiempo de promediado:** parámetro de Entorno con los siete valores de la tabla; default **90 min** (5400 s) *(opinión, ver 4.4)*. El balance compara τ con ese tiempo y avisa si τ es menor.
- **Nivel:** por defecto 3,3σ (percentiles 0,04 y 99,96, el «engineering worst case») [1, §4.2.3]. Los de 2σ (percentiles 5 y 95, Tabla A-1) quedan como opción para estudios de sensibilidad: NASA no los recomienda como especificación salvo en aplicaciones no críticas [1, §5.3].
- **Corrección por ángulo cenital solar (SZA):** los albedos de las tablas están referidos a SZA = 0 y la corrección se suma [1, §4.2.1]. Hestia ya calcula en cada muestra el coseno del SZA en el punto subsatelital, así que corresponde la corrección **instantánea** (el polinomio) en cada muestra: `a(θ) = a_tabla + c(θ)`. Nunca la instantánea y la de promedio orbital a la vez [2, cap. 2, Tablas 2.1–2.4, nota a]. Se aplica en los dos lados.
- **IR de la banda alta con β > 80°:** en la banda alta, caso caliente de extremo de OLR, a 6 h y 24 h, sumar 15 W/m² en las condiciones con |β| > 80° [2, cap. 2, Tablas 2.2 y 2.4, nota c]. NASA da el mismo número para SSO siempre iluminadas [1, Tabla 4.2.3-3, nota]. Depende de la condición, no de la órbita.
- **Radio de la fuente:** los valores están referidos al tope de la atmósfera, R_E + 30 km [1, §3.4.1]. Conviene usar R_E + 30 km como radio de la Tierra en los factores de vista de albedo e IR (no en el eclipse) *(opinión)*: es lo que define la fuente y no cuesta nada. No hacerlo subestima menos de 1 % [1, §3.4.1; 2, cap. 2, p. 25].

### Cómo se usan en la práctica

- **Qué representan:** extremos de medias móviles de los datos del experimento ERBE (resolución de 16 s, 28 meses entre noviembre de 1984 y julio de 1987), por banda de inclinación, para promedios de 16 s a 24 h. Promediar más de 24 h no cambia los resultados [1, §4.1 y §4.2.2; 2, cap. 2, p. 25].
- **Cómo se elige el tiempo:** según la constante de tiempo del sistema. Se modela solo el ciclo luz–sombra con el albedo y la OLR extremos que le corresponden a esa constante [1, §4.2.2].
- **Percentiles:** 0,04 y 99,96, equivalentes a ±3,3σ si la distribución fuera normal. Son la fracción del tiempo en que se superan, no una probabilidad sobre la vida de la misión [1, §4.2.3; 2, cap. 2, p. 25]. Los peores datos superaron los valores de 3,3σ en 17 W/m² (OLR) y 0,06 (albedo) a 16 y 128 s [2, cap. 2, p. 30; 1, §5.1].
- **Pares:** albedo y OLR están parcialmente correlacionados: albedo alto con OLR baja [1, §4.2.3]. El par de un extremo de OLR lleva el promedio de los albedos medidos junto con esos OLR, y al revés. El «combinado» es el percentil del subconjunto donde las dos variables normalizadas son iguales [1, §4.2.3; 2, cap. 2, pp. 30–31].
- **Qué par manda depende de la superficie,** de su relación α/ε [1, §4.2.3]. Los acabados de radiador (α ~0,2, ε ~0,8) son mucho más sensibles a la IR que al albedo [2, cap. 2, p. 31]. La herramienta STEM de NASA elige el tipo con una esfera según α/ε [1, §5.3]. El balance de Hestia puede hacerlo sin esfera: evaluar los tres.
- **2σ o 3,3σ:** según la tolerancia al riesgo. La diferencia es chica con constantes de tiempo de 90 min o más, y el margen de incertidumbre usual de 10 °C equivale a una protección de ~2σ [2, cap. 2, p. 30].
- **Inicialización:** en el método de la ISS cada perfil se inicializa con las condiciones de promedio de 90 min y los pulsos cortos se aplican encima [1, §5.3].

### Cuánto exagera hoy «máximo con máximo» *(cálculo propio, ilustrativo)*

Flujo terrestre absorbido por unidad de factor de vista en el punto subsolar, `q = α·S·a + ε·OLR`, con S = 1361 W/m², banda baja y 90 min (pares de la tabla T1):

| Superficie | Peor par caliente | q (W/m²) | Máx. + máx. | Exceso | Peor par frío | q (W/m²) | Mín. + mín. | Defecto |
|---|---|---|---|---|---|---|---|---|
| Radiador (α 0,10, ε 0,80) | OLR (0,20 ⇔ 285) | 255 | 266 | +4 % | OLR (0,25 ⇔ 206) | 199 | 180 | −10 % |
| Kapton (α 0,38, ε 0,67) | combinado (0,24 ⇔ 275) | 308 | 336 | +9 % | combinado (0,14 ⇔ 228) | 225 | 195 | −13 % |
| Negro (α 0,95, ε 0,85) | albedo (0,28 ⇔ 237) | 563 | 604 | +7 % | albedo (0,11 ⇔ 258) | 362 | 317 | −12 % |

Cada superficie tiene otro peor par: por eso el balance tiene que evaluar los tres. Combinar extremos independientes es conservador en los dos lados.

### Elegir banda, tiempo y tipo

- **Banda.** NASA divide en tres bandas porque la dependencia con la latitud es débil [1, §4.2.2], pero no dice qué hacer con i > 90°. Lo que cuenta es qué latitudes recorre el trazo, y en una órbita retrógrada el máximo es 180° − i *(opinión)*. Respaldo indirecto: los datos de alta inclinación incluyen los de NOAA-9 y NOAA-10, que estaban en SSO [1, §4.1 y §4.2.2], y la nota de la Tabla 4.2.3-3 habla de satélites heliosincrónicos [1]. En los bordes, 30° cae en la baja y 60° en la media: la fuente dice «0 to 30», «>30 to 60» y «>60» [1, §4.2.2].
- **Tiempo de promediado.** El que corresponde a la constante de tiempo [1, §4.2.2]. Para el cuerpo de un satélite mediano (τ de horas, [balance-global.md](balance-global.md), sección 1) el valor «justo» sería el de 6 h; el de 90 min es más severo. Por ejemplo, la OLR caliente de la banda baja es 285 W/m² a 90 min y 269 a 6 h [1, Tabla 4.2.3-1]. Las piezas livianas (paneles, radiadores desplegables, τ de minutos) piden 896 s o 30 min, pero eso es de `load_cases` y `discretization`.
- **Tipo.** Se evalúan los tres; Entorno no necesita α/ε.

### Corrección por ángulo cenital solar

- **Polinomio** (SZA en grados, válido entre 0° y 90°) [1, §4.2.1, p. 6]: `c(θ) = C4·θ⁴ + C3·θ³ + C2·θ² + C1·θ`, con los coeficientes de la tabla T3. Quita la dependencia con el SZA dentro de ±0,04 [1, §4.2.1].
- **Promedio orbital** según β [1, Tabla 4.2.1-1] y **promedio de pulsos** desde el mediodía solar [1, Tabla A-2]: tabla T3. Gilmore publica las mismas correcciones, pero solo en algunos ángulos [2, cap. 2, Tablas 2.1–2.4].
- **Cuándo importa:** para constantes de tiempo cortas (menos de 10 min) en órbitas de inclinación baja y media, y para las SSO cerca del terminador incluso en promedio orbital [1, §4.2.1]. Con β = 60° suma 0,12 al albedo medio [1, Tabla 4.2.1-1].
- **Sirve de test:** el promedio del polinomio pesado con cos θ sobre la parte iluminada del trazo, con `cos θ = cos β · cos u`, reproduce la Tabla 4.2.1-1 y la columna de 128 s de la A-2 dentro de ±0,005 *(cálculo propio)*. El método está descrito en [1, Apéndice, Tabla A-2]. Es un oráculo directo para el proveedor.

### Radio de referencia

- **Qué dice la fuente:** los datos se llevaron al tope de la atmósfera (R_E + 30 km) y hay que suponer la fuente a esa altura. No hacerlo subestima el albedo y la OLR en un factor `Fa = (R_E + A)² / (R_E + 30 km + A)²`, que vale 0,9911 a 300 km y tiende a 1 al subir [1, §3.4.1]. Gilmore: modelar la Tierra con 6408 km; usar 6378 km da menos de 1 % de error [2, cap. 2, p. 25].
- **En Hestia:** `plate_to_earth_view_factor` usa `EARTH_RADIUS_M` = 6 378 137 m. El error es chico frente a la incertidumbre de la OLR (~5 W/m², [1, §5.1]), pero corregirlo cuesta una constante *(opinión)*.

### GEO y MEO

- Los datos son de LEO: ERBE medía a 610, 815 y 849 km, y la guía describe el ambiente de órbita baja [1, §2 y §3.2]. No encontré valores de diseño para MEO o GEO.
- En GEO los flujos terrestres son chicos: el factor de vista de una cara nadir es (R_E/r)² ≈ 0,023, así que 285 W/m² de OLR llegan como ~6,5 W/m² *(cálculo propio)*. Usar las mismas tablas mueve poco el resultado *(opinión)*.

### Sin respaldo

- La regla de la latitud máxima para inclinaciones retrógradas (inferencia, con respaldo indirecto).
- 90 min como default (ver 4.4).
- Aplicar las tablas de LEO en MEO y GEO.

## 2. Constante solar

### Recomendación

- **Mantener 1361 W/m² y citar ECSS-E-ST-10-04C Rev.1 (15 de junio de 2020), §6.1.2.1 y Tabla 6-2** [3]. Es la revisión vigente en ecss.nl (consultado el 2026-10-05). Sacar «a verificar» de `SOLAR_CONSTANT_SOURCE` y de [environment.md](../etapas/environment.md).
- **La irradiancia de cada fecha** sigue saliendo de la distancia Tierra–Sol, como ya hace Hestia; no hace falta cargar afelio y perihelio.
- **Sin incertidumbre adicional:** ECSS da ±0,5 W/m² (1σ) y una variación de ~1,3 W/m² en el ciclo solar (1360,5 a 1362) [3, §6.1.2.1], despreciables frente al albedo y la IR *(opinión)*.
- **Test:** afelio y perihelio de la Tabla 6-2 (1316 y 1407 W/m²) contra `S/r²` en esas fechas, con 1 W/m² de tolerancia *(propuesta)*.

### Datos

| Fuente | Irradiancia a 1 UA (W/m²) | Afelio (W/m²) | Perihelio (W/m²) | Notas |
|---|---|---|---|---|
| ECSS-E-ST-10-04C Rev.1 (2020) [3, §6.1.2.1, Tabla 6-2] | 1361 ± 0,5 (1σ) | 1316 | 1407 | Valor acordado por la IAU; cita a Kopp y Lean (2011) |
| ECSS-E-ST-10-04C (2008) [4, Tabla 6-2] | 1366,1 | 1321,6 | 1412,9 | Reemplazada por la Rev.1 |
| NASA/TM-2001-211221 [1, §3.1]; Gilmore [2, cap. 2, p. 22] | 1367 | 1322 (caso frío) | 1414 (caso caliente) | World Radiation Center (Davos), mediciones de 1969 a 1980. NASA admite ±5 W/m² más por medición y ciclo solar, que no incluye |

- La diferencia entre 1361 y 1367 es 0,44 % (6 W/m²) *(cálculo propio)*.
- Ojo con una cifra cercana: ECSS normaliza el espectro ASTM E-490 a 1362 W/m² [3, Anexo F.1]. Es el espectro, no la constante de diseño.

## 3. Degradación EOL de recubrimientos

### Recomendación

- **Modelo:** `α_EOL = α_BOL,máx + Δα(t, régimen)`, con `t` = `design_life` de Misión, el régimen sacado de la órbita de Entorno y Δα interpolado linealmente en una curva de la tabla T5. El frío sigue usando `α_BOL,mín` *(opinión: las curvas de Gilmore dan el aumento respecto del propio BOL; sumarlo al extremo alto del rango es conservador)*.
- **Régimen** *(opinión, con el límite de [2, cap. 4, p. 150])*:
  - **LEO:** altitud máxima ≤ 1000 km (por debajo del cinturón interior de Van Allen, donde la dosis ionizante es baja [2, cap. 4, p. 150]);
  - **GEO:** tipo `geo`;
  - **otra:** cualquier otra órbita (MEO, 12 h, LEO alta).
- **Default solo donde hay fuente para el régimen y la vida.** Fuera de eso, α EOL es obligatorio y el problema dice por qué (sin datos para la órbita o vida mayor que la curva). Resumen:

| Recubrimiento | LEO | GEO | Otra órbita |
|---|---|---|---|
| OSR (espejo de cuarzo) | Curva GEO de la Fig. 4.7 como cota (degradación por contaminación) *(opinión)*, hasta 8 años | Curva de diseño de la Fig. 4.7, hasta 8 años | Sin default |
| Teflon plateado o aluminizado | Curva LEO de la Fig. 4.9, hasta 9 años | Curva GEO de la Fig. 4.9, hasta 9 años | Sin default |
| S13G-LO | Curva S13G de la Fig. 4.10, hasta 9,5 años *(opinión: la fuente no dice la órbita; envuelve LDEF y OTS)* | Ídem | Sin default |
| Familia Z93 (Z-93, Z-93P, AZ-93) | Δα = 0,05 [7] | Curva Z93 de la Fig. 4.10, hasta 10 años *(opinión, ídem)* | Sin default |
| SG121FD | α EOL = 0,48, hasta 7 años [5] | Sin dato | Sin dato |
| PCBE | α EOL = 0,52, hasta 7 años [5] | Sin dato | Sin dato |
| Kapton aluminizado (capa externa de MLI) | Δα = 0,10, hasta 7 años [5] | Curva de la Fig. 4.11, hasta 9,5 años | Sin default |
| Beta cloth | Sin dato numérico | Sin dato numérico | Sin dato |

- **Radiador por defecto según el régimen** *(opinión)*:
  - LEO: Teflon plateado (como propone [balance-global.md](balance-global.md));
  - GEO: OSR, porque el Teflon «prácticamente desapareció» como superficie externa en GEO por lo difícil que es conectarlo a masa [2, cap. 4, p. 159];
  - otra órbita: sin default.

### Datos por recubrimiento

**OSR (espejo de cuarzo plateado):**
- **No lo daña la radiación;** solo la contaminación, que sube mucho α en los primeros años y después poco [2, cap. 4, p. 152].
- **GEO:** curva de diseño recomendada, construida sobre OTS-2, Intelsat IV y IV A, FLTSATCOM, SBX, COMSTAR y SCATHA [2, cap. 4, Fig. 4.7] *(digitalizado, tabla T5)*. Con poca contaminación, el OSR con recubrimiento conductor de SCATHA pasó de 0,08 a 0,10 en 10 años y se estiman 0,11 a los 15 (Δα 0,03) [6, Tabla 6]. La distancia entre las dos fuentes es la contaminación.
- **MEO:** en GPS (órbita circular de 12 h, medición calorimétrica) α sube casi lineal, ~0,065 por año hasta los 2 años [2, Fig. 4.7] *(digitalizado)*. En NTS (1977) el OSR pasó de 0,15 a 0,26 en 337 días [6, Tabla 5]. [6] titula esa tabla «geosynchronous»; por el año sería NTS-2, que voló en órbita de 12 h *(dato no verificado)*. Por la tasa se parece más a GPS que a GEO.
- **LEO:** no encontré datos de α de OSR. Para superficies que solo degrada la contaminación, Gilmore recomienda usar las tasas de los espejos de cuarzo de la Fig. 4.7 [2, cap. 4, p. 154]. En LDEF no hubo impactos sobre OSR [2, cap. 4, p. 151].

**Teflon metalizado (SSM, plateado o aluminizado):**
- **Mecanismo:** daño por partículas cargadas más contaminación; LEO es lo más benigno, GEO más severo y las órbitas de 12 h pueden ser extremas [2, cap. 4, pp. 153–154].
- **Curvas de diseño:** una para LEO y otra para GEO [2, cap. 4, Fig. 4.9] *(digitalizadas, tabla T5)*.
- **Contraste en GEO:** el Ag/FEP de 5 mil de SCATHA pasó de 0,11 a 0,16 en 1 año y a 0,34 en 10, y se estiman 0,36 a los 15 (Δα 0,25) [6, Tabla 6]. A 1 año coincide con la curva GEO (0,059) *(comparación propia)*.
- **Contraste en LEO (THERME, SSO):** tabla T6 [5, Tablas 2 a 7].
  - SSM plateado: +0,021 y +0,040 a los 4,5 años (HELIOS 2A); ITO-SSM plateado: +0,040 y +0,057 a los 5 años (DEMETER).
  - SSM aluminizado: +0,124 en la cara al cénit, +0,090 en la cara a la velocidad y +0,045 en la opuesta a los 7 años (SPOT 5), con α máximo 0,28.
  - La curva LEO de Gilmore da 0,117 a los 7 años *(digitalizado)*: cubre el peor dato de THERME.
- **LDEF:** las mantas de Teflon plateado no degradaron mucho salvo en zonas contaminadas, donde α subió hasta 0,25 en áreas chicas [2, cap. 4, pp. 157–158]. En la cara a la velocidad el oxígeno atómico erosionó ~1 mil, con la caída de ε esperable [2, cap. 4, p. 157].
- **Órbitas de 12 h:**
  - curva «Spacecraft» de GPS: Δα ≈ 0,18 a 1,5 años y 0,22 a 2 años [2, Fig. 4.9] *(digitalizado, dudoso ±0,01)*;
  - NTS: Ag/FEP de 0,08 a 0,26 en 337 días [6, Tabla 5].

**Pintura blanca S13G-LO:**
- **LEO:** en LDEF M0003 (5,8 años, 28,5°) pasó de 0,147 a 0,232 en la cara a la velocidad (blanqueo por oxígeno atómico) y a 0,458 en la opuesta (UV) [2, cap. 4, Tabla 4.4].
- **GEO (OTS):** α ≈ 0,43 a los 500 días, 0,46–0,50 a los 1000 y 0,52–0,57 entre 1700 y 2000 [9, Fig. 5-27] *(lectura visual, ±0,01)*.
- **Órbita de 12 h (Navstar 6):** de 0,20 a ~0,45 en ~180 días [9, Fig. 5-27].
- **Gilmore:** puede pasar de ~0,20 a 0,70 en pocos años [2, cap. 4, p. 154]. Su curva S13G llega a Δα 0,43 [2, Fig. 4.10] *(digitalizado)*, pero no dice la órbita.

**Familia Z93 (óxido de zinc en silicato de potasio):**
- **LEO, en vuelo:**
  - LDEF (5,8 años): de 0,14 a 0,15, y de 0,16 a 0,16 y 0,17 [8];
  - MISSE-2 (~4 años): Z-93 de 0,14 a 0,14 y Z-93P de 0,14 a 0,13–0,14 [8, Tabla 1]; AZ93 de 0,14–0,15 a 0,15–0,16 [8, Tabla 2];
  - con contaminación sube: en POSA-I el Z-93P pasó de 0,16 a 0,23 con ~5000 Å de silicona [8].
- **LEO, modelo:** el de la ISS para 30 años sin desgasificación ni bipropelente da Δα ≈ 0,05 [7, p. 6]. Es el default propuesto.
- **GEO, laboratorio:** UV más electrones simulando GEO dan Δα 0,044–0,050 [7, Tabla 2].
- **GEO, valores de diseño:**
  - GSFC fijó α EOL < 0,45 a 15 años para el Z93C55 conductor (BOL 0,14) [6];
  - el NS43G de SCATHA, otra pintura, tuvo Δα 0,13 estimado a 15 años [6, Tabla 6];
  - la curva Z93 de Gilmore llega a Δα 0,33 a los 10 años [2, Fig. 4.10] *(digitalizado; órbita no indicada)*.
- **Con radiación alta:** Lunar Orbiter V, +0,06 a 1500 ESH; Mariner IV, +0,12 a 3000 ESH [7, p. 6].

**SG121FD y PCBE (pinturas blancas de MAP), solo LEO SSO (THERME):**
- suben fuerte los dos primeros años y después se estabilizan [5, §5.1];
- SG121FD: +0,21 a +0,235 a los 7 años, con α final de 0,43 en las caras laterales y 0,46–0,48 en la del cénit;
- PCBE: +0,20 a +0,27 entre 4,5 y 7 años, con α final de 0,48–0,52 [5];
- el ensayo UV en tierra subestimó mucho la degradación en vuelo de las dos [5, Tabla 9].

**Kapton aluminizado (capa externa de MLI):**
- **LEO (THERME,** Kapton con aluminio en la cara posterior; 50 µm en HELIOS 2A): +0,089 y +0,094 a los 7 años (SPOT 5) y +0,100 a los 4,5 (HELIOS 2A) [5].
- **Oxígeno atómico:** en LDEF erosionó por completo mantas de 5 mil en la cara a la velocidad [2, cap. 4, p. 157]. THERME midió un coeficiente de reacción de 3,0 × 10⁻²⁴ cm³/átomo [5, Tabla 10]. Sin protección, en esa cara el problema es la integridad, no α.
- **GEO:** Δα llega a ~0,37 en tres o cuatro años [2, Fig. 4.11] *(digitalizado)*; el texto dice que se puede volver casi negro [2, cap. 4, p. 154].

**Beta cloth:**
- **No encontré valores numéricos.** Gilmore: casi negro tras varios años en GEO [2, cap. 4, p. 154]. Finckenor y Dooling: amarillea con UV si se procesó con metilsiloxano, y el oxígeno atómico lo blanquea [10, §4.1.1]. En MISSE-5 se oscureció con UV [8].
- La degradación de la capa externa del MLI pesa poco en el balance [2, cap. 4, p. 154].

### Sin respaldo

- α EOL de OSR en LEO (se propone la curva GEO como cota).
- Beta cloth en cualquier órbita; SG121FD y PCBE fuera de LEO.
- MEO a largo plazo: los datos llegan a ~2 años.
- Vidas más largas que las curvas, que llegan a 8 años (Fig. 4.7), 9 (Fig. 4.9) y ~10 (Figs. 4.10 y 4.11). Una misión GEO de 15 años queda sin default salvo con extrapolación (ver Abierto).
- La órbita de la Fig. 4.10 y el tramo de la curva LEO de la Fig. 4.9 por debajo de 3,5 años (dudoso, ver T5).

## 4. Huecos del balance que se cierran con datos

### 4.1 Margen de madurez de la disipación

**Recomendación.**
- **Categoría de madurez por equipo en Equipos,** con los márgenes de ESA: ≥5 % para equipos de catálogo, ≥10 % con modificaciones menores y ≥20 % para equipos nuevos o con rediseño mayor [11, R-P-1].
- **El balance lo aplica solo en los casos calientes.** Los fríos usan la disipación nominal *(opinión: el margen de madurez cubre el crecimiento, que es para un solo lado)*.
- **Sin categoría cargada, 20 %** *(opinión: en fase 0 casi todo es estimación; es el valor de ESA para equipos nuevos)*.

**Datos y práctica.**
- **ESA** [11, §2.4]:
  - los márgenes de madurez de potencia van por equipo y por categoría ECSS (A/B, C, D);
  - aparte, un margen de sistema ≥20 % sobre el presupuesto de potencia (R-P-3), que dimensiona la generación y no la disipación *(opinión)*;
  - para criogenia pide un análisis de sensibilidad con ±30 % en la disipación eléctrica (R-T-3); no es una regla general.
- **ESA, curso de ECSS-E-ST-31:** el caso caliente va con la disipación interna máxima y el frío con la mínima [13, diap. 114].
- **GSFC:**
  - los márgenes de potencia de la Tabla 1.06-1 son de capacidad del sistema de potencia al fin de vida, no de disipación: ≥25 % en pre-fase A, ≥20 % en A, ≥15 % en B, ≥10 % en C y ≥5 % en D [12, Tabla 1.06-1];
  - para el diseño térmico, el margen de temperatura cubre la incertidumbre de la disipación [12, regla 4.25, fundamento].
- **Dos filosofías:** margen explícito de disipación (ESA) o margen de temperatura (GSFC). ESA usa las dos a la vez, porque su filosofía remite los rangos de temperatura a ECSS-E-ST-31C [11, R-T-1]. No hay doble conteo según ESA.
- **El riesgo opuesto:** si la disipación real resulta menor que la máxima esperada, un radiador justo puede quedar sin heaters suficientes en el frío [14, p. 9]. Es otra razón para no sumar margen en los fríos.
- **AIAA S-120A-2015** (crecimiento de masa) y **S-122** (potencia) no se consultaron (sin acceso). GSFC cita la S-120A para el crecimiento de masa [12, Tabla 1.06-1].

### 4.2 Gradiente entre equipos y radiador

**Recomendación.**
- **No hay default con fuente.** Agregar un parámetro opcional `radiator_gradient` (K, default 0) y escribir en la ayuda qué hace.
- **El gradiente real sale de la fase 1,** en `discretization` y `couplings` (tema 2).

**Datos.**
- **No encontré un valor típico de fase 0** en Gilmore (caps. 1–7 y 15), ECSS-E-HB-31-01 partes 9 y 15, el curso de ESA ni el lector de Zandbergen.
- **Lo que hay es cualitativo:** los equipos de alta disipación generan gradientes grandes en paneles de honeycomb, y se resuelven con doublers o heat pipes [2, cap. 6, p. 209]. El ejemplo de la Fig. 6.3 de Gilmore es un caso particular.
- **Sensibilidad** *(cálculo propio, sin ambiente)*: el rechazo cae con T⁴. Con el radiador 5 K más frío que el nodo a 40 °C, la emisión baja ~6 % y el área sube ~7 %; con 10 K, ~14 %.

### 4.3 cp efectivo y cp de la hidracina

**Recomendación.**
- **Regla de mezcla,** exacta para un nodo isotermo: `C = Σ mᵢ·cᵢ`, `cp_eff = C / m`.
- **Default: 900 J/(kg·K) sobre la masa total de Misión** (en órbita al inicio de vida, con propelente) *(opinión)*. Si hay propelente, subestima C. Eso es conservador para los dos usos en el balance: da una τ más corta, que avisa antes, y transitorios con excursiones más grandes.
- **Para refinar, un `propellant_mass` opcional** con `propellant_specific_heat` = 3080 J/(kg·K), la hidracina a 298 K [15]. Ejemplo *(cálculo propio)*: 500 kg con 50 kg de hidracina dan C = 450·900 + 50·3084 ≈ 559 kJ/K, es decir 1120 J/(kg·K), +24 %.
- **La banda de ±30 % sigue siendo opinión.** Los materiales secos de la tabla T8 caen entre ~540 (titanio) y ~1300 (algunos compuestos).

**Datos:** tabla T8.
- **Hidracina:** NIST-JANAF (Chase 1998) da para el líquido una ecuación de Shomate válida entre 298 y 800 K [15]. A 298,15 K da 98,8 J/(mol·K), es decir 3084 J/(kg·K) con M = 32,0452 g/mol *(cálculo propio)*. Por debajo de 298 K es extrapolación. NIST anota que los datos se revisaron por última vez en 1965.
- **Sin fuente:** el cp de la electrónica (placas, componentes) y el cp efectivo de un satélite completo.

### 4.4 90 min como promediado por defecto

**Recomendación:** 90 min (5400 s) como default de Entorno, con el aviso del balance si τ < 90 min *(opinión con respaldo indirecto)*.

**Respaldo y lo que falta.**
- **Respaldo indirecto:**
  - NASA inicializa los perfiles de diseño de la ISS con las condiciones de promedio de 90 min [1, §5.3];
  - descarta los datos promediados por hora o por día porque son largos frente a las constantes de tiempo típicas [1, §4.1];
  - la diferencia entre 2σ y 3,3σ es chica a partir de 90 min [2, cap. 2, p. 30].
- **Encaja con el balance:** usa flujos promediados en la órbita, y 90 min es el orden del período en LEO *(opinión)*.
- **Es conservador para un satélite mediano** (τ de horas): los extremos de 90 min son más amplios que los de 6 h y 24 h [1, Tablas 4.2.3-1 a -3].
- **Lo que no tiene respaldo:** ninguna fuente dice «usar 90 min en la fase 0».

## 5. Umbral de excentricidad de Entorno

**Recomendación.** Mantener 0,01 y quitarle «provisorio» después de la revisión de `physics-reviewer` *(opinión, con el cálculo de abajo)*. Documentar el sesgo: el modelo circular al perigeo es conservador en el caliente y optimista en el frío, en un 2e.

**Cálculo** *(cálculo propio, script en el scratchpad de la sesión)*.
- **Qué hace hoy el proveedor:** modela la órbita circular a la altitud del perigeo, con el período del semieje mayor; el eclipse sale de la geometría circular al perigeo por ese período.
- **Con qué se compara:** con la órbita elíptica real con β = 0, sombra cilíndrica y la línea de ápsides en la dirección del Sol (eclipse máximo centrado en el apogeo).
- **Flujos terrestres:** el promedio temporal de 1/r² en la elipse vale `1 / (a²·√(1 − e²))`.

| Perigeo (km) | e | Apogeo (km) | F circular / F medio | F apogeo / F perigeo | Eclipse del modelo (min) | Eclipse máximo real (min) | Error |
|---|---|---|---|---|---|---|---|
| 600 | 0,005 | 670 | 1,010 | 0,980 | 35,76 | 35,55 | +0,6 % |
| 600 | 0,01 | 741 | 1,020 | 0,961 | 36,03 | 35,63 | +1,1 % |
| 600 | 0,02 | 885 | 1,041 | 0,923 | 36,58 | 35,80 | +2,2 % |
| 600 | 0,05 | 1335 | 1,107 | 0,819 | 38,33 | 36,48 | +5,1 % |
| 20 000 | 0,01 | 20 533 | 1,020 | 0,961 | 56,08 | 56,06 | 0,0 % |
| 35 786 | 0,01 | 36 638 | 1,020 | 0,961 | 70,47 | 70,46 | 0,0 % |

**Lectura.**
- **Flujos terrestres:** el modelo sobreestima el promedio en ~2e (2 % con e = 0,01). Es conservador en el caliente y optimista en el frío. En el apogeo, el flujo instantáneo es ~4e menor que en el perigeo.
- **Eclipse:** el modelo da un eclipse algo más largo que el real (+1 % con e = 0,01, 0,4 % de la órbita).
- **Frente a los datos:** la incertidumbre de medición de la OLR es de ~5 W/m² (~2 %) y la del albedo ~0,02 [1, §5.1]. Con e = 0,01 el error geométrico no supera la incertidumbre de los datos; con 0,02 ya la duplica.
- **Si hiciera falta admitir hasta e ≈ 0,05:** sumar la altitud del apogeo como otro extremo geométrico de las condiciones, como `eol_altitude`. El frío usaría el apogeo (circular al apogeo subestima el promedio en ~2e, conservador) *(opinión)*.

## Tablas listas para cargar

Unidades SI: albedo como fracción (adimensional), OLR en W/m², tiempos en s, Δα adimensional, cp en J/(kg·K).

### T1. Albedo e IR terrestre, pares de diseño (NASA/TM-2001-211221)

- **3,3σ** (percentiles 0,04 y 99,96): [1, Tablas 4.2.3-1 (baja), 4.2.3-2 (media) y 4.2.3-3 (alta)], iguales a [2, cap. 2, Tablas 2.1 (frío) y 2.2 (caliente)].
- **2σ** (percentiles 5 y 95): [1, Tabla A-1], igual a [2, cap. 2, Tablas 2.3 (frío) y 2.4 (caliente)]. NASA rotula las columnas de la A-1 «30 deg», «60 deg» y «90 deg»; Gilmore, «30», «60» y «90». Corresponden a las tres bandas.
- **Referencia:** valores al tope de la atmósfera (R_E + 30 km), albedo referido a SZA = 0 (sumar la corrección de T3).
- **Medias de cada banda** [1]: albedo 0,18, 0,22 y 0,23; OLR 246, 234 y 211 W/m² (baja, media y alta).
- **\*** En la banda alta, caso caliente de extremo de OLR, 6 h y 24 h: incluyen datos del lado nocturno y pueden subestimar en ~15 W/m² el máximo de una SSO siempre iluminada [1, nota de la Tabla 4.2.3-3]. Gilmore indica sumar ~15 W/m² con β > 80° [2, cap. 2, Tablas 2.2 y 2.4, nota c].

#### 3,3σ, banda baja (0° a 30°)

| Promediado | Tiempo (s) | Frío · albedo mín.: a | OLR (W/m²) | Frío · combinado: a | OLR (W/m²) | Frío · OLR mín.: a | OLR (W/m²) | Caliente · albedo máx.: a | OLR (W/m²) | Caliente · combinado: a | OLR (W/m²) | Caliente · OLR máx.: a | OLR (W/m²) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 16 s | 16 | 0,06 | 273 | 0,13 | 225 | 0,40 | 150 | 0,43 | 182 | 0,30 | 298 | 0,22 | 331 |
| 128 s | 128 | 0,06 | 273 | 0,13 | 226 | 0,38 | 154 | 0,42 | 181 | 0,29 | 295 | 0,22 | 326 |
| 896 s | 896 | 0,07 | 265 | 0,14 | 227 | 0,33 | 173 | 0,37 | 219 | 0,28 | 291 | 0,22 | 318 |
| 30 min | 1800 | 0,08 | 261 | 0,14 | 228 | 0,30 | 188 | 0,33 | 219 | 0,26 | 284 | 0,17 | 297 |
| 90 min | 5400 | 0,11 | 258 | 0,14 | 228 | 0,25 | 206 | 0,28 | 237 | 0,24 | 275 | 0,20 | 285 |
| 6 h | 21600 | 0,14 | 245 | 0,16 | 232 | 0,19 | 224 | 0,23 | 248 | 0,21 | 264 | 0,19 | 269 |
| 24 h | 86400 | 0,16 | 240 | 0,16 | 235 | 0,18 | 230 | 0,22 | 251 | 0,20 | 260 | 0,19 | 262 |

#### 3,3σ, banda media (más de 30° a 60°)

| Promediado | Tiempo (s) | Frío · albedo mín.: a | OLR (W/m²) | Frío · combinado: a | OLR (W/m²) | Frío · OLR mín.: a | OLR (W/m²) | Caliente · albedo máx.: a | OLR (W/m²) | Caliente · combinado: a | OLR (W/m²) | Caliente · OLR máx.: a | OLR (W/m²) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 16 s | 16 | 0,06 | 273 | 0,15 | 213 | 0,40 | 151 | 0,48 | 180 | 0,31 | 267 | 0,21 | 332 |
| 128 s | 128 | 0,06 | 273 | 0,15 | 213 | 0,38 | 155 | 0,47 | 180 | 0,30 | 265 | 0,22 | 331 |
| 896 s | 896 | 0,08 | 262 | 0,17 | 217 | 0,34 | 163 | 0,36 | 192 | 0,28 | 258 | 0,22 | 297 |
| 30 min | 1800 | 0,12 | 246 | 0,18 | 217 | 0,27 | 176 | 0,34 | 205 | 0,28 | 261 | 0,21 | 282 |
| 90 min | 5400 | 0,16 | 239 | 0,19 | 218 | 0,30 | 200 | 0,31 | 204 | 0,26 | 257 | 0,22 | 274 |
| 6 h | 21600 | 0,18 | 238 | 0,19 | 221 | 0,31 | 207 | 0,31 | 212 | 0,24 | 248 | 0,21 | 249 |
| 24 h | 86400 | 0,19 | 233 | 0,20 | 223 | 0,25 | 210 | 0,28 | 224 | 0,24 | 247 | 0,21 | 245 |

#### 3,3σ, banda alta (más de 60°)

| Promediado | Tiempo (s) | Frío · albedo mín.: a | OLR (W/m²) | Frío · combinado: a | OLR (W/m²) | Frío · OLR mín.: a | OLR (W/m²) | Caliente · albedo máx.: a | OLR (W/m²) | Caliente · combinado: a | OLR (W/m²) | Caliente · OLR máx.: a | OLR (W/m²) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 16 s | 16 | 0,06 | 273 | 0,16 | 212 | 0,40 | 108 | 0,50 | 180 | 0,32 | 263 | 0,22 | 332 |
| 128 s | 128 | 0,06 | 273 | 0,16 | 212 | 0,38 | 111 | 0,49 | 184 | 0,31 | 262 | 0,22 | 331 |
| 896 s | 896 | 0,09 | 264 | 0,17 | 218 | 0,33 | 148 | 0,35 | 202 | 0,28 | 259 | 0,20 | 294 |
| 30 min | 1800 | 0,13 | 246 | 0,18 | 218 | 0,31 | 175 | 0,33 | 204 | 0,27 | 260 | 0,20 | 284 |
| 90 min | 5400 | 0,16 | 231 | 0,19 | 218 | 0,26 | 193 | 0,28 | 214 | 0,26 | 244 | 0,22 | 250 |
| 6 h | 21600 | 0,18 | 231 | 0,20 | 224 | 0,27 | 202 | 0,27 | 218 | 0,24 | 233 | 0,22 | 221* |
| 24 h | 86400 | 0,18 | 231 | 0,20 | 224 | 0,24 | 205 | 0,24 | 224 | 0,23 | 232 | 0,20 | 217* |

#### 2σ, banda baja (0° a 30°)

| Promediado | Tiempo (s) | Frío · albedo mín.: a | OLR (W/m²) | Frío · combinado: a | OLR (W/m²) | Frío · OLR mín.: a | OLR (W/m²) | Caliente · albedo máx.: a | OLR (W/m²) | Caliente · combinado: a | OLR (W/m²) | Caliente · OLR máx.: a | OLR (W/m²) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 16 s | 16 | 0,09 | 270 | 0,15 | 236 | 0,30 | 195 | 0,29 | 205 | 0,21 | 260 | 0,17 | 285 |
| 128 s | 128 | 0,09 | 267 | 0,16 | 237 | 0,29 | 198 | 0,29 | 211 | 0,21 | 260 | 0,17 | 284 |
| 896 s | 896 | 0,10 | 261 | 0,16 | 237 | 0,26 | 209 | 0,26 | 225 | 0,21 | 261 | 0,18 | 279 |
| 30 min | 1800 | 0,12 | 257 | 0,16 | 237 | 0,23 | 216 | 0,24 | 234 | 0,21 | 258 | 0,18 | 274 |
| 90 min | 5400 | 0,13 | 249 | 0,16 | 237 | 0,20 | 225 | 0,22 | 246 | 0,20 | 258 | 0,19 | 268 |
| 6 h | 21600 | 0,15 | 241 | 0,17 | 237 | 0,18 | 231 | 0,20 | 252 | 0,19 | 255 | 0,19 | 261 |
| 24 h | 86400 | 0,16 | 240 | 0,17 | 236 | 0,17 | 233 | 0,20 | 252 | 0,19 | 257 | 0,18 | 258 |

#### 2σ, banda media (más de 30° a 60°)

| Promediado | Tiempo (s) | Frío · albedo mín.: a | OLR (W/m²) | Frío · combinado: a | OLR (W/m²) | Frío · OLR mín.: a | OLR (W/m²) | Caliente · albedo máx.: a | OLR (W/m²) | Caliente · combinado: a | OLR (W/m²) | Caliente · OLR máx.: a | OLR (W/m²) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 16 s | 16 | 0,10 | 267 | 0,19 | 227 | 0,33 | 183 | 0,36 | 201 | 0,23 | 240 | 0,17 | 280 |
| 128 s | 128 | 0,10 | 265 | 0,19 | 227 | 0,33 | 184 | 0,35 | 202 | 0,23 | 240 | 0,17 | 279 |
| 896 s | 896 | 0,13 | 252 | 0,20 | 226 | 0,28 | 189 | 0,29 | 213 | 0,23 | 241 | 0,18 | 264 |
| 30 min | 1800 | 0,16 | 242 | 0,20 | 225 | 0,25 | 200 | 0,27 | 223 | 0,23 | 240 | 0,20 | 258 |
| 90 min | 5400 | 0,18 | 238 | 0,20 | 225 | 0,23 | 209 | 0,26 | 229 | 0,23 | 241 | 0,21 | 254 |
| 6 h | 21600 | 0,19 | 233 | 0,20 | 226 | 0,23 | 212 | 0,25 | 231 | 0,23 | 242 | 0,21 | 242 |
| 24 h | 86400 | 0,19 | 235 | 0,20 | 226 | 0,23 | 212 | 0,25 | 232 | 0,23 | 241 | 0,21 | 241 |

#### 2σ, banda alta (más de 60°)

| Promediado | Tiempo (s) | Frío · albedo mín.: a | OLR (W/m²) | Frío · combinado: a | OLR (W/m²) | Frío · OLR mín.: a | OLR (W/m²) | Caliente · albedo máx.: a | OLR (W/m²) | Caliente · combinado: a | OLR (W/m²) | Caliente · OLR máx.: a | OLR (W/m²) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 16 s | 16 | 0,10 | 267 | 0,20 | 225 | 0,35 | 164 | 0,38 | 197 | 0,24 | 237 | 0,17 | 280 |
| 128 s | 128 | 0,10 | 265 | 0,20 | 225 | 0,34 | 164 | 0,37 | 199 | 0,24 | 238 | 0,17 | 279 |
| 896 s | 896 | 0,14 | 252 | 0,20 | 227 | 0,27 | 172 | 0,28 | 213 | 0,23 | 240 | 0,18 | 263 |
| 30 min | 1800 | 0,17 | 244 | 0,20 | 226 | 0,25 | 190 | 0,26 | 223 | 0,23 | 242 | 0,20 | 258 |
| 90 min | 5400 | 0,18 | 230 | 0,21 | 224 | 0,24 | 202 | 0,24 | 219 | 0,23 | 232 | 0,21 | 242 |
| 6 h | 21600 | 0,19 | 230 | 0,21 | 226 | 0,23 | 205 | 0,23 | 224 | 0,22 | 230 | 0,21 | 216* |
| 24 h | 86400 | 0,19 | 230 | 0,20 | 225 | 0,23 | 207 | 0,23 | 224 | 0,23 | 230 | 0,21 | 215* |

### T2. Constante solar

| Parámetro | Valor | Unidad | Fuente |
|---|---|---|---|
| Irradiancia solar total a 1 UA | 1361 | W/m² | [3, §6.1.2.1, Tabla 6-2] |
| Incertidumbre (1σ) | 0,5 | W/m² | [3, §6.1.2.1] |
| Afelio (para test) | 1316 | W/m² | [3, Tabla 6-2] |
| Perihelio (para test) | 1407 | W/m² | [3, Tabla 6-2] |

### T3. Corrección del albedo por ángulo cenital solar (NASA/TM-2001-211221)

Polinomio, SZA θ en grados, albedo como fracción: `a(θ) = a(θ = 0) + C4·θ⁴ + C3·θ³ + C2·θ² + C1·θ` [1, §4.2.1, p. 6].

| Coeficiente | Valor |
|---|---|
| C4 | +4,9115 × 10⁻⁹ |
| C3 | +6,0372 × 10⁻⁸ |
| C2 | −2,1793 × 10⁻⁵ |
| C1 | +1,3798 × 10⁻³ |

Corrección del albedo medio orbital [1, Tabla 4.2.1-1] y medio de pulsos desde el mediodía solar en una órbita de 5400 s [1, Tabla A-2]. Si se usa la corrección instantánea, estas tablas sirven solo de test. Gilmore reproduce la columna orbital y la de 128 s (como «posición desde el punto subsolar»), sin 10° ni 30° [2, cap. 2, Tablas 2.1–2.4].

| β (°) | Promedio orbital ⟨c⟩ | Pulso 128 s | Pulso 448 s | Pulso 896 s | Pulso ≥ 1350 s |
|---|---|---|---|---|---|
| 0 | 0,04 | 0,01 | 0,02 | 0,03 | 0,04 |
| 10 | 0,04 | 0,01 | 0,02 | 0,03 | 0,04 |
| 20 | 0,05 | 0,02 | 0,02 | 0,04 | 0,05 |
| 30 | 0,06 | 0,03 | 0,03 | 0,04 | 0,06 |
| 40 | 0,07 | 0,04 | 0,04 | 0,05 | 0,07 |
| 50 | 0,09 | 0,05 | 0,06 | 0,07 | 0,09 |
| 60 | 0,12 | 0,08 | 0,09 | 0,10 | 0,12 |
| 70 | 0,16 | 0,13 | 0,13 | 0,15 | 0,16 |
| 80 | 0,22 | 0,20 | 0,21 | 0,22 | 0,22 |
| 90 | 0,31 | 0,31 | 0,31 | 0,31 | 0,31 |

### T4. Bandas de inclinación

| Banda | Latitud máxima `mín(i, 180° − i)` | Fuente |
|---|---|---|
| Baja | 0° a 30° | [1, §4.2.2] |
| Media | más de 30° a 60° | [1, §4.2.2] |
| Alta | más de 60° | [1, §4.2.2]; aplicar a retrógradas por latitud *(opinión)* |

### T5. Curvas de degradación Δα(t) *(digitalizadas)*

Tiempo en años. Δα es el aumento sobre el BOL de cada muestra. Interpolar linealmente; fuera del rango, sin default.

**T5-a. OSR, curva de diseño GEO** [2, cap. 4, Fig. 4.7] (incertidumbre ±0,003):

| t (años) | 0 | 0,5 | 1 | 1,5 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Δα | 0 | 0,026 | 0,045 | 0,062 | 0,076 | 0,096 | 0,112 | 0,127 | 0,142 | 0,158 | 0,173 |

**T5-b. Teflon metalizado, curva de diseño GEO** [2, cap. 4, Fig. 4.9] (±0,003):

| t (años) | 0 | 0,5 | 1 | 1,5 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Δα | 0 | 0,032 | 0,059 | 0,082 | 0,101 | 0,130 | 0,151 | 0,168 | 0,182 | 0,194 | 0,206 | 0,219 |

**T5-c. Teflon metalizado, curva de diseño LEO** [2, cap. 4, Fig. 4.9] (±0,003 desde 4 años). Entre 0 y 3,5 años la curva corre dentro de un haz de líneas y no se pudo separar con certeza: se dan los valores de la candidata más alta, conservadores, marcados como **dudosos**.

| t (años) | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| Δα | 0 | 0,027 (dudoso) | 0,048 (dudoso) | 0,063 (dudoso) | 0,077 | 0,093 | 0,106 | 0,117 | 0,124 | 0,128 |

**T5-d. S13G** [2, cap. 4, Fig. 4.10], órbita no indicada en la fuente (±0,005; 0,5 años dudoso por el cruce con la curva del aluminio laminar):

| t (años) | 0 | 0,5 | 1 | 1,5 | 2 | 2,5 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 9,5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Δα | 0 | 0,083 | 0,168 | 0,235 | 0,287 | 0,328 | 0,358 | 0,391 | 0,410 | 0,420 | 0,424 | 0,430 | 0,431 | 0,431 |

**T5-e. Z93** [2, cap. 4, Fig. 4.10], órbita no indicada (±0,005; 1 y 2 años leídos a ojo, dudosos ±0,01):

| t (años) | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Δα | 0 | 0,045 (dudoso) | 0,10 (dudoso) | 0,152 | 0,202 | 0,238 | 0,265 | 0,287 | 0,303 | 0,316 | 0,326 |

**T5-f. Kapton aluminizado de 2 mil, GEO** [2, cap. 4, Fig. 4.11 y p. 154] (±0,005):

| t (años) | 0 | 0,5 | 1 | 1,5 | 2 | 2,5 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 9,5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Δα | 0 | 0,147 | 0,233 | 0,283 | 0,313 | 0,331 | 0,343 | 0,355 | 0,360 | 0,362 | 0,363 | 0,364 | 0,367 | 0,367 |

**T5-g. Órbitas de 12 h (GPS), solo informativo** [2, cap. 4, Figs. 4.7 y 4.9] *(dudoso ±0,01)*:

| t (años) | 0,5 | 1 | 1,5 | 2 |
|---|---|---|---|---|
| OSR (calorimétrico), Δα | 0,035 | 0,065 | 0,095 | 0,124 |
| Teflon (curva «Spacecraft»), Δα | 0,07 | — | 0,18 | 0,22 |

### T6. Datos de vuelo de degradación

THERME [5, Tablas 2 a 7]. Las tres órbitas son SSO: SPOT 5 a 820 km y 98,7° (7 años); HELIOS 2A en LEO por debajo de SPOT 5 (4,5 años); DEMETER a 710 km y 98,2° (5 años). Caras: cénit; V+, que recibe oxígeno atómico; V−, sin oxígeno atómico. La cara a la Tierra se descartó por incertidumbre.

| Recubrimiento | Satélite | α BOL en tierra | α inicial en vuelo (cénit / V+ / V−) | Δα (cénit / V+ / V−) |
|---|---|---|---|---|
| SSM aluminizado | SPOT 5 | 0,11 ± 0,04 | 0,15 (fijado) / 0,15 / 0,15 | +0,124 / +0,090 / +0,045 |
| SSM aluminizado | HELIOS 2A | 0,11 ± 0,04 | 0,14 / 0,15 / — | +0,091 / +0,035 / — |
| SSM plateado | HELIOS 2A | 0,09 ± 0,04 | — / 0,10 / 0,10 | — / +0,021 / +0,040 |
| ITO-SSM plateado | DEMETER | 0,11 ± 0,02 | — / 0,14 / 0,15 | — / +0,040 / +0,057 |
| SG121FD | SPOT 5 | 0,19 ± 0,04 | 0,22 / 0,21 / 0,22 | +0,235 / +0,224 / +0,210 |
| SG121FD | HELIOS 2A | 0,24 ± 0,02 | 0,25 / — / — | +0,230 / — / — |
| PCBE | SPOT 5 | 0,20 ± 0,04 | 0,25 / — / — | +0,267 / — / — |
| PCBE | HELIOS 2A | 0,22 ± 0,02 | 0,23 / — / — | +0,265 / — / — |
| PCBE | DEMETER | 0,27 ± 0,04 | — / 0,24 / 0,27 | — / +0,235 / +0,201 |
| SCK5 | DEMETER | 0,27 ± 0,04 | — / 0,33 / 0,35 | — / +0,062 / +0,097 |
| Kapton | SPOT 5 | 0,34 ± 0,04 | — / 0,31 / 0,34 | — / +0,089 / +0,094 |
| Kapton (50 µm) | HELIOS 2A | 0,36 ± 0,02 | — / — / 0,38 | — / — / +0,100 |
| Mapatox K sobre Kapton | SPOT 5 | 0,36 ± 0,04 | — / 0,33 / 0,37 | — / +0,083 / +0,091 |
| Mapatox K sobre Kapton | HELIOS 2A | 0,40 ± 0,02 | — / 0,34 / 0,40 | — / +0,070 / +0,080 |

GEO y 12 h [6, Tablas 5 y 6]:

| Experimento | Recubrimiento | α BOL | α intermedio | α final | Δα |
|---|---|---|---|---|---|
| SCATHA (1979), cuasi GEO | OSR/CC | 0,08 | 0,08 (1 año); 0,10 (10 años) | 0,11 (15 años, estimado) | 0,03 |
| SCATHA | Ag/FEP 5 mil | 0,11 | 0,16 (1 año); 0,34 (10 años) | 0,36 (15 años, estimado) | 0,25 |
| SCATHA | NS43G | 0,31 | 0,36 (1 año); 0,43 (10 años) | 0,44 (15 años, estimado) | 0,13 |
| NTS (1977), ver nota de órbita en la sección 3 | OSR/CC | 0,15 | 0,16 (40 días) | 0,26 (337 días) | 0,11 |
| NTS | Ag/FEP 5 mil | 0,08 | 0,14 (40 días) | 0,26 (337 días) | 0,18 |
| NTS | NS43C | 0,18 | 0,28 (40 días) | 0,51 (337 días) | 0,33 |

LDEF M0003, 5,8 años, 465 km a 28,5° [2, cap. 4, Tabla 4.4]:

| Pintura | α inicial | α cara a la velocidad | α cara opuesta |
|---|---|---|---|
| YB-71 | 0,130 | 0,182 | 0,182 |
| A276 | 0,282 | 0,228 | 0,552 |
| S13GLO | 0,147 | 0,232 | 0,458 |
| D111 (negra) | 0,971 | 0,933 | 0,968 |

### T7. Márgenes de madurez de la disipación

| Categoría (ECSS) | Descripción | Margen mínimo | Fuente |
|---|---|---|---|
| A / B | Equipo de catálogo | 5 % | [11, R-P-11] |
| C | Equipo de catálogo con modificaciones menores | 10 % | [11, R-P-12] |
| D | Equipo nuevo, o con modificaciones mayores o rediseño | 20 % | [11, R-P-13] |
| — (sistema, solo presupuesto de potencia) | Margen de sistema sobre la potencia nominal | 20 % | [11, R-P-3] |

### T8. Calor específico

| Material | cp (J/(kg·K)) | Temperatura | Fuente |
|---|---|---|---|
| Aluminio | ~900 (lectura de figura: 880–900) | 300 K | [16, Fig. 4-1] |
| Ti-6Al-4V | ~530–560 (lectura de figura) | ~300 K | [16, Fig. 4-68] |
| Epoxi + vidrio E unidireccional | 850 | 290 K | [16, Tabla 5-8] |
| Epoxi + Kevlar 49 unidireccional | 1120 | 300 K | [16, Tabla 5-8] |
| Tejido de carbono (Narmco 4047) | 1200 | 290 K | [16, Tabla 5-8] |
| Fibra P75 (matriz no identificada, 60 %) | 1300 | 290 K | [16, Tabla 5-8] |
| Fibra P75 en aluminio / SiC / grafito | 920 / 750 / 790 | 290 K | [16, Tabla 5-8] |
| Tejido de cuarzo (Narmco 4033 / 4065) | 1000 / 1300 | 290 K | [16, Tabla 5-8] |
| Hidracina líquida | 3073 / **3084** / 3119 / 3143 | 293 / **298,15** / 313 / 323 K | [15], Shomate de Chase (1998) *(cálculo propio con M = 32,0452 g/mol; fuera de 298–800 K es extrapolación)* |

Shomate de la hidracina líquida [15]: `Cp = A + B·t + C·t² + D·t³ + E/t²` (J/(mol·K)), `t = T/1000`, con A = 48,17750, B = 170,4860, C = −100,8340, D = 45,11350 y E = 0,674292.

## Propuesta de cambios

Coherente con el [ADR 0021](../adr/0021-etapas-de-calculo.md): parámetros como formulario, defaults de biblioteca con procedencia que se resuelven al actualizar, y el resultado informa valor y fuente. También con el [ADR 0023](../adr/0023-orbita-y-actitud-en-entorno.md): la órbita está en Entorno, así que banda y defaults se validan en seco dentro del mismo formulario.

### Entorno: `EnvironmentParameters` v3 y proveedor versión 2

**Valores de diseño** (`design_values`):

| Campo | Tipo | Unidad | Default | Fuente del default |
|---|---|---|---|---|
| `solar_constant` | `float` | W/m² | 1361 | [3, Tabla 6-2] (cambia el texto de la fuente) |
| `averaging_time` | `enum AveragingTime` (16 s, 128 s, 896 s, 30 min, 90 min, 6 h, 24 h) | s | 90 min | *(opinión)*; [1, §5.3] |
| `extreme_level` | `enum ExtremeLevel` (`percentile_0_04`, «3,3σ»; `percentile_5`, «2σ») | — | 3,3σ | [1, §4.2.3] |
| `earth_pairs` | seis pares opcionales `{albedo, olr}`: `cold_albedo`, `cold_combined`, `cold_olr`, `hot_albedo`, `hot_combined`, `hot_olr` | —, W/m² | Vacío: tabla según banda × tiempo × nivel | [1, Tablas 4.2.3-1 a -3 y A-1] |
| `albedo_sza_correction` | `bool` | — | sí | [1, §4.2.1] |

- **Salen** `albedo_min`, `albedo_max`, `olr_min` y `olr_max`.
- **Biblioteca:** `EARTH_RADIATION_PAIRS`, indexada por (nivel, banda, tiempo, lado, tipo), con la tabla de origen como texto de fuente. `design_value_band` pasa a decidir por latitud máxima.
- **Validación:**
  - albedo entre 0 y 1 y OLR > 0 en cada par;
  - desaparece la regla de orden mínimo ≤ máximo, porque los pares no son extremos ordenados;
  - opcional: avisar si el par caliente de un tipo es menos severo que el frío del mismo tipo *(opinión)*.
- **Migración v2 → v3:** los valores cargados a mano pasan a los seis pares (frío: `albedo_min` con `olr_min`; caliente: `albedo_max` con `olr_max`), y así los resultados no cambian. Los vacíos siguen vacíos y toman la tabla nueva al actualizar.

**Proveedor:**
- albedo instantáneo `S·(a + c(θ))·F·cos θ` en cada muestra, si `albedo_sza_correction`;
- R_E + 30 km en los factores de vista de albedo e IR *(opinión)*;
- +15 W/m² en las condiciones con |β| > 80° (banda alta, extremo de OLR caliente, 6 h y 24 h);
- sube `PROVIDER_VERSION`.

**Resultado:**
- `DesignValuesUsed` informa banda, tiempo, nivel y los seis pares con su fuente.
- `fluxes` y `orbit_profiles` dan el solar con la irradiancia mínima y la máxima, y el albedo y la IR por par: frío con la irradiancia mínima y los tres pares fríos, caliente con la máxima y los tres calientes.
- `ranges` informa mínimo y máximo de albedo y OLR sobre los seis pares, solo como información.

**Documentación:**
- en [environment.md](../etapas/environment.md): quitar el aviso «Provisorio» de la tabla y la constante solar, cerrar los puntos de «Abierto» sobre tablas y tiempo de promediado, y documentar el sesgo de la excentricidad;
- en [balance-global.md](balance-global.md): marcar como resueltos los puntos abiertos 4, 10, 11 y 12.

### Balance global

**Casos:** cada candidato caliente se evalúa con los tres pares calientes y cada frío con los tres fríos; se queda el peor. Multiplica las evaluaciones por 3, que siguen costando milisegundos.

**Recubrimientos:**
- `RadiatorCoating`: `silvered_teflon`, `aluminized_teflon`, `osr`, `s13g_lo`, `z93`, `sg121fd`, `pcbe`, `custom`.
- `OuterLayer`: `aluminized_kapton`, `beta_cloth`, `custom`.
- Cada preset lleva α BOL (rango), ε y una curva Δα por régimen, de la tabla T5, o un valor fijo de las T6. `absorptance_eol` vacío se resuelve con `α_BOL,máx + Δα(design_life)` si hay curva para el régimen y la vida; si no, problema `required` con el motivo.

**Régimen:** derivado del resultado de Entorno (tipo y altitudes); el umbral de LEO, 1000 km, es una constante con nombre.

**Default del radiador:** `silvered_teflon` en LEO, `osr` en GEO; en otra órbita, obligatorio *(opinión)*.

**Disipación:**
- en Equipos, campo por equipo `maturity` (`off_the_shelf`, `modified`, `new`), vacío = `new`;
- los márgenes de T7 como constantes con cita en `hestia_core`;
- el balance los aplica en los casos calientes e informa la disipación nominal y la usada.

**Modelo térmico:**
- `effective_specific_heat` 900 sobre la masa de Misión;
- opcionales `propellant_mass` y `propellant_specific_heat` (3080);
- aviso si τ es menor que el tiempo de promediado de Entorno.

**Gradiente:** `radiator_gradient` opcional, 0 K.

## Lo que queda abierto

Cada punto con mi recomendación; decidir antes de especificar.

1. **Pares en Entorno.** Recomendado: los seis pares, evaluados en el balance. Alternativa: seguir con mínimo y máximo independientes, más simple y conservador (+4 a +9 % en caliente, −10 a −13 % en frío, según el ejemplo de la sección 1).
2. **Tiempo de promediado.** Recomendado: parámetro con default 90 min. Alternativas:
   - 6 h, que es más «justo» para τ de horas pero optimista si τ es menor;
   - derivarlo de τ, imposible porque Entorno corre antes que el balance.
3. **2σ en la interfaz.** Recomendado: ofrecerlo con 3,3σ por defecto y una nota de que es para sensibilidad.
4. **Banda de las SSO por latitud máxima** (cae en la alta). Recomendado: sí. Alternativa: tratar las retrógradas como banda alta sin más, que da lo mismo para las SSO bajas.
5. **R_E + 30 km en los factores de vista terrestres.** Recomendado: sí (efecto < 1 %).
6. **Corrección SZA instantánea por defecto.** Recomendado: sí. Alternativa: apagada por defecto, como en las especificaciones de la ISS [1, §5.3], que es más conservadora en el caliente y menos en el frío.
7. **+15 W/m² con β > 80° en la banda alta.** Recomendado: sí, por condición.
8. **α BOL que se suma al Δα.** Recomendado: el máximo del rango. Alternativa: el típico, que es menos conservador.
9. **Vidas más largas que las curvas** (GEO de 15 años). Recomendado: α EOL obligatorio, con el dato de SCATHA a 15 años citado en el mensaje. Alternativa: extrapolar con la pendiente final. Para el Teflon daría ~0,30 a 15 años, frente a 0,25 medido en SCATHA, pero no tiene fuente.
10. **OSR en LEO con la curva GEO como cota.** Recomendado: sí, con aviso «sin datos LEO». Alternativa: obligatorio.
11. **Beta cloth sin default de α EOL.** Recomendado: sí (no hay dato).
12. **Margen de madurez.**
    - Dónde: por equipo en Equipos (recomendado), global en el balance, o no aplicarlo.
    - Default sin categoría: 20 % (recomendado) o 0 %.
    - Solo en calientes: recomendado.
13. **Gradiente equipo–radiador.** Recomendado: parámetro opcional con 0 K y revisarlo en el tema 2. Alternativa: un default sin fuente, por ejemplo 5 K; no lo recomiendo.
14. **cp.** Recomendado: 900 sobre la masa total y propelente opcional. Alternativa: pedir masa seca y propelente en Misión.
15. **Excentricidad.** Recomendado: 0,01 y documentar el sesgo. Alternativa: sumar el apogeo como condición y subir a 0,05.

## Supuestos de física para `physics-reviewer`

1. **Un par por caso para toda la envolvente:** el par describe la escena terrestre, así que todas las caras ven el mismo par en un caso. Se aplica el mismo par a toda la órbita, como en el método de promedio de NASA.
2. **Corrección SZA en el punto subsatelital** aplicada a todo el casquete visible con `F·cos θ`. NASA ajustó el polinomio para TRASYS, Thermal Desktop y TSS, que integran sobre el casquete [1, §4.2.1]. Verificar el oráculo de la Tabla 4.2.1-1 con tolerancia 0,006 y la diferencia cerca del terminador.
3. **R_E + 30 km en los factores de vista y R_E en el eclipse:** consistencia geométrica.
4. **Banda por latitud máxima** para órbitas retrógradas.
5. **β > 80°:** +15 W/m² solo en las combinaciones que marca la fuente, por condición.
6. **Δα:** interpolación lineal en curvas cóncavas, que subestima < 0,003 entre puntos; `α_BOL,máx + Δα`; curvas medidas sobre su propio BOL.
7. **Régimen:** el umbral de 1000 km y qué pasa entre LEO y GEO.
8. **Margen de madurez solo en calientes;** que no rompa la búsqueda del peor caso.
9. **Regla de mezcla del cp** y extrapolación de la Shomate de la hidracina por debajo de 298 K.
10. **Excentricidad:** las fórmulas (`⟨1/r²⟩ = 1 / (a²·√(1 − e²))`), la geometría del eclipse centrado en el apogeo y la conclusión sobre el umbral.
11. **Digitalización:** revisar al azar algunos valores de la tabla T5 contra las figuras (páginas 152–155 de Gilmore cap. 4) y el tramo dudoso de la curva LEO del Teflon.
12. **Orden de magnitud en GEO:** que el factor de vista ~0,023 haga despreciable la elección de banda y tiempo.

## Fuentes

**Consultadas** (copias en `docs/investigacion/fuentes/`)

1. Anderson, B. J., Justus, C. G. y Batts, G. W. *Guidelines for the Selection of Near-Earth Thermal Environment Parameters for Spacecraft Design*. NASA/TM-2001-211221, Marshall Space Flight Center, octubre de 2001. Usadas: §2, §3.1 (constante solar), §3.2, §3.4.1 (tope de la atmósfera), §4.1, §4.2.1 (corrección SZA, polinomio p. 6, Tabla 4.2.1-1 p. 7), §4.2.2, §4.2.3 (Tablas 4.2.3-1 a 4.2.3-3, pp. 15–17), §5.1, §5.3, Apéndice (Tablas A-1 y A-2, pp. 23–24). <https://ntrs.nasa.gov/citations/20020004360>. Local: `fuentes/nasa/NASA-TM-2001-211221-albedo-ir.pdf`.
2. Gilmore, D. G. (ed.). *Spacecraft Thermal Control Handbook, Volume I: Fundamental Technologies*, 2.ª ed. The Aerospace Press / AIAA, El Segundo, 2002. Usados:
   - cap. 2, Clawson et al., «Spacecraft Thermal Environments», pp. 22–31: constante solar (p. 22), radio de 6408 km (p. 25), Tablas 2.1 a 2.4 (pp. 26–29) y discusión (pp. 30–31);
   - cap. 4, Gilmore, Stuckey y Fong, «Thermal Surface Finishes», pp. 150–159: Figs. 4.7 (p. 152), 4.9 (p. 153), 4.10 (p. 154) y 4.11 (p. 155), Tabla 4.4 (p. 156), LDEF (pp. 155–158) y conexión a masa (p. 159);
   - cap. 6, Gilmore, «Radiators», p. 209.

   Local: `fuentes/gilmore-2ed/` (`capitulos/ch02.pdf`, `ch04.pdf`, `ch06.pdf`).
3. ECSS-E-ST-10-04C Rev.1. *Space engineering — Space environment*. ECSS Secretariat, ESA-ESTEC, Noordwijk, 15 de junio de 2020. §6.1.2.1, Tabla 6-2 y Anexo F.1 y F.5. <https://ecss.nl/standard/ecss-e-st-10-04c-rev-1-space-environment-15-june-2020/>. Local: `fuentes/ecss/ECSS-E-ST-10-04C-Rev1-2020.pdf`.
4. ECSS-E-ST-10-04C. *Space engineering — Space environment*. ECSS Secretariat, 15 de noviembre de 2008. Tabla 6-2. Reemplazada por [3]. Local: `fuentes/ecss/ECSS-E-ST-10-04C-2008.pdf`.
5. Remaury, S., Nabarra, P., Bellouard, E. y d'Escrivan, S. (CNES). «In-flight thermal coatings ageing on the THERME experiment». 11th International Symposium on Materials in a Space Environment (ISMSE-11), 2009. Tablas 1 a 11 y §5.1. <http://esmat.esa.int/materials_news/isme09/pdf/10-In-flight/Remaury%20Paper.pdf>. Local: `fuentes/otros/CNES-THERME-remaury-ISMSE11-2009.pdf`.
6. Hasegawa, M., Freese, S., Kauder, L. y Triolo, J. (NASA GSFC). «End-of-Life Optical Property Predictions of White Conductive Thermal Control Coatings through Analysis of On-Orbit and Ground Based Testing Data», 2011. Tablas 1 y 3 a 6 y conclusión (α EOL < 0,45 a 15 años en GEO). NTRS 20180000013. Local: `fuentes/nasa/NTRS-20180000013-hasegawa-eol-white-coatings.pdf`.
7. Jaworske, D. A. y Kline, S. E. *Review of End-of-Life Thermal Control Coating Performance*. NASA/TM-2008-215173, Glenn Research Center, abril de 2008. Tablas 1 a 4 y pp. 2–7. NTRS 20080018585. Local: `fuentes/nasa/NASA-TM-2008-215173-jaworske-eol-coatings.pdf`.
8. Finckenor, M. M., Pippin, H. G. y Frey, G. «MISSE Thermal Control Materials with Comparison to Previous Flight Experiments», 2008. Tablas 1 y 2 y texto sobre LDEF, POSA-I y MISSE-5. NTRS 20080031037. Local: `fuentes/nasa/NTRS-20080031037-finckenor-misse-thermal-control.pdf`.
9. ECSS-E-HB-31-01 Part 6A. *Space engineering — Thermal design handbook — Part 6: Thermal Control Surfaces*. ECSS Secretariat, 5 de diciembre de 2011. Fig. 5-27 (S-13G/LO en OTS y Navstar 6, p. 105, a partir de Chalmers et al. 1983 y de Pence y Grant 1981). <https://ecss.nl/hbs/active-handbooks/>. Local: `fuentes/ecss-e-hb-31-01/partes/part06.pdf`.
10. Finckenor, M. M. y Dooling, D. *Multilayer Insulation Material Guidelines*. NASA/TP-1999-209263, Marshall Space Flight Center, 1999. §4.1.1 (beta cloth). Local: `fuentes/nasa/NASA-TP-1999-209263-finckenor-mli.pdf`.
11. ESA (SRE-PA y D-TEC). *Margin philosophy for science assessment studies*. SRE-PA/2011.097, Issue 1, Rev. 3, 15 de junio de 2012. §2.4 (R-P-1 a R-P-6) y §2.7 (R-T-1 a R-T-3). Local: `fuentes/esa/ESA-SRE-PA-2011-097-margin-philosophy-1.3.pdf`.
12. NASA Goddard Space Flight Center. *Rules for the Design, Development, Verification, and Operation of Flight Systems* (GOLD rules). GSFC-STD-1000, Rev. I, 19 de agosto de 2025. Regla 1.06 y Tabla 1.06-1 (p. 10); regla 4.25 (p. 76). <https://standards.nasa.gov/system/files/tmp/GSFC-STD-1000RevI_Approved_0.pdf>. Local: `fuentes/nasa/GSFC-STD-1000-RevI-gold-rules.pdf`.
13. ESA. *ECSS-E-ST-31 Standardisation Training Course 2023*, Rev. 1. Diapositiva 114. Local: `fuentes/ecss/ESA-ECSS-E-ST-31-training-2023-rev1.pdf`.
14. Peabody, H. L. y Peabody, S. A. S. «Gaps in Thermal Design Guidelines in the Goddard Space Flight Center GOLD Rules». ICES-2018-268, 2018. p. 9 (autoridad de control de heaters y disipación menor que la esperada). Local: `fuentes/nasa/ICES-2018-268-peabody-gold.pdf`.
15. NIST Chemistry WebBook, SRD 69. *Hydrazine* (CAS 302-01-2), datos de fase condensada: capacidad calorífica del líquido (ecuación de Shomate) de Chase, M. W., Jr., *NIST-JANAF Thermochemical Tables*, 4.ª ed., J. Phys. Chem. Ref. Data, Monografía 9, 1998. <https://webbook.nist.gov/cgi/cbook.cgi?ID=C302012&Mask=2>, consultado el 2026-10-05. Local: `fuentes/otros/NIST-webbook-hydrazine-C302012-condensed-phase.html`.
16. ECSS-E-HB-31-01 Part 5A. *Space engineering — Thermal design handbook — Part 5: Structural Materials: Metallic and Composite*. ECSS Secretariat, 5 de diciembre de 2011. Fig. 4-1 (aluminio, p. 30), Fig. 4-68 (Ti-6Al-4V, p. 152) y Tabla 5-8 (compuestos, p. 221). Local: `fuentes/ecss-e-hb-31-01/partes/part05.pdf`.

**No consultadas** (citadas a través de otras fuentes o sin acceso; no respaldan ningún valor de este informe)

- Hall, D. F. y Fote, A. A. «Thermal Control Coatings Performance at Near Geosynchronous Altitude». *J. Thermophysics and Heat Transfer*, vol. 6, n.º 4, 1992, p. 665. Fuente original de SCATHA; citada en [6].
- Pence, W. R. y Grant, T. J. «αs measurements of thermal control coatings on Navstar GPS» (1981). Citada en [9].
- Justus, C. G., Batts, G. W., Anderson, B. J. y James, B. F. *Simple Thermal Environment Model (STEM) User's Guide*. Citada en [1] como «en preparación».
- ANSI/AIAA S-120A-2015, *Mass Properties Control for Space Systems*, y AIAA S-122, *Electrical Power Systems for Unmanned Spacecraft*. Sin acceso.
- ECSS-E-ST-10-02C (categorías de calificación A a D). No se leyó; las categorías se usan como las define [11].
- GSFC-STD-7000 (GEVS), §2.6. Referida por [12, regla 4.25].
- Slemp, W. S. y Young, P. R. *LDEF thermal control coatings post-flight analysis*. NTRS 19930019089. Identificada, no leída.
- Karam, R. D. *Satellite Thermal Control for Systems Engineers*. AIAA, 1998. Sigue sin acceso.
