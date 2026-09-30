# Etapa 0.2 · Entorno (`environment`): parámetros y resultado

> **Implementado (2026-09-29).** Etapa de cálculo ([ADR 0021](../adr/0021-etapas-de-calculo.md), contrato en [ADR 0022](../adr/0022-contrato-de-etapas-de-calculo.md)) con proveedor analítico propio ([ADR 0020](../adr/0020-entorno-orbital-analitico.md)): parámetros `hestia_core.environment.parameters.EnvironmentParameters` (v1) con validación `validate_environment_parameters`, proveedor `hestia_core.environment.analytic.AnalyticEnvironmentProvider` (versión 1) detrás del Protocol `EnvironmentProvider`, resultado `EnvironmentResult` (v1), API (`update_cell`, `get_cell_result`, `get_orbit_profile` y los endpoints genéricos del artefacto para los parámetros), tools MCP y pestaña con Parámetros (con vista previa de la órbita), Resultados y Órbita 3D, alineada con `workspace.pen` (2026-09-30). Tests contra cálculos a mano y referencias, y Skyfield (SGP4 + DE421) como oráculo de desarrollo de β y eclipse. Lo marcado *(propuesta)* se decidió sin revisión y puede cambiar. Convenciones y tipos: los de [mission.md](mission.md#convenciones).
>
> **Cambio en curso ([ADR 0023](../adr/0023-orbita-y-actitud-en-entorno.md)):** la órbita y los modos de actitud pasan de Misión a los parámetros de Entorno (`EnvironmentParameters` v2), y la pestaña suma una vista previa de la órbita mientras se edita. Backend, API y MCP implementados (2026-09-30), incluida la vista previa (`preview_orbit`) y la migración v4 → v5; la UI se está alineando.
>
> **Provisorio:** la tabla de albedo e IR por inclinación tiene una sola banda (albedo 0,25–0,35, IR 218–258 W/m², «provisorio, a verificar contra NASA TM-2001-211221»); el umbral de excentricidad (0,01) y la constante solar (1361 W/m², ECSS-E-ST-10-04C) están por verificar.
>
> **Decisiones de la implementación:** albedo e IR vacíos significan «tabla por inclinación» y se resuelven al actualizar (el resultado informa el valor y su fuente); `ltan_dispersion` y `geo_max_inclination` vacíos valen 0; la altitud nominal es la de la SSO, el perigeo en LEO/MEO o la de GEO, y la órbita se modela circular a esa altitud; el período nominal sale del semieje mayor; el eclipse cónico cuenta la penumbra; la deriva de la hora del nodo se aplica como ±Δ desde el lanzamiento (conservador); cada condición propia va a la primera fecha cuya envolvente tiene su β (si la misión nunca lo tiene, a la fecha de lanzamiento con una nota); los flujos de cada condición usan la irradiancia mínima y máxima de la misión, no la de su fecha; el Sol queda fijo durante una órbita y los perfiles empiezan en el nodo ascendente; el proveedor rechaza un paso que daría más de 200 000 fechas. Detalle en los commits de la etapa.

Define la órbita y los modos de actitud y los traduce en la geometría (ángulo β, eclipses) y los **flujos incidentes** (W/m²) que recibe cada cara de la envolvente, y entrega las **condiciones extremas** del ambiente. No elige cuál es el caso caliente o frío del satélite: eso depende de sus propiedades ópticas y su disipación, y se decide en `global_balance`.

## Alcance

- **Requiere** `mission` en su contexto. Usa solo `general.launch_date` y `general.design_life` (ventana de la misión). La órbita y los modos de actitud son parámetros propios (ADR 0023): una Misión puede alimentar varios Entornos, uno por variante de órbita o de actitud.
- **Flujos incidentes, no absorbidos.** La absorción necesita propiedades ópticas (α, ε), que se fijan más adelante (`global_balance`, `tcs_concept`, `discretization`).
- **Condiciones, no casos.** Entorno no sabe qué calienta o enfría al satélite: no tiene propiedades ópticas ni Equipos en su contexto (ADR 0016). Entrega el rango de cada variable y los flujos en las combinaciones extremas. Qué combinación, qué actitud y qué modo operativo forman el caso caliente y el frío lo decide `global_balance`; los demás casos, `load_cases`. Los flujos se calculan para **todos** los modos de actitud, así esas etapas eligen.

## Parámetros

Se editan como un formulario (borrador, validación en seco, Aplicar con justificación; ADR 0021). Los defaults de biblioteca quedan marcados como tales.

### 1. Órbita (`orbit`)

Órbita terrestre. El tipo define qué se carga, tal como lo entrega el análisis de misión:

| Campo | Tipo | Unidad | Oblig. | Descripción |
|---|---|---|---|---|
| `type` | `enum OrbitType` | — | sí (default `sso`, *propuesta*) | `sso` (SSO), `keplerian` (LEO/MEO: órbita definida por sus elementos; también sirve para una elíptica) o `geo` (GEO) |
| `altitude` | `float` | m → km | si `sso` | Altitud (circular). La inclinación la fija la altitud y se calcula |
| `ltan` | `time` | — | si `sso` | Hora local (solar media) del nodo ascendente |
| `perigee_altitude` | `float` | m → km | si `keplerian` | Altitud del perigeo sobre la superficie |
| `apogee_altitude` | `float` | m → km | no | Altitud del apogeo. Vacío: órbita circular (igual al perigeo) |
| `inclination` | `float` | rad → ° | si `keplerian` | Inclinación |

`geo` no pide campos: altitud 35 786 km, circular y ecuatorial (el formulario lo muestra como nota). En la UI las opciones se muestran como **SSO · LEO/MEO · GEO**; el valor interno `keplerian` describe qué se carga, así la etiqueta puede cambiar sin tocar el modelo.

### 2. Modos de actitud (`attitude_modes`): `list`, al menos uno

Cada modo fija la actitud con dos pares eje del cuerpo → dirección: el primario se cumple exacto; el secundario orienta el giro alrededor del primario. Los ejes y las caras son los de la envolvente de Misión.

| Campo | Tipo | Unidad | Oblig. | Descripción |
|---|---|---|---|---|
| `id` | `str` | — | — | Generado |
| `name` | `str` | — | sí | P. ej. «Apuntado nadir», «Apuntado al Sol» |
| `primary_axis` | `enum Axis` | — | sí | Eje del cuerpo que apunta a `primary_target` |
| `primary_target` | `enum Target` | — | sí | Dirección del eje primario |
| `secondary_axis` | `enum Axis` | — | sí | Eje del cuerpo que se alinea con `secondary_target` |
| `secondary_target` | `enum Target` | — | sí | Dirección del eje secundario |

### 3. Valores de diseño (`design_values`)

| Campo | Tipo | Unidad | Oblig. | Descripción |
|---|---|---|---|---|
| `solar_constant` | `float` | W/m² | sí | Irradiancia solar a 1 UA. Default: 1361 W/m² *(propuesta; ECSS-E-ST-10-04C, a verificar)*. La irradiancia en cada fecha sale de la distancia Tierra–Sol, que se calcula |
| `albedo_min` | `float` | — | sí | Albedo de diseño mínimo. Default: tabla por inclinación |
| `albedo_max` | `float` | — | sí | Albedo de diseño máximo. Default: tabla por inclinación |
| `olr_min` | `float` | W/m² | sí | IR terrestre (radiación de onda larga saliente) mínima. Default: tabla por inclinación |
| `olr_max` | `float` | W/m² | sí | IR terrestre máxima. Default: tabla por inclinación |

**Por qué son datos y no salen del cálculo orbital:** la órbita da la geometría (dónde está el Sol, cuánto ve cada cara a la Tierra, cuándo hay eclipse). El albedo (qué fracción de luz refleja la Tierra) y la IR (cuánto calor emite) son propiedades de la Tierra: cambian con nubes, superficie y latitud y no se deducen de la órbita. Son la incertidumbre principal del entorno (ADR 0020). El cálculo los multiplica por la geometría.

**Default por inclinación** *(propuesta)*: la órbita sí elige el valor. Los defaults salen de las tablas de NASA TM-2001-211221 (Anderson, Justus y Batts, *Guidelines for the Selection of Near-Earth Thermal Environment Parameters for Spacecraft Design*), que dan rangos de albedo e IR de diseño por banda de inclinación. Entorno toma la banda de la inclinación de la órbita (la calculada en SSO) y los carga con procedencia `default` y la fuente. Los valores de la tabla se cargan en `hestia_core` al implementar, verificados contra el documento; la opción de tiempo de promediado de la tabla queda por fijar.

### 4. Dispersión de la órbita (`dispersion`)

Perturbaciones de largo plazo que no se propagan: Entorno evalúa sus extremos alrededor de la órbita nominal (ADR 0020).

| Campo | Tipo | Unidad | Oblig. | Descripción |
|---|---|---|---|---|
| `ltan_dispersion` | `float` | s → min | si `sso` | Deriva máxima de la hora del nodo (±) a lo largo de la vida. Default *(propuesta)*: 0 |
| `eol_altitude` | `float` | m → km | no | Altitud al fin de vida por decaimiento (`sso`, `keplerian`). Vacío: sin decaimiento |
| `geo_max_inclination` | `float` | rad → ° | si `geo` | Inclinación máxima que alcanza la órbita GEO. Default *(propuesta)*: 0 |

### 5. Muestreo (`sampling`)

| Campo | Tipo | Unidad | Oblig. | Descripción |
|---|---|---|---|---|
| `mission_step` | `float` | s → días | sí | Paso de las series a lo largo de la misión. Default *(propuesta)*: 1 día |
| `orbit_samples` | `int` | — | sí | Puntos por órbita en los perfiles. Default *(propuesta)*: 120 (3°) |
| `eclipse_model` | `enum EclipseModel` | — | sí | `cylindrical` (sombra sin penumbra) o `conical` (umbra y penumbra). Default *(propuesta)*: `cylindrical` |

### 6. Condiciones propias (`custom_conditions`): `list`, opcional

Geometrías que el usuario agrega a las extremas (p. ej. un β intermedio que interesa).

| Campo | Tipo | Unidad | Oblig. | Descripción |
|---|---|---|---|---|
| `id` | `str` | — | — | Generado |
| `name` | `str` | — | sí | P. ej. «β = 30°» |
| `beta` | `float` | rad → ° | sí | Ángulo β |
| `altitude` | `float` | m → km | no | Vacío: la nominal |

## Qué calcula

Todo en `hestia_core`, analítico (ADR 0020):

- **Sol:** posición y distancia en función de la fecha, con la fórmula de baja precisión del Astronomical Almanac (error del orden de 0,01°). La irradiancia de cada fecha es `solar_constant / r²` (r en UA).
- **Plano orbital:** RAAN a lo largo de la misión por precesión secular J2 (`orbits.py`).
  - SSO: el nodo sigue al Sol medio desde el LTAN.
  - GEO: ecuatorial, o inclinada hasta `geo_max_inclination`.
  - LEO/MEO (`keplerian`): la órbita no fija el RAAN, así que se barre completo y β se informa como envolvente (mínimo y máximo).
- **Ángulo β** a lo largo de la misión: el nominal (SSO, GEO) y la envolvente con las dispersiones.
- **Eclipse** por órbita: fracción y duración, con sombra cilíndrica en fórmula cerrada o cónica con penumbra.
- **Actitud:** la terna del cuerpo de cada modo de actitud se construye con sus dos pares eje → dirección (el primario exacto, el secundario orienta el giro), a partir de posición, velocidad y vector solar.
- **Flujos incidentes por cara:** solar directo (cero en eclipse o si la cara no ve el Sol), albedo e IR terrestre. Usan factores de vista de placa plana a la Tierra esférica en fórmula cerrada, según la altitud y el ángulo entre la normal de la cara y el nadir.
  - IR uniforme: `olr · F`.
  - Albedo: `S · a · F · cos θ`, con θ el ángulo cenital solar en el punto subsatélite (cero en el lado nocturno) *(propuesta)*.
- **Rangos:** irradiancia mínima y máxima dentro de la ventana de la misión (afelio y perihelio), β mínimo y máximo de la envolvente, altitud nominal y de fin de vida, y los rangos de albedo e IR.
- **Condiciones extremas** *(propuesta)*: cada combinación de los extremos geométricos (β de mayor y de menor eclipse × altitud nominal y de fin de vida, sin repetir), más las condiciones propias. Para cada una: período, eclipse y flujos. Cada flujo se da en su mínimo y su máximo: solar con la irradiancia mínima y la máxima, albedo con irradiancia × albedo mínimos y máximos, IR con la IR mínima y la máxima. Entorno no combina ni elige: `global_balance` toma de acá los extremos que forman sus casos.

## Resultado

| Parte | Contenido |
|---|---|
| `mission_series` | Por fecha (cada `mission_step`): β nominal (vacío en `keplerian`), β mínimo y máximo, fracción y duración de eclipse (mínimo y máximo), irradiancia solar |
| `ranges` | Irradiancia, β, altitud, albedo e IR: mínimo y máximo, con la fecha o el motivo de cada extremo |
| `conditions` | Por condición (extremas y propias): origen, β, altitud, período, fracción y duración de eclipse |
| `fluxes` | Por condición × modo de actitud × cara: promedio orbital y pico de solar, albedo e IR, cada uno en su valor mínimo y máximo (W/m²) |
| `orbit_profiles` | Por condición × modo de actitud, `orbit_samples` puntos sobre una órbita: tiempo, posición y velocidad (inerciales, m y m/s), vector solar, en sol/eclipse, cuaternión cuerpo → inercial, ángulo de rotación terrestre y flujos por cara |
| `provenance` | Celda y cambio de Misión usados, parámetros aplicados, proveedor y versión (ADR 0021) |

Los perfiles sirven para los gráficos, la vista 3D y, más adelante, para los transitorios de `load_cases`. Los tamaños son chicos: una misión de 5 años con paso diario da ~1800 puntos, y un perfil 120. Se guardan como JSON en el `.hestia`; Parquet u otro formato se evalúa cuando el volumen lo pida (fase 1).

## Validaciones

**Parámetros**
- Órbita: obligatorios según la tabla; solo se cargan los campos del tipo elegido (`not_allowed`); altitudes ≥ 100 km; `apogee_altitude` ≥ `perigee_altitude` (`order`); `inclination` entre 0° y 180°; en `sso`, la altitud tiene que admitir una SSO (hasta unos 5 970 km, `sso_altitude`); el LTAN con formato `HH:MM` (`format`).
- Modos de actitud: al menos uno; nombres únicos (`duplicate_name`); `secondary_axis` no es paralelo a `primary_axis` (ni igual ni opuesto) y `secondary_target` no es la misma dirección ni la opuesta que `primary_target` (`parallel`).
- `solar_constant` > 0; albedos entre 0 y 1; IR > 0; `albedo_min` ≤ `albedo_max` y `olr_min` ≤ `olr_max` (con los valores de tabla para los vacíos).
- Solo se cargan los campos de dispersión del tipo de órbita (`not_allowed`, como los de la órbita).
- `ltan_dispersion` ≥ 0; `geo_max_inclination` ≥ 0; `eol_altitude` ≥ 100 km y ≤ la altitud nominal (el perigeo en `keplerian`).
- `mission_step` > 0 y ≤ `design_life` (la única regla que mira el contexto); `orbit_samples` entre 36 y 3600.
- Condiciones propias: nombres únicos; β entre −90° y 90°; altitud ≥ 100 km.

**Al actualizar** (la celda queda `failed` con el problema):
- `missing`: no hay Misión en el contexto.
- `context_invalid`: la Misión del contexto tiene problemas.
- `eccentricity_out_of_range`: excentricidad mayor que 0,01 *(propuesta)*, fuera de la envolvente del proveedor.

## Vista de la celda

La pestaña de la celda tiene tres secciones *(propuesta; diseño primero en `workspace.pen`)*:

1. **Parámetros:** el formulario, como Misión, con una **vista previa de la órbita** al lado (ADR 0023). Mientras se edita, la UI pide al backend la órbita del borrador (con *debounce*, como la validación en seco) y la dibuja con la escena de la Órbita 3D: órbita nominal en la fecha elegida (por defecto, la de lanzamiento), coloreada por sol/eclipse, y la envolvente orientada según el modo de actitud elegido. Muestra β, período y eclipse de esa órbita. No tiene flujos, no guarda nada ni cambia el estado de la celda. Si la órbita o los modos del borrador tienen problemas, la vista previa lo dice y muestra la última órbita válida atenuada *(propuesta)*.
2. **Resultados:**
   - gráficos de β y eclipse a lo largo de la misión (línea nominal y banda de envolvente);
   - tabla de rangos y de condiciones;
   - tabla de flujos por cara con selector de condición y modo de actitud;
   - perfil orbital de flujos por cara.
3. **Órbita 3D:** animación de una órbita para la condición y el modo de actitud elegidos. Un selector **Global · Local** cambia la cámara de la misma escena (se ve una vista a la vez):
   - **Global:**
     - Tierra estilizada (esfera oscura con costas y retícula, sin textura fotográfica) que gira;
     - la órbita coloreada por sol/eclipse y el cilindro de sombra;
     - la dirección del Sol y el satélite.
   - **Local:** acercamiento que sigue al satélite (doble clic en el satélite desde Global también la abre). Se ven:
     - la superficie de la Tierra con su retícula y el horizonte;
     - la línea de la órbita, que pasa por el satélite y se pierde tras el horizonte;
     - la envolvente, fuera de escala, con sus caras (+X…−Z) y los ejes del cuerpo;
     - los vectores Sol, nadir y velocidad;
     - cada cara coloreada por el flujo incidente total en ese instante, con escala.
   - **Controles:** play/pausa, velocidad, barra de tiempo sobre la órbita y lectura del instante (tiempo, β, sol/eclipse, flujos de la cara elegida). Cambiar de vista conserva el instante.

Con la celda desactualizada, los resultados se muestran con el aviso de «desactualizada»; sin resultado, la sección lo dice y ofrece Actualizar.

La UI no calcula: dibuja `orbit_profiles` tal como llegan y solo interpola entre muestras para animar. Los agentes leen los mismos datos con la tool del resultado, y la vista previa con su propia tool (paridad). Librería 3D: three.js con `@react-three/fiber` *(propuesta)*; costas de Natural Earth (dominio público), empaquetadas con la app.

## Limitaciones conocidas

- Órbitas geocéntricas circulares o casi circulares, sin empuje (ADR 0020).
- Sin eclipses lunares (relevantes sobre todo en GEO).
- Albedo e IR como valores de diseño, sin variación espacial ni temporal dentro de la órbita.
- Sin calentamiento aerotérmico ni flujos de moléculas libres.
- Sin sombras propias, paneles ni apéndices: la envolvente es una caja convexa y cada cara ve el entorno completo.
- Actitudes solo por pares eje → dirección (sin inerciales, giratorias ni *yaw steering*).
- Órbitas elípticas sin orientación (RAAN, argumento del perigeo): se barre el peor caso.

## Abierto

- Tiempo de promediado de las tablas de albedo e IR (depende de la inercia térmica, que se conoce recién en `global_balance`).
- Umbral de excentricidad (hoy 0,01, provisorio).
- Tablas de albedo e IR de NASA TM-2001-211221 (hoy una banda provisoria).
- Si la vista previa suma flujos (necesita albedo e IR válidos).
- Con qué RAAN dibuja la vista previa una órbita LEO/MEO (hoy 0° en la fecha elegida, *propuesta*) y si conviene un selector.
- Recorrer la misión completa en la vista 3D (la fecha mueve el plano orbital), además de una órbita por condición.

## Enumeraciones

| Enum | Valores |
|---|---|
| `Axis` | `+X`, `-X`, `+Y`, `-Y`, `+Z`, `-Z` |
| `EclipseModel` | `cylindrical`, `conical` |
| `OrbitType` | `sso`, `keplerian`, `geo` |
| `Target` | `nadir`, `zenith`, `sun`, `velocity`, `anti_velocity`, `orbit_normal`, `anti_orbit_normal` |
