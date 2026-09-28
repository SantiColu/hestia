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
FONTS = APP / "node_modules/@fontsource-variable"
INTER = FONTS / "inter/files/inter-latin-opsz-normal.woff2"
MONO = FONTS / "jetbrains-mono/files/jetbrains-mono-latin-wght-normal.woff2"

# Graphite tokens (app/src/styles.css): --text, --hot, --surface, --border.
FG, HOT, SURFACE, BORDER = "#E4E7EB", "#EC7A48", "#161A20", "#272D36"
BG = "#0F1216"  # --bg
MUTED = "#98A0AC"  # --text-muted
SUBTLE = "#667080"  # --subtle-foreground
SURFACE_2, BORDER_STRONG = "#1D222A", "#38404B"
TAGLINE = "Prediseño del control térmico de satélites"

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


def shape(text: str, font: Path, axes: dict[str, int], x: float) -> tuple[str, list[float]]:
    """Shape `text` in a variable `font` as SVG path data, cap height 100, baseline at y = 100.

    `x` is where the first glyph's ink starts. Returns the path data and the ink
    box as [x0, y0, x1, y1].
    """
    font = instancer.instantiateVariableFont(TTFont(font), axes)
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
    shaped.add_str(text)
    shaped.guess_segment_properties()
    hb.shape(hb.Font(hb.Face(data)), shaped, {"kern": True})

    x -= bounds(order[shaped.glyph_infos[0].codepoint])[0] * s
    d, box = [], [x, 0.0, x, float(MARK_H)]
    for info, pos in zip(shaped.glyph_infos, shaped.glyph_positions, strict=True):
        name = order[info.codepoint]
        transform = (s, 0, 0, -s, x + pos.x_offset * s, MARK_H - pos.y_offset * s)
        pen = SVGPathPen(glyph_set, ntos=fmt)
        glyph_set[name].draw(TransformPen(pen, transform))
        d.append(pen.getCommands())
        if b := bounds(name, transform):
            box = [min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3])]
        x += pos.x_advance * s + TRACKING * upm * s
    return "".join(d), box


def estia_paths() -> tuple[str, tuple[float, float, float, float]]:
    """Shape "estia" in Inter Display SemiBold after the mark, as SVG path data."""
    d, b = shape("estia", INTER, {"opsz": 32, "wght": 600}, MARK_W + GAP)
    box = [min(0, b[0]), min(0, b[1]), max(MARK_W, b[2]), max(MARK_H, b[3])]
    return d, (box[0], box[1], box[2] - box[0], box[3] - box[1])


def label(text: str, cx: float, baseline: float, rotate: bool = False) -> str:
    """Dimension label in JetBrains Mono, 9 px cap height, centered on `cx`."""
    d, box = shape(text, MONO, {"wght": 400}, 0)
    k = 9 / MARK_H
    x, y = cx - (box[2] - box[0]) * k / 2, baseline - 9
    g = f'<path fill="{SUBTLE}" d="{d}"/>'
    t = f"translate({fmt(x)} {fmt(y)}) scale({fmt(k)})"
    if rotate:
        t = f"rotate(-90 {fmt(cx)} {fmt(baseline - 4.5)}) {t}"
    return f'<g transform="{t}">{g}</g>'


def banner(logo: str, logo_box: tuple[float, float, float, float]) -> str:
    """README banner: the logo on a drawing grid, dimensioned in cap-height units."""
    w, h, r = 1280, 320, 12
    tag, tag_box = shape(TAGLINE, INTER, {"opsz": 14, "wght": 400}, 0)
    k, tag_k = 72 / MARK_H, 17 / MARK_H  # cap heights in px
    logo_w, tag_w = logo_box[2] * k, (tag_box[2] - tag_box[0]) * tag_k
    x0, top, tag_y = (w - logo_w) / 2 - logo_box[0] * k, 98, 206  # cap tops
    bottom = top + MARK_H * k

    # Grid: 32 px cells, a stronger line every 4, centered on the banner.
    cx, cy = w / 2, h / 2
    minor, major = [], []
    for i in range(-20, 21):
        for pos, lim, horiz in ((cx + 32 * i, w, False), (cy + 32 * i, h, True)):
            if 0 < pos < lim:
                line = f"M0 {pos + 0.5:g}H{w}" if horiz else f"M{pos + 0.5:g} 0V{h}"
                (major if i % 4 == 0 else minor).append(line)
    grid = (
        f'<path stroke="{SURFACE}" d="{"".join(minor)}"/>'
        f'<path stroke="{SURFACE_2}" d="{"".join(major)}"/>'
    )

    # Dimensions: chained widths above (mark, gap, text), cap height at the left.
    stops = [x0, x0 + MARK_W * k, x0 + (MARK_W + GAP) * k, x0 + logo_w]
    values = [MARK_W, GAP, round(logo_box[2]) - MARK_W - GAP]
    dim_y, ext_x = top - 22, x0 - 26

    def tick(x: float, y: float) -> str:
        return f"M{fmt(x - 3)} {fmt(y + 3)}L{fmt(x + 3)} {fmt(y - 3)}"

    lines = [f"M{fmt(stops[0])} {fmt(dim_y)}H{fmt(stops[-1])}"]
    lines += [f"M{fmt(x)} {fmt(top - 30)}V{fmt(top - 6)}" + tick(x, dim_y) for x in stops]
    lines += [f"M{fmt(ext_x - 8)} {fmt(y)}H{fmt(x0 - 6)}" + tick(ext_x, y) for y in (top, bottom)]
    lines.append(f"M{fmt(ext_x)} {fmt(top)}V{fmt(bottom)}")
    labels = [
        label(str(v), (a + b) / 2, dim_y - 7)
        for v, a, b in zip(values, stops, stops[1:], strict=False)
    ]
    labels.append(label(str(MARK_H), ext_x - 8, (top + bottom) / 2 + 4.5, rotate=True))

    # Registration crosses in the corners.
    cross = "".join(
        f"M{fmt(x - 5)} {fmt(y)}H{fmt(x + 5)}M{fmt(x)} {fmt(y - 5)}V{fmt(y + 5)}"
        for x in (24, w - 24)
        for y in (24, h - 24)
    )

    return (
        f'<defs><clipPath id="plate"><rect width="{w}" height="{h}" rx="{r}"/></clipPath></defs>'
        f'<rect width="{w}" height="{h}" rx="{r}" fill="{BG}"/>'
        f'<g clip-path="url(#plate)" fill="none" stroke-width="1">{grid}</g>'
        f'<path fill="none" stroke="{BORDER_STRONG}" d="{"".join(lines)}{cross}"/>'
        + "".join(labels)
        + f'<g transform="translate({fmt(x0)} {fmt(top)}) scale({fmt(k)})">{logo}</g>'
        f'<g transform="translate({fmt((w - tag_w) / 2)} {fmt(tag_y)}) scale({fmt(tag_k)})">'
        f'<path fill="{MUTED}" d="{tag}"/></g>'
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="{r - 0.5}" fill="none" '
        f'stroke="{BORDER}"/>'
    )


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
        "hestia-banner.svg": svg(
            "0 0 1280 320", banner(mark(FG, HOT) + f'<path fill="{FG}" d="{text}"/>', box)
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
