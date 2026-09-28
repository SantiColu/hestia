# Marca

<img src="hestia-app-icon.svg" width="96" alt="Ícono de Hestia" />

La marca es una H que también es un satélite: dos paneles solares inclinados hacia el sol, un brazo y el bus en el centro, en brasa. Hestia es la diosa del hogar, y el hogar es el núcleo que el control térmico mantiene caliente. En el logotipo la marca reemplaza a la H: **Hestia** se escribe marca + `estia`.

## Archivos

| Archivo                                    | Uso                                                                        |
| ------------------------------------------ | -------------------------------------------------------------------------- |
| `hestia-mark.svg`                          | Marca a color, fondo transparente. Solo sobre fondos oscuros.              |
| `hestia-mark-mono.svg`                     | Marca en un color (`currentColor`). Para cualquier fondo.                  |
| `hestia-logo.svg`                          | Logotipo a color (marca + `estia`, texto en curvas).                       |
| `hestia-logo-mono.svg`                     | Logotipo en un color (`currentColor`).                                     |
| `hestia-app-icon.svg`                      | Ícono de app (1024, grilla de macOS). Fuente de `src-tauri/icons/`.        |
| `hestia-icon-32.svg`, `hestia-icon-16.svg` | Ícono ajustado al píxel para 32 y 16 px. El de 32 es `public/favicon.svg`. |
| `build.py`                                 | Genera todo lo anterior, el favicon y los íconos de Tauri.                 |

## Construcción

Unidad: la altura de mayúscula = 100. La marca mide 88 × 100.

- Paneles: 20 de ancho, cortados en diagonal con 8 de desnivel (arriba sube hacia la derecha, abajo baja hacia la izquierda).
- Brazo: 7 de alto, centrado.
- Núcleo: cuadrado de 22, centrado en la marca. Es el único elemento en brasa.
- Logotipo: `estia` en Inter Display SemiBold (opsz 32, wght 600), tracking −1 %, a 16 unidades de la marca. La marca mide exactamente la altura de mayúscula de Inter.
- Por debajo de 24 px de alto la marca pierde el brazo: usar `hestia-icon-32.svg` o `hestia-icon-16.svg`, dibujados sobre la grilla de píxeles.

## Color

| Token Graphite | Hex       | Uso en la marca       |
| -------------- | --------- | --------------------- |
| `--text`       | `#E4E7EB` | Paneles, brazo, texto |
| `--hot`        | `#EC7A48` | Núcleo                |
| `--surface`    | `#161A20` | Placa del ícono       |
| `--border`     | `#272D36` | Borde del ícono       |

## Uso

- Fondos oscuros. Sobre fondos claros, la versión mono en `#0F1216`.
- Área de resguardo: 25 unidades (un cuarto de la altura) alrededor de la marca o del logotipo.
- No deformar, rotar ni recolorear las piezas. El núcleo es brasa o del mismo color que el resto, nunca otro.
- No separar la marca de `estia` ni escribir «H Hestia»: la marca ya es la H.
- Sin sombras, glow, gradientes ni contornos.

## Regenerar

Requiere `rsvg-convert`, ImageMagick (`magick`) y las dependencias de la app (`pnpm install`, para Inter y la CLI de Tauri). Desde la raíz del repo:

```sh
uv run app/design/brand/build.py
```

Sobrescribe los SVG de esta carpeta, `app/public/favicon.svg` y el set de escritorio de `app/src-tauri/icons/`. En `icon.ico` y `32x32.png` usa las variantes ajustadas al píxel.
