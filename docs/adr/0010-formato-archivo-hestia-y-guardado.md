# 0010. Formato del archivo `.hestia` y semántica de guardado

- **Estado:** propuesto
- **Fecha:** 2026-09-28
- **Amplía:** 0006, 0008 (resuelve el TODO de formato interno y guardado)

## Contexto

ADR 0008 fija que cada proyecto es un archivo SQLite con Abrir, Guardar, Guardar como (API de backup), recientes y lock contra doble apertura, pero deja como TODO el formato interno y si se guarda automáticamente o de forma explícita. Hoy el proyecto es solo el esquemático (sistemas, celdas, vínculos) y su historial; todavía no hay resultados de cálculo.

## Decisión

- **Guardado explícito**, como en Ansys o Pencil. El estado de trabajo vive en memoria en el backend; el archivo cambia solo con Guardar o Guardar como. El proyecto está *dirty* cuando hubo cambios (incluidos deshacer y rehacer) desde el último guardado. Sin autoguardado por ahora.
- **Guardar = reescritura atómica.** Se arma la base completa en memoria, se copia con la API de backup de SQLite a un temporal junto al destino y se reemplaza el destino con un `rename` atómico. Un corte a mitad de guardado nunca deja el archivo a medias. Guardar como usa el mismo camino hacia otra ruta y pasa a trabajar sobre ella; agrega `.hestia` si falta y el nombre del proyecto pasa a ser el del archivo.
- **Formato interno (esquema v1):**
  - `PRAGMA application_id = 0x48535441` («HSTA») identifica el archivo; `PRAGMA user_version` = versión de esquema (`hestia_project.model.SCHEMA_VERSION`). Se rechazan archivos ajenos y versiones más nuevas que la soportada.
  - Tablas: `meta` (clave/valor: formato, versión, id y nombre del proyecto), `systems`, `cells`, `links` (con `UNIQUE(target_cell_id, input)`: una fuente por entrada) y `changes`.
  - `changes` es el log de ADR 0006: por entrada, el `Change` (autor, justificación, operación, resumen, ids creados y desactualizados) y las instantáneas completas del proyecto antes y después. Instantáneas y no diffs: el esquemático pesa kilobytes y así deshacer y auditar son triviales.
- **Historial persistente, pilas de deshacer por sesión.** El historial se guarda en el archivo; deshacer/rehacer opera sobre los cambios de la sesión abierta (al reabrir, las pilas empiezan vacías). Deshacer y rehacer también quedan en el historial con su autor.
- **Lock:** archivo hermano `<nombre>.hestia.lock` creado con `O_EXCL`, con pid, host, usuario e id de instancia. Un lock de un proceso muerto en el mismo host se toma sin preguntar; cualquier otro bloquea la apertura (HTTP 423) salvo que el usuario fuerce la toma.
- **Recientes:** `~/.hestia/recents.json` (o `$HESTIA_HOME`), máximo 12, más nuevo primero. Al listarlos se marca si el archivo todavía existe.

## Consecuencias

- Abrir, guardar y cerrar son operaciones de archivo: no entran en el historial ni piden justificación. Cerrar o reemplazar un proyecto con cambios sin guardar falla (`unsaved_changes`) salvo `discard_unsaved`.
- Reescribir el archivo completo es barato mientras el proyecto sea chico. Cuando haya resultados pesados habrá que decidir si van en tablas del mismo SQLite (y guardar incremental) o en una carpeta hermana. TODO.
- Sin autoguardado un cierre inesperado pierde los cambios desde el último guardado. TODO: evaluar un archivo de recuperación.
- Un cambio incompatible de las tablas o de los modelos exige subir `SCHEMA_VERSION` y escribir la migración de lectura.
