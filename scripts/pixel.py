"""Pixel-art SVG primitives: a 5x7 bitmap font, sprites, and window frames.

Everything is drawn with axis-aligned rects/paths on an integer grid so the
output stays crisp at any zoom (`shape-rendering="crispEdges"`).
"""

from __future__ import annotations

from html import escape

U = 4  # one "art pixel" for frames and decorations

# Palette ---------------------------------------------------------------
INK = "#F4F1FF"
DIM = "#9A96CF"
OUTLINE = "#07060F"
PANEL = "#1B1838"
SLOT = "#13112A"
LINE = "#2E2A5C"
LIGHT = "#4E48A0"
GREEN = "#3EDD3A"
GREEN_HI = "#7CF56E"
GREEN_DK = "#1CA31C"
YELLOW = "#FFD447"
ORANGE = "#FF8C42"
PINK = "#FF5E8A"
CYAN = "#5CE1E6"
PURPLE = "#A78BFA"

# 5x7 font -------------------------------------------------------------
_GLYPHS = {
    "A": ".###.|#...#|#...#|#####|#...#|#...#|#...#",
    "B": "####.|#...#|#...#|####.|#...#|#...#|####.",
    "C": ".###.|#...#|#....|#....|#....|#...#|.###.",
    "D": "####.|#...#|#...#|#...#|#...#|#...#|####.",
    "E": "#####|#....|#....|####.|#....|#....|#####",
    "F": "#####|#....|#....|####.|#....|#....|#....",
    "G": ".###.|#...#|#....|#.###|#...#|#...#|.####",
    "H": "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    "I": ".###.|..#..|..#..|..#..|..#..|..#..|.###.",
    "J": "..###|...#.|...#.|...#.|...#.|#..#.|.##..",
    "K": "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#",
    "L": "#....|#....|#....|#....|#....|#....|#####",
    "M": "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#",
    "N": "#...#|#...#|##..#|#.#.#|#..##|#...#|#...#",
    "O": ".###.|#...#|#...#|#...#|#...#|#...#|.###.",
    "P": "####.|#...#|#...#|####.|#....|#....|#....",
    "Q": ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#",
    "R": "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
    "S": ".####|#....|#....|.###.|....#|....#|####.",
    "T": "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    "U": "#...#|#...#|#...#|#...#|#...#|#...#|.###.",
    "V": "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
    "W": "#...#|#...#|#...#|#.#.#|#.#.#|#.#.#|.#.#.",
    "X": "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    "Y": "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..",
    "Z": "#####|....#|...#.|..#..|.#...|#....|#####",
    "0": ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.",
    "1": "..#..|.##..|..#..|..#..|..#..|..#..|.###.",
    "2": ".###.|#...#|....#|...#.|..#..|.#...|#####",
    "3": "#####|...#.|..#..|...#.|....#|#...#|.###.",
    "4": "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.",
    "5": "#####|#....|####.|....#|....#|#...#|.###.",
    "6": "..##.|.#...|#....|####.|#...#|#...#|.###.",
    "7": "#####|....#|...#.|..#..|.#...|.#...|.#...",
    "8": ".###.|#...#|#...#|.###.|#...#|#...#|.###.",
    "9": ".###.|#...#|#...#|.####|....#|...#.|.##..",
    " ": "...|...|...|...|...|...|...",
    ".": ".|.|.|.|.|.|#",
    ",": "..|..|..|..|..|.#|#.",
    "!": "#|#|#|#|#|.|#",
    "?": ".###.|#...#|....#|...#.|..#..|.....|..#..",
    "'": "#|#|.|.|.|.|.",
    ":": ".|.|#|.|.|#|.",
    "-": "...|...|...|###|...|...|...",
    "+": ".....|..#..|..#..|#####|..#..|..#..|.....",
    "/": "....#|...#.|...#.|..#..|.#...|.#...|#....",
    "#": ".#.#.|.#.#.|#####|.#.#.|#####|.#.#.|.#.#.",
    "&": ".##..|#..#.|#.#..|.#...|#.#.#|#..#.|.##.#",
    "@": ".###.|#...#|#.###|#.#.#|#.###|#....|.###.",
    "_": ".....|.....|.....|.....|.....|.....|#####",
    "(": "..#|.#.|#..|#..|#..|.#.|..#",
    ")": "#..|.#.|..#|..#|..#|.#.|#..",
    "%": "##..#|##..#|...#.|..#..|.#...|#..##|#..##",
    "=": ".....|.....|#####|.....|#####|.....|.....",
    "·": "...|...|...|.#.|...|...|...",
    "▶": "#....|##...|###..|####.|###..|##...|#....",
    "▼": ".......|#######|.#####.|..###..|...#...|.......|.......",
}
FONT = {ch: rows.split("|") for ch, rows in _GLYPHS.items()}
FONT_H = 7

# 7x7 icons sized to sit on a text line.
ICONS7 = {
    "heart": ".##.##.|#######|#######|#######|.#####.|..###..|...#...",
    "gem": "...#...|..###..|.#####.|#######|.#####.|..###..|...#...",
    "star": "...#...|..###..|#######|.#####.|..###..|.##.##.|.#...#.",
    "flag": "######.|#######|######.|#......|#......|#......|#......",
    "chest": ".#####.|#######|#######|###.###|#######|#######|#######",
    "person": "..###..|..###..|..###..|.......|.#####.|#######|#######",
    "globe": "..###..|.#.#.#.|#..#..#|#######|#..#..#|.#.#.#.|..###..",
    "mail": ".......|#######|##...##|#.#.#.#|#..#..#|#######|.......",
    "linkedin": "#######|#.#####|#######|#.#...#|#.#.#.#|#.#.#.#|#######",
    "note": "...###.|...#..#|...#...|...#...|.###...|#..#...|.##....",
    "camera": ".#####.|#....##|#.###.#|#.#.#.#|#.###.#|#.....#|.#####.",
}
ICONS7 = {k: v.split("|") for k, v in ICONS7.items()}


