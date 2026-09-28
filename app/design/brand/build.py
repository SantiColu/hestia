# /// script
# requires-python = ">=3.12"
# dependencies = ["fonttools", "brotli", "uharfbuzz"]
# ///
"""Build the Hestia brand assets from the mark geometry.

Writes the SVG sources next to this file, the browser favicon to app/public and
the desktop icon set to app/src-tauri/icons. Needs `rsvg-convert`, ImageMagick
(`magick`) and the app dependencies installed (`pnpm install`, for Inter and the
Tauri CLI).

    uv run app/design/brand/build.py
"""

import io
import shutil
import subprocess
import tempfile
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

BRAND = Path(__file__).resolve().parent
APP = BRAND.parents[1]
ICONS = APP / "src-tauri" / "icons"
FONT = APP / "node_modules/@fontsource-variable/inter/files/inter-latin-opsz-normal.woff2"

# Graphite tokens (app/src/styles.css): --text, --hot, --surface, --border.
FG, HOT, SURFACE, BORDER = "#E4E7EB", "#EC7A48", "#161A20", "#272D36"

# Mark geometry in cap-height units: 100 tall, 88 wide. Two solar arrays tilted
# toward the sun, a boom, and the bus (the hearth) at the center.
MARK_W, MARK_H = 88, 100
TRACKING = -0.01  # em, logotype
GAP = 16  # mark to first glyph ink, cap-height units


def mark(fg: str, hot: str) -> str:
    def panel(x: float) -> str:
        return f"M{x} 8L{x + 20} 0V92L{x} 100Z"

    return (
        f'<path fill="{fg}" d="{panel(0)}{panel(68)}M20 46.5H68V53.5H20Z"/>'
        f'<path fill="{hot}" d="M33 39H55V61H33Z"/>'
    )


def mark_32px(fg: str, hot: str) -> str:
    """Pixel-snapped mark for a 32 px canvas (also used for the favicon)."""
    return (
        f'<path fill="{fg}" d="M6 7L11 5V25L6 27ZM21 7L26 5V25L21 27ZM11 15H21V17H11Z"/>'
        f'<path fill="{hot}" d="M13 13H19V19H13Z"/>'
    )


def mark_16px(fg: str, hot: str) -> str:
    """Pixel-snapped mark for a 16 px canvas."""
    return (
        f'<path fill="{fg}" d="M2 3L5 2V13L2 14ZM11 3L14 2V13L11 14ZM5 7H11V9H5Z"/>'
        f'<path fill="{hot}" d="M6 6H10V10H6Z"/>'
    )


def placed(body: str, cx: float, cy: float, height: float) -> str:
    k = height / MARK_H
    x, y = cx - MARK_W * k / 2, cy - height / 2
    return f'<g transform="translate({x:g} {y:g}) scale({k:g})">{body}</g>'


def svg(view_box: str, body: str) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}">{body}</svg>\n'


def fmt(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def estia_paths() -> tuple[str, tuple[float, float, float, float]]:
    """Shape "estia" in Inter Display SemiBold after the mark, as SVG path data."""
    font = instancer.instantiateVariableFont(TTFont(FONT), {"opsz": 32, "wght": 600})
    font.flavor = None
    buf = io.BytesIO()
    font.save(buf)
    data = buf.getvalue()
    font = TTFont(io.BytesIO(data))
    glyph_set, order = font.getGlyphSet(), font.getGlyphOrder()

    def bounds(name: str, transform=(1, 0, 0, 1, 0, 0)):
        pen = BoundsPen(glyph_set)
        glyph_set[name].draw(TransformPen(pen, transform))
        return pen.bounds

    cap = bounds(font.getBestCmap()[ord("H")])[3]
    s = MARK_H / cap
    upm = font["head"].unitsPerEm

    shaped = hb.Buffer()
    shaped.add_str("estia")
    shaped.guess_segment_properties()
    hb.shape(hb.Font(hb.Face(data)), shaped, {"kern": True})

    x = MARK_W + GAP - bounds(order[shaped.glyph_infos[0].codepoint])[0] * s
    d, box = [], [0.0, 0.0, float(MARK_W), float(MARK_H)]
    for info, pos in zip(shaped.glyph_infos, shaped.glyph_positions, strict=True):
        name = order[info.codepoint]
        transform = (s, 0, 0, -s, x + pos.x_offset * s, MARK_H - pos.y_offset * s)
        pen = SVGPathPen(glyph_set, ntos=fmt)
        glyph_set[name].draw(TransformPen(pen, transform))
        d.append(pen.getCommands())
        if b := bounds(name, transform):
            box = [min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3])]
        x += pos.x_advance * s + TRACKING * upm * s
    return "".join(d), (box[0], box[1], box[2] - box[0], box[3] - box[1])


