# 0008. Aplicación de escritorio local; el proyecto es un archivo

- **Estado:** aceptado
- **Fecha:** 2026-09-28
- **Reemplaza parcialmente:** 0004 (frontend Next.js)

## Contexto

Se quiere trabajar como en Ansys o Pencil: guardar un proyecto en un lugar local y volver a abrirlo. El valor de Next.js es su servidor (SSR, route handlers, server actions), que por principio no usamos para lógica. Una versión web multiusuario no es necesaria por ahora.

## Decisión

- Hestia es una **aplicación de escritorio local**. La versión web se reevalúa si el proyecto escala.
- **Frontend:** React + Vite + TanStack Router, compilado a estáticos, sin servidor Node. Componentes sin cambios (ADR 0007).
- **Shell:** Tauri 2. Antes de consolidarlo, validar rendimiento de WebKitGTK (Linux) con React Flow y Plotly; Electron es la alternativa si falla.
- **Backend:** FastAPI como proceso sidecar en `127.0.0.1`, puerto aleatorio y token por sesión. Sigue siendo el único dueño del dominio y del estado.
- **MCP:** sigue siendo cliente HTTP de esa API. Descubre puerto y token mediante un archivo de instancia (p. ej. `~/.hestia/instance.json`).
- **Proyecto = un archivo SQLite** (`.hestia`) con entradas, artefactos versionados, resultados y log de cambios (extiende ADR 0006). Abrir, Guardar, Guardar como (API de backup de SQLite), proyectos recientes y lock contra doble apertura.

## Consecuencias

- La arquitectura de capas, el contrato OpenAPI y la paridad humano-agente no cambian.
- Rutas solo del lado del cliente; nada de rutas dinámicas de servidor.
- Hay que empaquetar Python y un JRE mínimo (Orekit) por sistema operativo, firmar binarios y resolver actualizaciones. TODO: herramienta (PyInstaller o Nuitka) y `jlink`.
- TODO: formato interno del archivo, dónde van los resultados pesados (dentro del SQLite o en carpeta hermana) y semántica de autoguardado frente a guardado explícito.
- Colaboración multiusuario en tiempo real queda fuera de alcance mientras el proyecto sea un archivo local.
