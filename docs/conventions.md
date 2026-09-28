# Convenciones

## Idioma

- Código, identificadores, comentarios, docstrings, mensajes de commit: **inglés**.
- Documentación (`docs/`, READMEs, `AGENTS.md`, ADRs): **español**.

## Unidades

- Internamente **SI** en todo el backend, la API y el MCP.
- Temperaturas en **Kelvin** internamente y en la API. La UI muestra **°C** (conversión solo en presentación).
- Cuando la unidad no es obvia, sufijo en el nombre: `power_w`, `area_m2`, `temperature_k`, `conductance_w_per_k`, `angle_rad`.
- Ángulos en radianes internamente salvo que un ADR diga lo contrario.

## Nombres

- Etapas: snake_case inglés (`mission`, `global_balance`, `load_cases`…). El número (0.1, 1.3…) es metadato, nunca parte del id.
- Python: PEP 8 (ruff). Paquetes `hestia_<capa>`; distribuciones `hestia-<capa>`.
- TypeScript: camelCase para variables, PascalCase para componentes y tipos.

## Artefactos y contrato

- Todo artefacto tiene esquema versionado (campo de versión en el modelo pydantic).
- Los modelos pydantic son la fuente de verdad; OpenAPI y el cliente TS se generan.
- `shared/openapi.json` no se edita a mano.

## Cambios

- Toda escritura (web o MCP) registra autor y justificación.
- Todo cálculo físico nuevo lleva test contra referencia citada, con tolerancia explícita.
- Decisiones de arquitectura → ADR en `docs/adr/`.

## Estilo

- Python: ruff (lint + format), pyright strict, línea de 100.
- Web: ESLint + Prettier, TypeScript strict.
- `.editorconfig` en la raíz.
