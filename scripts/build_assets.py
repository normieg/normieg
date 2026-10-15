"""Build the raster/pixel source assets that render.py embeds.

One-off tool (not run in CI). Requires: pip install pillow resvg-py

    python scripts/build_assets.py --sprite path/to/grey-walk.webp \
        --head path/to/head-64.png

Outputs (committed):
    assets/grey-sheet.png   animation frames, quantized, nearest-upscaled 2x
    assets/grey-head.png    dialog portrait, nearest-upscaled 2x
    assets/icons.json       16x16 pixel icons for the inventory panel
"""

from __future__ import annotations

import argparse
import io
import json
import math
import urllib.request
from pathlib import Path

import resvg_py
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

FRAME_DOWNSCALE = 5  # source sprite is drawn on a ~5px grid
SHEET_UPSCALE = 2
PALETTE_SIZE = 48
GRID = 16
SIMPLE_ICONS = "https://cdn.jsdelivr.net/npm/simple-icons@16/icons/{}.svg"

# Inventory, in display order (2 rows x 8). `holes` paints enclosed
# transparent pixels; `mode` recolors the silhouette to mimic multi-color logos.
ICONS = [
    {"key": "typescript", "name": "TYPESCRIPT", "flavor": "TYPE-SAFE ARMOR. +10 CONFIDENCE", "color": "#3178C6", "holes": "#FFFFFF"},
    {"key": "javascript", "name": "JAVASCRIPT", "flavor": "RUNS EVERYWHERE. HANDLE WITH CARE", "color": "#F7DF1E", "holes": "#1C1C1C"},
    {"key": "react", "name": "REACT", "flavor": "COMPONENT MAGIC. RE-RENDERS ON CUE", "color": "#61DAFB"},
    {"key": "expo", "name": "EXPO", "flavor": "ONE CODEBASE, PHONES EVERYWHERE", "color": "#E8ECFF"},
    {"key": "tailwindcss", "name": "TAILWIND CSS", "flavor": "UTILITY BELT FOR FAST STYLING", "color": "#06B6D4"},
    {"key": "vite", "name": "VITE", "flavor": "INSTANT DEV SERVER. SPEED +99", "color": "#BD34FE", "mode": "vite"},
    {"key": "html5", "name": "HTML5", "flavor": "THE FOUNDATION STONE", "color": "#E34F26", "holes": "#FFFFFF"},
    {"key": "css", "name": "CSS", "flavor": "PAINT, LAYOUT AND MOTION", "color": "#663399", "holes": "#FFFFFF"},
    {"key": "php", "name": "PHP", "flavor": "POWERS CAMPUS SYSTEMS", "manual": "php"},
    {"key": "python", "name": "PYTHON", "flavor": "SCRIPTS AND AGENT SKILLS", "color": "#3776AB", "mode": "python"},
    {"key": "postgresql", "name": "POSTGRESQL", "flavor": "RELIABLE RELATIONAL VAULT", "manual": "postgresql"},
    {"key": "mysql", "name": "MYSQL", "flavor": "CLASSIC DATA CHEST", "manual": "mysql"},
    {"key": "supabase", "name": "SUPABASE", "flavor": "AUTH + DATABASE IN ONE SPELL", "color": "#3FCF8E"},
    {"key": "convex", "name": "CONVEX", "flavor": "REACTIVE BACKEND, REALTIME SYNC", "color": "#EE342F", "mode": "convex"},
    {"key": "figma", "name": "FIGMA", "flavor": "DESIGN BEFORE YOU BUILD", "manual": "figma"},
    {"key": "claude", "name": "CLAUDE", "flavor": "AI PARTY MEMBER", "color": "#D97757"},
]

