---
name: clean-code-review
description: Autorrevisión de calidad antes de dar por terminado un cambio en Hestia (backend, mcp o app) — lint y tests, duplicación, código muerto, nombres, tipos del contrato, supresiones, Tailwind, documentación. Usala al final de toda tarea que toque código, antes de reportar que está hecha o de commitear.
---

# Revisión de código limpio

Reglas de referencia: `docs/conventions.md` («Código limpio»). Esta skill es el procedimiento para aplicarlas sobre tu propio cambio.

## 1. Verificación automática (obligatoria)

```sh
make lint   # ruff, pyright, import-linter, eslint (incl. Tailwind), prettier, cargo
make test   # pytest backend y mcp
```

Si algo falla, el cambio no está terminado. No relajes una regla ni agregues una supresión para pasar: arreglá el código. Si la supresión es legítima, lleva regla y motivo (`// eslint-disable-next-line <regla> -- <motivo>`, `# noqa: <código>  # <motivo>`).

## 2. Revisar el diff

Leé `git diff` completo (y los archivos nuevos) como lo haría un revisor:

- **Duplicación.** Por cada función o helper nuevo, buscá si ya existe algo equivalente: `rg -n "function <verbo>|def <verbo>"`, `rg "<fragmento de lógica>"`. En la app, mirá primero `src/lib/`, `src/project/lookup.ts` y `src/components/`. En el backend, `hestia_project.schematic` (lookups, `clean_name`), `hestia_core.forms`, `hestia_project.errors`.
- **Código muerto.** Nada comentado, ni exports o componentes sin uso (`rg -n "<Nombre>"` fuera de su archivo), ni ramas imposibles, ni `TODO` resolubles ahora.
- **Nombres y constantes.** Nombres que dicen qué es; números con nombre y unidad (`_MS`, `_M`, `_K`); sin literales de diseño sueltos.
- **Tamaño.** Funciones y componentes de un solo nivel de abstracción; más de ~150 líneas o lógica anidada en JSX → extraer subcomponente o helper puro. Nada de funciones declaradas después de un `return`.
- **Tipos.** Python: firmas completas, sin `Any` gratuito. TS: tipos de `@/api/client`, sin `any`, `as never`, `!` ni tipos del contrato redefinidos a mano.
- **Errores.** Nada de `except:`/`catch {}` silenciosos sin comentario del porqué; errores de dominio con `code` estable.
- **Capas y principios.** La UI no decide reglas del workflow ni calcula física; el MCP solo llama a la API; todo resultado físico sale de `hestia_core` con test contra referencia (skill `physics-validation`).
- **UI.** Sin valores arbitrarios de Tailwind (skill `ui-styling`), componentes reutilizados, textos en español sin números de etapa, `aria-label` en botones de solo ícono.
- **Tests.** Comportamiento nuevo → test nuevo; sin fixtures o parámetros sin usar.

## 3. Documentación

- ¿Cambió la estructura de un módulo (archivo nuevo, helper compartido, regla nueva)? Actualizá la sección «Estructura» del `AGENTS.md` del módulo.
- ¿Una decisión de arquitectura, contrato o convención global? ADR (skill `write-adr`).
- ¿Una convención nueva de código? `docs/conventions.md` y, si es verificable, una regla de lint.
- ¿Cambió la API? Skill `add-api-operation` (contrato, cliente TS, tool MCP, paridad).

## 4. Errores frecuentes (vistos en revisiones anteriores)

| Error | En su lugar |
|---|---|
| `text-[13px]`, `w-[232px]`, `h-[30px]` | `text-ui`, `w-58`, `h-7.5` |
| Token nuevo solo en `styles.css` | También en `createCn` (`src/lib/utils.ts`) |
| `listNames` en una pantalla y `joinList` en otra | Un helper en `src/lib/format.ts` |
| `new Intl.DateTimeFormat(...)` repetido por pantalla | `timeFormat` / `dateFormat` de `@/lib/format` |
| `project.cells.find((c) => c.id === id)` en cada archivo | `findCell(project, id)` de `@/project/lookup` |
| `error instanceof ApiError && error.code === "x"` | `isApiError(error, "x")` |
| Tipo del contrato copiado a mano con `TODO` | El tipo generado de `@/api/client` |
| `stage as never` para pasar el tipado | Tipar bien la variable (`StageType`) |
| Dos funciones que hacen el mismo `PUT` con variantes | Una función parametrizada |
| Ternario cuyas dos ramas devuelven lo mismo | Simplificar la condición |
| `style={{ gridTemplateColumns: … }}` con valores fijos | Mapa de clases estáticas |
| Componente de ejemplo que ya no está en el diseño | Borrarlo (y del catálogo `/dev`) |
| `eslint-disable` sin motivo | `-- <motivo>` o arreglar el código |
| `os.replace`, `open()` sobre rutas `str` | `Path.replace`, `Path.read_text` |

## 5. Reporte

Al terminar, decí qué verificaste (`make lint`, `make test`, revisión visual si hubo UI) y qué quedó fuera o pendiente. No commitees salvo que te lo pidan; cuando sí, seguí la convención de commits de `docs/conventions.md`.
