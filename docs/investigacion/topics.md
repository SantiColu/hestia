# Temas de investigación

Temas para investigar antes de especificar las etapas que vienen. Cada uno termina en un documento en esta carpeta, con el formato de [balance-global.md](balance-global.md): recomendación primero, respaldo separado de opinión y fuentes completas.

**Estados:** `pendiente` · `en curso` · `hecho (en revisión)` · `cerrado` (revisado y volcado a la especificación de la etapa).

| # | Tema | Etapas | Estado | Documento |
|---|---|---|---|---|
| 0 | Balance global: concepto | `global_balance` | hecho (en revisión) | [balance-global.md](balance-global.md) |
| 1 | Concepto TCS: cómo se elige la arquitectura | `tcs_concept` | hecho (en revisión) | [concepto-tcs.md](concepto-tcs.md) |
| 2 | Modelo nodal: discretización y acoplamientos | `discretization`, `couplings` | hecho (en revisión) | [modelo-nodal.md](modelo-nodal.md) |
| 3 | Resolución numérica y casos de referencia | `solution` (y tests de todas) | pendiente | — |
| 4 | Pendientes de Entorno y del balance | `environment`, `global_balance` | hecho (en revisión) | [datos-entorno-y-balance.md](datos-entorno-y-balance.md) |
| 5 | Casos de carga y márgenes | `load_cases`, `margins` | pendiente | — |
| 6 | Datos de satélites reales para chequeos de sanidad | todas | pendiente | — |

## 1. Concepto TCS

La etapa que sigue al balance y la que más depende de él.

- **Catálogo de tecnologías:** recubrimientos, MLI, radiadores fijos y desplegables, heaters, heat pipes (de conductancia constante y variable, y de lazo), louvers, PCM, correas térmicas y doublers. Para cada una: cuándo conviene y valores de dimensionamiento con fuente (kg/m² de MLI, W·m de un heat pipe, rango de emitancia efectiva de un louver, masa de heaters).
- **Trade-off en la práctica:** criterios y métodos.
- **El punto difícil:** hacer el trade-off sin juicio de IA. Cada alternativa se dimensiona con `hestia_core`; los pesos de la evaluación son parámetros explícitos.

## 2. Modelo nodal: discretización y acoplamientos

El bloque de física más grande de la fase 1.

- Cómo se discretiza un satélite mediano en prediseño: cuántos nodos y por qué.
- Conductancias de contacto típicas con fuente: uniones abulonadas, con y sin relleno, paneles de honeycomb. ECSS-E-HB-31-01, parte 4 (cláusula 5), y Gilmore, caps. 8 y 16, tratan la resistencia de contacto.
- Acoplamientos radiativos y factores de vista; qué puede hacer pyViewFactor.

## 3. Resolución numérica y casos de referencia

- Cómo resuelven ESATAN y SINDA una red no lineal en estacionario y en transitorio.
- Criterios de convergencia y de balance de energía.
- Una colección de casos publicados, con todos sus datos y resultados, para usar como tests de regresión (`physics-validation`). Candidato ya identificado: el ejemplo POAM de Gilmore, cap. 15.

## 4. Pendientes de Entorno y del balance

Tema chico, que se implementa enseguida.

