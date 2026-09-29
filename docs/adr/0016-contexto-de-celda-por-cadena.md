# 0016. Contexto de celda por cadena aguas arriba

- **Estado:** propuesto
- **Fecha:** 2026-09-29
- **Reemplaza en parte:** 0009 (la regla de vínculos por entrada)

## Contexto

Según el ADR 0009, cada entrada de una celda se identifica por el tipo que la alimenta y necesita su propio vínculo. Si una etapa usa datos de varias etapas anteriores, hay que vincularlas todas: ramificar Fase 1 desde Misión crea dos vínculos (a Discretización y a Márgenes), y entre Fase 0 y Fase 1 terminan tres flechas. El esquemático se llena de vínculos que repiten algo que la cadena ya dice.

Además, la lista de equipos se separa de la misión en una etapa propia (`equipment`): cambia seguido, viene de otra fuente y no la usa el ambiente. Hace falta poder combinar un ambiente y una lista de equipos sin duplicar ninguna de las dos, y comparar resultados de ramas distintas (post-proceso tipo CFX).

## Decisión

- **Contexto:** una celda ve las salidas de todas las celdas aguas arriba de ella. Un vínculo transmite todo el contexto de la fuente, no solo su salida.
- **Requisitos por tipo:** cada tipo de etapa declara qué tipos necesita en su contexto, no de qué celdas. Si falta alguno, la celda muestra qué le falta y no puede correr.
- **Un padre por defecto:** una celda recibe un solo vínculo y puede alimentar a muchas. En el contexto no se repiten tipos.
- **Unión:** una celda puede tener varios padres si sus contextos no comparten ningún tipo, así que cada tipo viene de un solo lado. Es el caso del balance global, que une la rama misión → ambiente con equipos.
- **Colectores:** algunos tipos (Comparación) aceptan varios padres del mismo tipo para compararlos. Son terminales: no pasan contexto aguas abajo.
- **Raíces:** `mission` y `equipment` no tienen entradas. Los modos operativos pasan de Misión a Equipos, junto con el estado y la disipación de cada equipo por modo. Misión conserva los modos de actitud. La relación entre modo operativo y actitud se elige al armar cada caso (casos hot/cold de `global_balance`, `load_cases`).
- **Vínculo válido:** el grafo sigue acíclico, el destino no tenía padre (salvo unión o colector), el contexto resultante no repite tipos y los tipos siguen el orden del catálogo.
- **Numeración y plantillas:** la fase 0 conserva el orden de lectura aunque el grafo no sea lineal: 0.1 `mission`, 0.2 `environment`, 0.3 `equipment`, 0.4 `global_balance`, 0.5 `tcs_concept`. La plantilla Fase 0 crea las cinco celdas en ese orden (misión → ambiente, y ambiente y equipos → balance → concepto TCS). Entre fases alcanza un vínculo: `tcs_concept` → `discretization`.

## Consecuencias

- Menos vínculos: una cadena simple Fase 0 → Fase 1 es un solo vínculo entre sistemas.
- Variantes sin duplicar: dos ambientes pueden usar la misma celda de Equipos y dos listas de equipos el mismo ambiente. La comparación es un colector.
- La trazabilidad pasa de los vínculos a la procedencia: cada celda informa de qué celda concreta sale cada tipo de su contexto (panel Propiedades).
- Las validaciones que cruzan raíces (p. ej. masa de los equipos ≤ masa del satélite) se hacen donde las raíces se unen (`global_balance`), no en los formularios.
- La propagación de «desactualizada» no cambia: recorre los vínculos aguas abajo.
- Pendiente de implementar: catálogo (requisitos y orden en lugar de entradas por fuente, tipo `equipment`, renumeración), validación de vínculos, plantillas, ramificar y los documentos de campos de cada etapa.