def text_width(s: str, scale: int) -> int:
    s = s.upper()
    if not s:
        return 0
    return (sum(len(FONT[ch][0]) for ch in s) + len(s) - 1) * scale


def _runs(rows: list[str], ox: int, oy: int, scale: int, row_filter=None) -> list[str]:
    parts = []
    for ry, row in enumerate(rows):
        if row_filter is not None and ry not in row_filter:
            continue
        rx = 0
        while rx < len(row):
            if row[rx] == "#":
                start = rx
                while rx < len(row) and row[rx] == "#":
                    rx += 1
                parts.append(f"M{ox + start * scale} {oy + ry * scale}h{(rx - start) * scale}v{scale}h-{(rx - start) * scale}z")
            else:
                rx += 1
    return parts


def text_d(s: str, x: int, y: int, scale: int, row_filter=None) -> str:
    """Path data for `s` with its top-left at (x, y)."""
    parts: list[str] = []
    cx = x
    for ch in s.upper():
        rows = FONT[ch]
        parts += _runs(rows, cx, y, scale, row_filter)
        cx += (len(rows[0]) + 1) * scale
    return "".join(parts)


def text(s: str, x: int, y: int, scale: int, fill: str, anchor: str = "start", shadow: str | None = None, cls: str = "") -> str:
    w = text_width(s, scale)
    if anchor == "middle":
        x -= w // 2
    elif anchor == "end":
        x -= w
    attr = f' class="{cls}"' if cls else ""
    out = ""
    if shadow:
        out += f'<path fill="{shadow}" d="{text_d(s, x + scale, y + scale, scale)}"/>'
    out += f'<path fill="{fill}" d="{text_d(s, x, y, scale)}"/>'
    return f"<g{attr}>{out}</g>" if cls else out


def gradient_text(s: str, x: int, y: int, scale: int, bands: list[tuple[range, str]], shadow: str | None = None) -> str:
    """Arcade-style title: each glyph row band gets its own color."""
    out = ""
    if shadow:
        out += f'<path fill="{shadow}" d="{text_d(s, x + scale, y + scale, scale)}"/>'
    for rows, color in bands:
        out += f'<path fill="{color}" d="{text_d(s, x, y, scale, set(rows))}"/>'
    return out


def icon7(name: str, x: int, y: int, scale: int, fill: str) -> str:
    return f'<path fill="{fill}" d="{"".join(_runs(ICONS7[name], x, y, scale))}"/>'


def grid_art(grid: list[str], palette: dict[str, str], x: int, y: int, scale: int) -> str:
    """Multi-color pixel art; one <path> per palette color."""
    out = ""
    for code, color in palette.items():
        rows = ["".join("#" if c == code else "." for c in row) for row in grid]
        d = "".join(_runs(rows, x, y, scale))
        if d:
            out += f'<path fill="{color}" d="{d}"/>'
    return out


def rect(x: int, y: int, w: int, h: int, fill: str, extra: str = "") -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"{extra}/>'


def notched(x: int, y: int, w: int, h: int, fill: str, n: int = U, extra: str = "") -> str:
    """Rectangle with its corner pixels knocked out."""
    return f'<path fill="{fill}"{extra} d="M{x + n} {y}h{w - 2 * n}v{n}h{n}v{h - 2 * n}h-{n}v{n}h-{w - 2 * n}v-{n}h-{n}v-{h - 2 * n}h{n}z"/>'


def window(x: int, y: int, w: int, h: int, fill: str = PANEL, shadow: bool = True) -> str:
    """Beveled pixel window: outline, light top-left edge, dark bottom-right edge."""
    out = notched(x + U, y + U, w, h, "#000", extra=' fill-opacity=".35"') if shadow else ""
    out += notched(x, y, w, h, OUTLINE)
    out += rect(x + U, y + U, w - 2 * U, h - 2 * U, LINE)
    out += rect(x + U, y + U, w - 3 * U, h - 3 * U, LIGHT)
    out += rect(x + 2 * U, y + 2 * U, w - 4 * U, h - 4 * U, fill)
    return out


def sunken(x: int, y: int, w: int, h: int, fill: str = SLOT) -> str:
    """Inset slot: dark top-left edge, light bottom-right edge."""
    return (
        rect(x, y, w, h, LIGHT)
        + rect(x, y, w - 2, h - 2, OUTLINE)
        + rect(x + 2, y + 2, w - 4, h - 4, fill)
    )


def tab(label: str, x: int, y: int, fill: str = GREEN, ink: str = OUTLINE) -> str:
    """Title plate that overlaps the top edge of a window."""
    w = text_width(label, 2) + 6 * U
    return notched(x, y, w, 8 * U, OUTLINE) + rect(x + U, y + U, w - 2 * U, 6 * U, fill) + rect(x + U, y + 6 * U, w - 2 * U, U, "#000", ' fill-opacity=".18"') + text(label, x + 3 * U, y + 9, 2, ink)


def svg(w: int, h: int, title: str, body: str, style: str = "") -> str:
    reduce = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'shape-rendering="crispEdges" role="img" aria-labelledby="title">'
        f'<title id="title">{escape(title)}</title>'
        f"<style>{style}{reduce}</style>{body}</svg>\n"
    )