def app_icon() -> str:
    # macOS grid: 824 px rounded tile centered on a 1024 canvas.
    return (
        f'<rect x="102" y="102" width="820" height="820" rx="184" fill="{SURFACE}" '
        f'stroke="{BORDER}" stroke-width="4"/>' + placed(mark(FG, HOT), 512, 512, 470)
    )


def render(src: Path, dst: Path, size: int) -> None:
    subprocess.run(
        ["rsvg-convert", str(src), "-w", str(size), "-h", str(size), "-o", str(dst)], check=True
    )


def main() -> None:
    text, box = estia_paths()
    logo_box = " ".join(fmt(v) for v in box)
    files = {
        "hestia-mark.svg": svg(f"0 0 {MARK_W} {MARK_H}", mark(FG, HOT)),
        "hestia-mark-mono.svg": svg(f"0 0 {MARK_W} {MARK_H}", mark("currentColor", "currentColor")),
        "hestia-logo.svg": svg(logo_box, mark(FG, HOT) + f'<path fill="{FG}" d="{text}"/>'),
        "hestia-logo-mono.svg": svg(
            logo_box,
            mark("currentColor", "currentColor") + f'<path fill="currentColor" d="{text}"/>',
        ),
        "hestia-app-icon.svg": svg("0 0 1024 1024", app_icon()),
        "hestia-icon-32.svg": svg(
            "0 0 32 32",
            f'<rect width="32" height="32" rx="7" fill="{SURFACE}"/>' + mark_32px(FG, HOT),
        ),
        "hestia-icon-16.svg": svg(
            "0 0 16 16",
            f'<rect width="16" height="16" rx="3.5" fill="{SURFACE}"/>' + mark_16px(FG, HOT),
        ),
    }
    for name, content in files.items():
        (BRAND / name).write_text(content)
    shutil.copyfile(BRAND / "hestia-icon-32.svg", APP / "public" / "favicon.svg")

    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        render(BRAND / "hestia-app-icon.svg", t / "app-icon.png", 1024)
        subprocess.run(
            ["pnpm", "tauri", "icon", str(t / "app-icon.png"), "-o", str(t / "icons")],
            cwd=APP,
            check=True,
        )
        # Keep the desktop set only (the repo has no Android/iOS targets).
        for existing in ICONS.glob("*"):
            generated = t / "icons" / existing.name
            if existing.is_file() and generated.is_file():
                shutil.copyfile(generated, existing)

        # Tiny sizes: full-bleed tile with the pixel-snapped mark instead of the
        # padded macOS tile, which would leave a few illegible pixels.
        full = svg(
            "0 0 100 100",
            f'<rect width="100" height="100" rx="22" fill="{SURFACE}"/>'
            + placed(mark(FG, HOT), 50, 50, 62),
        )
        (t / "full.svg").write_text(full)
        sizes = {16: BRAND / "hestia-icon-16.svg", 32: BRAND / "hestia-icon-32.svg"}
        pngs = []
        for size in (16, 24, 32, 48, 64, 256):
            png = t / f"{size}.png"
            render(sizes.get(size, t / "full.svg"), png, size)
            pngs.append(str(png))
        shutil.copyfile(t / "32.png", ICONS / "32x32.png")
        subprocess.run(["magick", *pngs, str(ICONS / "icon.ico")], check=True)


if __name__ == "__main__":
    main()