- **Tablas de albedo e IR:** hoy Entorno tiene una tabla provisoria de una sola banda. Extraer las tablas completas de NASA/TM-2001-211221: 3 bandas de inclinación × 7 tiempos de promediado × casos de albedo, IR y combinado, con la corrección por ángulo cenital solar. Sumar las tablas equivalentes de Gilmore (cap. 2, Tablas 2.1–2.4).
- **Degradación EOL en GEO y MEO:** cerrar el hueco del informe del balance (OSR en LEO; recubrimientos en GEO, Gilmore Figs. 4.7–4.11).
- **Puntos abiertos del balance** que se resuelven con datos: [balance-global.md](balance-global.md#lo-que-queda-abierto).

## 5. Casos de carga y márgenes

- Cómo se arman los transitorios: ciclos de trabajo, termostatos de heaters, LEOP, modo seguro.
- Cómo se verifican los márgenes ECSS por equipo, en su punto de referencia de temperatura (TRP).
- Qué pide ECSS-E-ST-31C para el informe de análisis del TCS (su anexo C), así la salida de Hestia ya tiene ese formato.

## 6. Datos de satélites reales para chequeos de sanidad

- ECSS-E-HB-31-01, parte 15 («Existing satellites»), describe el diseño térmico de satélites existentes.
- Armar una tabla de satélites medianos con áreas de radiador, potencia de heaters, masa del TCS y recubrimientos.
- **Para qué:** avisos «fuera de lo usual» en los resultados y rangos de referencia en todas las etapas.

## Fuentes accesibles

Verificado el 2026-10-05; ampliado el 2026-10-06 (tema 2). Con `pdftotext -layout` alcanza para extraer el texto de casi todas.

**Copia local:** `docs/investigacion/fuentes/` (ignorada por git) guarda cada PDF bajado con su texto extraído al lado (`.txt`), por fuente: `ecss/`, `ecss-e-hb-31-01/`, `gilmore-2ed/`, `nasa/`, `esa/`, `otros/`, `catalogos/`. Los libros que se bajan por partes tienen el PDF completo unido en su carpeta (`ECSS-E-HB-31-01-partes-1-16.pdf`, `gilmore-2ed-vol1.pdf`, con su `.txt`) y las piezas en una subcarpeta (`partes/partNN`, `capitulos/chNN`). El Gilmore unido tiene solo los capítulos 1–19, sin preliminares ni apéndices (la copia online no los tiene). Antes de bajar algo, buscar ahí.

| Fuente | Acceso | Notas |
|---|---|---|
| ECSS-E-ST-31C (2008) | <https://ecss.nl/wp-content/uploads/standards/ecss-e/ECSS-E-ST-31C15November2008.pdf> | Texto extraíble |
| Curso de ESA sobre ECSS-E-ST-31 (2023, Rev. 1) | <https://ecss.nl/wp-content/uploads/2023/05/ESA_ECSS-E-ST-31_Standardisation_Training_Course_2023_Rev1.pdf> | Márgenes típicos, incertidumbre por fase, hardware del TCS |
| ECSS-E-HB-31-03A (2016, handbook de análisis térmico) | <https://ecss.nl/wp-content/uploads/2016/11/ECSS-E-HB-31-03A15November2016.pdf> | La fuente más directa para el modelo nodal: discretización, cavidades, chequeos de topología, incertidumbres por fase y Tablas 6-1/6-2 de incertidumbre de parámetros, reducción de modelos, MLI, heat pipes, materiales en capas. Texto extraíble. Local: `ecss/` |
| Curso de ESA sobre ECSS-E-ST-31 (2017) | <https://ecss.nl/wp-content/uploads/2017/11/ECSS-Training-L2-E31-Thermal-(2017-10).pdf> | **No sirvió:** para modelado, lo mismo que la versión 2023 |
| ECSS-E-HB-31-01, partes 1 a 16 (2011) | `https://ecss.nl/wp-content/uploads/handbooks/ecss-e-hb/ECSS-E-HB-31-01_Part<N>A.pdf` | Probadas las 16 (títulos verificados en la tapa): 1 factores de vista, 2 agujeros, ranuras y cavidades, 3 temperatura de superficies, 4 conducción (cláusula 5: conductancia de juntas), 5 materiales estructurales, 6 superficies de control térmico, 7 aislación, 8 heat pipes, 9 radiadores, 10 PCM, 11 calentamiento eléctrico, 12 louvers, 13 lazos de fluido, 14 criogenia, 15 satélites existentes, 16 protección térmica. Parte 8, cláusula 9: catálogos de EHP, Iberespacio y Thales con W·m y g/m (los de Astrium son imágenes). Parte 15: masas por subsistema y trade-offs de IUE, OTS, Landsat D, SPOT 1. Parte 6, Fig. 5-27: α de S-13G/LO en vuelo (OTS en GEO, Navstar 6); el resto de la parte 6 son en su mayoría ensayos de laboratorio de los años 70 |
| Gilmore, *Spacecraft Thermal Control Handbook*, vol. I, 2.ª ed. (2002) | Copia accesible por capítulo: `http://matthewwturner.com/uah/IPT2008_summer/baselines/LOW%20Files/Thermal/Spacecraft%20Thermal%20Control%20Handbook/<NN>.pdf` | Leídos: 01–09, 11, 14, 15, 16 y 19. El número de capítulo coincide con el archivo (los 19 existen): 8 montajes e interfaces (doublers, contacto), 9 louvers, 10 heat switches, 11 PCM, 12 lazos bombeados, 13 termoeléctricos, 14 heat pipes, 16 resistencia de contacto, 17 control de precisión, 18 shuttle, 19 ensayos. Las figuras que salen ilegibles en el texto se leen bien renderizando la página (`pdftoppm -r 200`, o `pdfimages` para el escaneo original de 300 ppp); así se digitalizaron las Figs. 4.7 y 4.9 a 4.11 |
| NASA/TM-2001-211221 (albedo e IR) | <https://ntrs.nasa.gov/api/citations/20020004360/downloads/20020004360.pdf> | Tablas 4.2.1-1, 4.2.3-1 a -3, A-1 y A-2 extraíbles, con errores menores de OCR (`10S` por `108`, `0 i0` por `0,10`): verificar contra la imagen. Transcritas y verificadas en [datos-entorno-y-balance.md](datos-entorno-y-balance.md) |
| NASA RP-1121 (Henninger, recubrimientos) | <https://ntrs.nasa.gov/api/citations/19840015630/downloads/19840015630.pdf> | Solo BOL; poca degradación |
| NASA/TP-1999-209263 (Finckenor, materiales de MLI) | <https://ntrs.nasa.gov/api/citations/19990047691/downloads/19990047691.pdf> | Tablas con OCR desprolijo. Sin datos numéricos de degradación del beta cloth (solo cualitativos, §4.1.1) |
| NASA/TP-2005-212792 (Kauder, recubrimientos) | NTRS 20070014757 | El texto **no** se extrae (fuente con desplazamiento de caracteres, tablas sin números). No vale la pena |
| THERME, CNES (degradación en vuelo en SSO) | <http://esmat.esa.int/materials_news/isme09/pdf/10-In-flight/Remaury%20Paper.pdf> | Datos LEO de SSM, pinturas blancas y Kapton. Las tablas salen mezcladas por las dos columnas: leerlas en la imagen (Tablas 2 a 7, pp. 2–3) |
| Peabody, ICES-2018-268 (reglas GOLD de GSFC) | <https://ntrs.nasa.gov/api/citations/20180004564/downloads/20180004564.pdf> | Márgenes de GSFC (5 °C, 70 % de ciclo de heaters, 30 % de transporte en heat pipes) según la Rev. G. La Rev. I ya no da los 5 °C (ver GSFC-STD-1000) |
| GSFC-STD-1000 Rev. I (reglas GOLD, 2025) | <https://standards.nasa.gov/system/files/tmp/GSFC-STD-1000RevI_Approved_0.pdf> | Vigente. Tabla 1.06-1: márgenes de capacidad de potencia por fase (25/20/15/10/5 %). La regla térmica 4.25 remite a GEVS 2.6. La URL está en `tmp/`: puede cambiar |
| ECSS-E-ST-10-04C Rev.1 (2020, ambiente espacial) | <https://ecss.nl/wp-content/uploads/2020/07/ECSS-E-ST-10-04C-Rev.1(15June2020).pdf> | Constante solar 1361 W/m², afelio y perihelio (§6.1.2.1, Tabla 6-2). La versión 2008, reemplazada, da 1366,1: <https://ecss.nl/wp-content/uploads/standards/ecss-e/ECSS-E-ST-10-04C15November2008.pdf> |
| Hasegawa et al. (GSFC, 2011), EOL de pinturas blancas conductoras | <https://ntrs.nasa.gov/api/citations/20180000013/downloads/20180000013.pdf> | Datos de vuelo en GEO (SCATHA, estimado a 15 años) y NTS de OSR, Ag/FEP y pinturas; α EOL de diseño del Z93C55. OCR sucio: tablas en la p. 6 de la imagen |
| NASA/TM-2008-215173 (Jaworske y Kline, EOL de recubrimientos) | <https://ntrs.nasa.gov/api/citations/20080018585/downloads/20080018585.pdf> | Z-93 en laboratorio tipo GEO y en vuelo (OPM, MISSE, Lunar Orbiter, Mariner) |
| Finckenor, Pippin y Frey (2008), MISSE | <https://ntrs.nasa.gov/api/citations/20080031037/downloads/20080031037.pdf> | Z-93 y AZ-93 en LEO (~4 años), comparación con LDEF y POSA-I |
| NIST Chemistry WebBook, hidracina | <https://webbook.nist.gov/cgi/cbook.cgi?ID=C302012&Mask=2> | cp del líquido (Shomate de NIST-JANAF, 298–800 K). WebFetch resume mal la tabla: bajar el HTML con `curl` |
| ECSS-E-ST-10C Rev.1 (2017, ingeniería de sistemas) | <https://ecss.nl/wp-content/uploads/2017/02/ECSS-E-ST-10C-Rev.1(15February2017).pdf> | Anexo L: contenido del informe de trade-off (pesos, sensibilidad) |
| NASA/SP-2016-6105 Rev 2 (manual de ingeniería de sistemas) | <https://ntrs.nasa.gov/api/citations/20170001761/downloads/20170001761.pdf> | §6.8: análisis de decisión, matrices ponderadas, normalización |
| ESA SRE-PA/2011.097 (filosofía de márgenes, 2012) | <https://sci.esa.int/documents/34375/36249/1567260131067-Margin_philosophy_for_science_assessment_studies_1.3.pdf> | Márgenes de madurez de masa y potencia (5/10/20 %), de sistema (20 %) y criogénicos |
| Zandbergen, apunte AE1222-II de TU Delft (2013/2014) | <https://www.fisme.science.uu.nl/woudschotennatuurkunde/verslagen/Vrsl2013/lezingen/za-Zandbergen/Reader%201222%20-%20Spacecraft%20Design%20(total)_%202013-2014_v2.pdf> | Apéndice D: % de masa seca por subsistema de 17 satélites (SMAD/SSE), 11 GEO y 13 chicos. Fuente secundaria de SMAD |
| NASA, estado del arte de satélites chicos, cap. 7 térmico (2022) | <https://www.nasa.gov/wp-content/uploads/2023/05/7.-soa-thermal-2022.pdf> | TRL por tecnología, pero para satélites chicos |
| NASA, borrador «Thermal Straps» (2024) | <https://ntrs.nasa.gov/api/citations/20240006644/downloads/STCH_Thermal%20Straps_Submitted_Q2%202024.pdf> | Conductancia de correas, propiedades de materiales, ejemplos |
| Sensata, hoja de catálogo del termostato M2 (S-311-P641/02) | <https://www.flamecorp.com/PDF/Sensata/2021/G311P641-02_Series_Catalog_Sheets.pdf> | Masa y corriente de un termostato espacial. La página de sensata.com devuelve 403 |
| Minco, heaters de Kapton | <https://www.minco.com/products/heat/polyimidethermofoilheaters> | **No sirvió:** no publica masa por área |
| ESA, informe CDF-150(A) de ATHENA (2014) | <https://www.cosmos.esa.int/documents/400752/400864/ATHENA+-+CDF+Study+Report.pdf> | §11.2: el TCS del módulo de servicio dimensionado como un nodo en un CDF (fase 0). El resto del capítulo térmico es del espejo, no del satélite. Local: `esa/` |
| Gaite, «Nonlinear analysis of spacecraft thermal models» (arXiv:1010.4707, 2010) | <https://arxiv.org/abs/1010.4707> | Conectividad (irreducibilidad) de la red y estacionario único; condensación de nodos. Útil también para el tema 3. Local: `otros/` |
| Daryabeigi, AIAA 2001-2825 (honeycomb) | <https://ntrs.nasa.gov/api/citations/20010066875/downloads/20010066875.pdf> | Swann y Pittman frente a mediciones (17–61 % de diferencia) en un núcleo de titanio; poco para paneles de aluminio. Local: `nasa/` |
| pyViewFactor (PyPI y documentación) | <https://pypi.org/pypi/pyviewfactor/json>, <https://arep-dev.gitlab.io/pyViewFactor/> | La página de PyPI no se lee con WebFetch: usar la API JSON con `curl`. La documentación sí (obstrucción binaria, validación analítica) |
| Maleki et al. (1999), cp de celdas de ion-litio | <https://www.osti.gov/biblio/345380> | Solo el resumen; no se buscó el texto completo |
| View3D (NIST, Walton, NISTIR 6925) | <https://view3d.sourceforge.net/> | Factores de vista con obstrucción parcial, en C. Licencia no verificada; no leído |
| Gilmore, apéndices B y C (honeycomb y rellenos) | Sin acceso | La copia online no tiene los apéndices |
| Wertz y Larson, *SMAD* (3.ª ed.) | Sin acceso directo | Sus tablas de masa por subsistema llegan vía el apunte de TU Delft |
| Karam, *Satellite Thermal Control for Systems Engineers* (1998) | Sin acceso | globalspec y AIAA ARC devuelven 403 |
