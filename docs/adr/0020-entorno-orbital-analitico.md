# 0020. El entorno orbital se calcula con un proveedor analítico propio; Orekit queda diferido

- **Estado:** propuesto
- **Fecha:** 2026-09-29
- **Reemplaza en parte:** 0002 (Orekit como backend de mecánica orbital)

## Contexto

La etapa Entorno (`environment`, [campos](../etapas/environment.md)) traduce la órbita y los modos de actitud de Misión en ángulo β, eclipses y flujos incidentes por cara. En el prediseño de órbitas geocéntricas circulares la incertidumbre dominante es el entorno (constante solar, albedo, IR terrestre), no la geometría orbital: las soluciones analíticas (posición del Sol de baja precisión, precesión secular por J2, sombra cilíndrica o cónica, factores de vista de placa plana a la Tierra) tienen errores despreciables frente a esa incertidumbre.

El ADR 0002 elegía Orekit para la mecánica orbital y dejaba pendiente su costo: requiere JVM, JPype y datos propios, lo que complica la instalación, el tamaño de la app de escritorio (ADR 0008) y la CI.

## Decisión

- **Proveedor analítico propio en `hestia_core`**, sin dependencias de runtime más allá de NumPy (y pydantic para los modelos, que core ya usa). Es física propia, determinística y testeada: vive en core y no en `hestia_adapters`.
- **Interfaz de proveedor de entorno:** un Protocol en `hestia_core` que recibe la órbita y los modos de actitud de Misión y los parámetros de Entorno, y devuelve el resultado de la etapa. Cada resultado registra qué proveedor y qué versión lo produjo. Un proveedor futuro basado en Orekit (u otro) se implementa en `hestia_adapters` sin tocar el resto.
- **Envolvente de validez explícita:** el proveedor declara qué órbitas soporta (geocéntricas, circulares o casi circulares, sin empuje) y rechaza el resto con un problema de código estable (p. ej. `eccentricity_out_of_range`), que deja la celda `failed`. Nunca devuelve un resultado silenciosamente incorrecto.
- **Perturbaciones de largo plazo como rangos:** la deriva de la hora del nodo en SSO, el decaimiento de altitud y la deriva de inclinación en GEO no se propagan; son parámetros de dispersión de Entorno alrededor de la órbita nominal de Misión, y Entorno evalúa sus extremos. Misión no cambia.
- **Oráculo solo en desarrollo:** un propagador serio (Skyfield, por liviano) puede usarse como dependencia de desarrollo para comparar β y eclipse a lo largo de un año con tolerancias explícitas. Nunca es dependencia de runtime.

## Consecuencias

- La app no necesita JVM: se resuelve el pendiente de instalación y CI del ADR 0002 para esta etapa.
- Los tests comparan contra cálculos a mano y casos de referencia citados (skill `physics-validation`) y contra el oráculo. Skyfield necesita una efeméride JPL (de421, ~17 MB) que hay que descargar en CI o guardar en caché; no se versiona en el repo.
- Limitaciones conocidas, documentadas en la etapa: sin eclipses lunares (relevante sobre todo en GEO), albedo e IR como valores de diseño sin variación espacial, sin calentamiento aerotérmico, sin actitudes inerciales ni giratorias (Misión no las expresa todavía).
- Misión acepta órbitas elípticas (`keplerian` con apogeo): las que superan el umbral de excentricidad quedan `failed` en Entorno hasta que exista un proveedor que las soporte.
- Pendiente: el umbral de excentricidad definitivo y si hace falta un proveedor no analítico para algún caso real.