MANUAL = {
    "php": {
        "palette": {"P": "#777BB4", "W": "#FFFFFF", "D": "#4F5B93"},
        "grid": [
            "................",
            "................",
            "................",
            "....PPPPPPPP....",
            "..PPPPPPPPPPPP..",
            ".PPWWWPWPWPWWWP.",
            "PPPWPWPWPWPWPWPP",
            "PPPWWWPWWWPWWWPP",
            "PPPWPPPWPWPWPPPP",
            "PPPWPPPWPWPWPPPP",
            ".PPPPPPPPPPPPPP.",
            "..DPPPPPPPPPPD..",
            "....DDDDDDDD....",
            "................",
            "................",
            "................",
        ],
    },
    "mysql": {
        "palette": {"B": "#4479A1", "L": "#6FA3C9", "D": "#2E5878", "O": "#F29111"},
        "grid": [
            "................",
            "...DDDDDDDDDD...",
            ".DDLLLLLLLLLLDD.",
            ".DLLLLLLLLLLLLD.",
            ".BDDLLLLLLLLDDB.",
            ".BBBDDDDDDDDBBB.",
            ".BBBBBBBBBBBBBB.",
            ".OOBBBBBBBBBBOO.",
            ".BBOOOOOOOOOOBB.",
            ".BBBBBBBBBBBBBB.",
            ".BBBBBBBBBBBBBB.",
            ".OOBBBBBBBBBBOO.",
            ".BBOOOOOOOOOOBB.",
            ".DBBBBBBBBBBBBD.",
            "..DDBBBBBBBBDD..",
            "....DDDDDDDD....",
        ],
    },
    "figma": {
        "palette": {"R": "#F24E1E", "S": "#FF7262", "P": "#A259FF", "B": "#1ABCFE", "G": "#0ACF83"},
        "grid": [
            "....RRRRSSSS....",
            "...RRRRRSSSSS...",
            "...RRRRRSSSSS...",
            "...RRRRRSSSSS...",
            "....RRRRSSSS....",
            "....PPPP.BBB....",
            "...PPPPPBBBBB...",
            "...PPPPPBBBBB...",
            "...PPPPPBBBBB...",
            "....PPPP.BBB....",
            "....GGGG........",
            "...GGGGG........",
            "...GGGGG........",
            "...GGGG.........",
            "....GG..........",
            "................",
        ],
    },
    "postgresql": {
        "palette": {"L": "#4169E1", "D": "#2B4A9E", "W": "#FFFFFF"},
        "grid": [
            "................",
            "....LLLLLLLL....",
            "..LLLLLLLLLLLL..",
            ".LLLLLLLLLLLLLL.",
            "LLLDLLLLLLLLDLLL",
            "LLLDLWLLLLWLDLLL",
            "LLLDLLLLLLLLDLLL",
            "LLLDDLLLLLLDDLLL",
            ".LLL.LLLLLL.LLL.",
            "..L..LLLLLL..L..",
            ".....WLLLLW.....",
            "......LLLL......",
            "......LLLL......",
            ".......LLL......",
            "........LLL.....",
            ".........LL.....",
        ],
    },
}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "normieg-readme-builder"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def build_sheet(sprite: Path) -> None:
    src = Image.open(sprite)
    frames = []
    for i in range(src.n_frames):
        src.seek(i)
        frame = src.convert("RGBA")
        w, h = frame.width // FRAME_DOWNSCALE, frame.height // FRAME_DOWNSCALE
        frames.append(frame.resize((w, h), Image.Resampling.BOX))
    fw, fh = frames[0].size
    sheet = Image.new("RGBA", (fw * len(frames), fh))
    for i, frame in enumerate(frames):
        sheet.paste(frame, (i * fw, 0))
    alpha = sheet.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
    # One shared palette for every frame keeps colors stable across the loop.
    rgb = sheet.convert("RGB").quantize(
        colors=PALETTE_SIZE, method=Image.Quantize.MAXCOVERAGE, dither=Image.Dither.NONE
    )
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    out = out.resize((out.width * SHEET_UPSCALE, out.height * SHEET_UPSCALE), Image.Resampling.NEAREST)
    out = out.quantize(colors=PALETTE_SIZE + 1, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    out.save(ASSETS / "grey-sheet.png", optimize=True)
    meta = {"frames": len(frames), "width": fw * SHEET_UPSCALE, "height": fh * SHEET_UPSCALE, "ms": src.info.get("duration") or 97}
    (ASSETS / "grey-sheet.json").write_text(json.dumps(meta, indent=2) + "\n")


def build_head(head: Path) -> None:
    im = Image.open(head).convert("RGB")
    im = im.resize((im.width * 2, im.height * 2), Image.Resampling.NEAREST)
    im.quantize(colors=64, dither=Image.Dither.NONE).save(ASSETS / "grey-head.png", optimize=True)


def rasterize(spec: dict) -> list[list[bool]]:
    svg = fetch(SIMPLE_ICONS.format(spec["key"])).decode()
    if "viewbox" in spec:
        svg = svg.replace('viewBox="0 0 24 24"', f'viewBox="{spec["viewbox"]}"')
    png = bytes(resvg_py.svg_to_bytes(svg_string=svg, width=GRID * 12, height=GRID * 12))
    alpha = Image.open(io.BytesIO(png)).convert("RGBA").getchannel("A")
    small = alpha.resize((GRID, GRID), Image.Resampling.BOX)
    threshold = spec.get("threshold", 110)
    return [[small.getpixel((x, y)) >= threshold for x in range(GRID)] for y in range(GRID)]


def enclosed(mask: list[list[bool]]) -> set[tuple[int, int]]:
    """Transparent pixels not reachable from the border (logo counters)."""
    outside: set[tuple[int, int]] = set()
    stack = [(x, y) for x in range(GRID) for y in (0, GRID - 1)] + [(x, y) for y in range(GRID) for x in (0, GRID - 1)]
    while stack:
        x, y = stack.pop()
        if not (0 <= x < GRID and 0 <= y < GRID) or (x, y) in outside or mask[y][x]:
            continue
        outside.add((x, y))
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return {(x, y) for y in range(GRID) for x in range(GRID) if not mask[y][x] and (x, y) not in outside}


def colorize(spec: dict, mask: list[list[bool]]) -> dict:
    palette: dict[str, str] = {}
    grid = [["."] * GRID for _ in range(GRID)]

    def put(x: int, y: int, color: str) -> None:
        code = next((k for k, v in palette.items() if v == color), None)
        if code is None:
            code = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[len(palette)]
            palette[code] = color
        grid[y][x] = code

    c = (GRID - 1) / 2
    for y in range(GRID):
        for x in range(GRID):
            if not mask[y][x]:
                continue
            color = spec["color"]
            mode = spec.get("mode")
            if mode == "python":
                color = "#3776AB" if x + y < GRID - 1 else "#FFD43B"
            elif mode == "convex":
                angle = (math.degrees(math.atan2(y - c, x - c)) + 360) % 360
                color = "#F3B01C" if 210 <= angle < 330 else "#8D2676" if 90 <= angle < 210 else "#EE342F"
            elif mode == "figma":
                col, row = (0 if x < GRID // 2 else 1), min(y * 3 // GRID, 2)
                color = [["#F24E1E", "#FF7262"], ["#A259FF", "#1ABCFE"], ["#0ACF83", "#0ACF83"]][row][col]
            elif mode == "vite":
                color = "#FFC517" if 5 <= x <= 11 and y >= 4 else "#BD34FE"
            elif "accent" in spec and y <= 4 and x >= 9:
                color = spec["accent"]
            put(x, y, color)
    if "holes" in spec:
        for x, y in enclosed(mask):
            put(x, y, spec["holes"])
    return {"palette": palette, "grid": ["".join(row) for row in grid]}


def build_icons() -> None:
    out = []
    for spec in ICONS:
        art = MANUAL[spec["manual"]] if "manual" in spec else colorize(spec, rasterize(spec))
        out.append({"key": spec["key"], "name": spec["name"], "flavor": spec["flavor"], **art})
    (ASSETS / "icons.json").write_text(json.dumps(out, indent=1) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sprite", type=Path, help="animated sprite (webp/gif)")
    parser.add_argument("--head", type=Path, help="portrait image")
    parser.add_argument("--icons", action="store_true", help="rebuild assets/icons.json")
    args = parser.parse_args()
    ASSETS.mkdir(exist_ok=True)
    if args.sprite:
        build_sheet(args.sprite)
    if args.head:
        build_head(args.head)
    if args.icons:
        build_icons()


if __name__ == "__main__":
    main()
