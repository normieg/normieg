"""Render the pixel-art profile panels into an output directory.

    GITHUB_TOKEN=... python scripts/render.py --out dist

Standard library only. Live numbers (stats, stars, contribution grid) come
from the GitHub GraphQL API; everything else is drawn from assets/.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import math
import os
import random
import textwrap
import urllib.request
from pathlib import Path

from pixel import (
    CYAN, DIM, GREEN, GREEN_DK, GREEN_HI, INK, LIGHT, LINE, ORANGE, OUTLINE, PANEL, PINK, PURPLE, SLOT, U, YELLOW,
    gradient_text, grid_art, icon7, notched, rect, sunken, svg, tab, text, text_width, window,
)

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
LOGIN = "normieg"
W = 840  # panel width; README scales it to the column

QUESTS = [
    {"repo": "BYO-SMS-GATEWAY", "title": "BYO-SMS GATEWAY", "desc": "Send app SMS and one-time passcodes through an Android phone and SIM you control."},
    {"repo": "Swiper", "title": "SWIPER", "desc": "Evidence-driven agent skill for reverse engineering and recreating website frontends."},
    {"repo": "Readme-gen", "title": "README-GEN", "desc": "AI README generator skill for Codex and Claude Code. Create, audit, improve.", "lang": "Agent Skill"},
    {"repo": "Faculty-Evaluation-System", "title": "FACULTY EVAL SYSTEM", "desc": "Faculty evaluation platform: academic terms, subject assignments and results."},
]

ABOUT = [
    ("HI, I'M GREY! I MAKE THE WEB FEEL CONSIDERED.", INK),
    ("SOFTWARE ENGINEER + WEB AND GRAPHIC DESIGNER.", INK),
    ("NOW BUILDING: AGENT SKILLS, SMS GATEWAYS, BALIFIND.", INK),
    ("OFF-SCREEN: SCOOTER RIDES, SUNSETS, COFFEE HOPS.", INK),
    ("SCROLL DOWN TO CHECK MY GEAR AND QUESTS.", DIM),
]

CONTACTS = [
    ("portfolio", "PORTFOLIO", "globe", GREEN),
    ("email", "EMAIL", "mail", YELLOW),
    ("linkedin", "LINKEDIN", "linkedin", CYAN),
    ("tiktok", "TIKTOK", "note", PINK),
    ("instagram", "INSTAGRAM", "camera", ORANGE),
]


# Data -----------------------------------------------------------------

def graphql(token: str, query: str, variables: dict) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": f"{LOGIN}-readme"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload["data"]


def fetch_stats(token: str) -> dict:
    user = graphql(token, """
    query($login: String!) {
      user(login: $login) {
        createdAt
        followers { totalCount }
        pullRequests(states: MERGED) { totalCount }
        repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
          totalCount
          nodes {
            name stargazerCount
            primaryLanguage { name color }
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } }
          }
        }
        contributionsCollection {
          totalCommitContributions
          contributionCalendar { totalContributions weeks { contributionDays { contributionCount contributionLevel } } }
        }
      }
    }""", {"login": LOGIN})["user"]

    # Lifetime contributions = XP. The API caps each window at one year.
    first_year = int(user["createdAt"][:4])
    now = dt.datetime.now(dt.timezone.utc)
    windows = " ".join(
        f'y{y}: contributionsCollection(from: "{y}-01-01T00:00:00Z", to: "{min(now, dt.datetime(y, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")}") '
        "{ contributionCalendar { totalContributions } }"
        for y in range(first_year, now.year + 1)
    )
    years = graphql(token, f"query($login: String!) {{ user(login: $login) {{ {windows} }} }}", {"login": LOGIN})["user"]
    xp = sum(v["contributionCalendar"]["totalContributions"] for v in years.values())

    langs: dict[str, dict] = {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            entry = langs.setdefault(edge["node"]["name"], {"size": 0, "color": edge["node"]["color"] or DIM})
            entry["size"] += edge["size"]
    total = sum(v["size"] for v in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1]["size"])[:5]

    cal = user["contributionsCollection"]["contributionCalendar"]
    return {
        "xp": xp,
        "contributions": cal["totalContributions"],
        "commits": user["contributionsCollection"]["totalCommitContributions"],
        "stars": sum(r["stargazerCount"] for r in user["repositories"]["nodes"]),
        "prs": user["pullRequests"]["totalCount"],
        "repos": user["repositories"]["totalCount"],
        "followers": user["followers"]["totalCount"],
        "languages": [(name, v["color"], v["size"] / total) for name, v in top],
        "weeks": [[d["contributionLevel"] for d in w["contributionDays"]] for w in cal["weeks"]],
        "repo_meta": {r["name"]: r for r in user["repositories"]["nodes"]},
        "date": now.strftime("%Y-%m-%d"),
    }


def data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def fmt(n: int) -> str:
    return f"{n:,}"


# Panels -----------------------------------------------------------------

SKY = ["#1A1240", "#24165A", "#351C6E", "#4E2380", "#6E2B88", "#93348A", "#BC4585", "#E05E7B", "#F7826C", "#FFA764"]


def hero() -> str:
    H = 320
    x0, y0, iw, ih = 2 * U, 2 * U, W - 4 * U - 2 * U, H - 4 * U - 2 * U  # scene inside the frame
    rng = random.Random(7)
    sheet = json.loads((ASSETS / "grey-sheet.json").read_text())
    fw, fh, frames = sheet["width"], sheet["height"], sheet["frames"]

    body = window(0, 0, W - U, H - U)
    scene = ""
    band_h = 24
    horizon = y0 + band_h * len(SKY)
    for i, color in enumerate(SKY):
        scene += rect(x0, y0 + i * band_h, iw, band_h, color)
    for i in range(1, len(SKY)):  # 2-row checker dither between bands
        by = y0 + i * band_h - U
        scene += rect(x0, by, iw, U, f"url(#d{i})")
    defs = "".join(
        f'<pattern id="d{i}" width="{2 * U}" height="{U}" patternUnits="userSpaceOnUse">'
        f'{rect(0, 0, U, U, SKY[i])}{rect(U, 0, U, U, SKY[i - 1])}</pattern>'
        for i in range(1, len(SKY))
    )

    # Stars in the upper sky.
    for i in range(26):
        sx, sy = x0 + rng.randrange(4, iw // U - 4) * U, y0 + rng.randrange(1, 18) * U
        if 2 * U < sx < 400 and 48 < sy < 120:  # keep the title clear
            continue
        delay = rng.uniform(0, 4)
        if i % 5 == 0:
            scene += f'<g class="tw" style="animation-delay:{delay:.2f}s">{rect(sx, sy - U, U, 3 * U, "#FFF6D8")}{rect(sx - U, sy, 3 * U, U, "#FFF6D8")}</g>'
        else:
            scene += rect(sx, sy, U, U, "#FFF6D8", f' class="tw" style="animation-delay:{delay:.2f}s"')

    # Striped setting sun behind the character.
    cx, cy, r = 548, horizon - 8, 64
    for row in range(-r // U, 1):
        yy = cy + row * U
        half = int(math.sqrt(max(r * r - (row * U) ** 2, 0)) // U) * U
        depth = -row * U
        if depth < 40 and (depth // U) % 3 == 0:  # retro cut lines near the horizon
            continue
        color = "#FFF0A8" if depth > 52 else "#FFD36B" if depth > 26 else "#FF9F5A"
        scene += rect(cx - half, yy, 2 * half, U, color)

    # Drifting clouds.
    cloud = ["..####......", ".######.###.", "############", ".##########."]
    for i, (cy_, dur, delay, color) in enumerate([(56, 90, -10, "#B9548E"), (100, 120, -70, "#D8668A"), (140, 70, -40, "#F08C7E")]):
        d = "".join(
            f"M{x * U} {y * U}h{U}v{U}h-{U}z" for y, row in enumerate(cloud) for x, c in enumerate(row) if c == "#"
        )
        scene += f'<g class="cl" style="animation-duration:{dur}s;animation-delay:{delay}s"><path transform="translate(0 {cy_})" fill="{color}" d="{d}"/></g>'

    # City skyline: far layer, near layer with windows.
    for layer, (base, color, hmin, hmax) in enumerate([(horizon, "#3A1D5E", 5, 12), (horizon + 2 * U, "#1C1036", 3, 10)]):
        bx = x0
        while bx < x0 + iw:
            bw = rng.randrange(6, 14) * U
            bh = rng.randrange(hmin, hmax) * U
            scene += rect(bx, base - bh, bw, H, color)
            if layer == 1:
                for wy in range(base - bh + 2 * U, base + 4 * U, 3 * U):
                    for wx in range(bx + U, bx + bw - U, 2 * U):
                        if rng.random() < 0.28:
                            lit = rng.choice(["#FFD27A", "#FFB86B", "#FFE9A8"])
                            flick = f' class="fl" style="animation-delay:{rng.uniform(0, 6):.2f}s"' if rng.random() < 0.12 else ""
                            scene += rect(wx, wy, U, U, lit, flick)
            bx += bw + rng.choice([0, U, 2 * U])

    # Rooftop ledge the character sits on.
    ledge = H - 2 * U - 7 * U
    scene += rect(x0, ledge, iw, H, "#120A26") + rect(x0, ledge, iw, U, "#3A2466")
    for lx in range(x0, x0 + iw, 12 * U):
        scene += rect(lx, ledge + U, U, 6 * U, "#1E1238")

    # Animated character (sprite sheet scrolled in steps).
    px, py = 622, ledge - fh + 30
    scene += (
        f'<svg x="{px}" y="{py}" width="{fw}" height="{fh}" viewBox="0 0 {fw} {fh}">'
        f'<image class="sp" width="{fw * frames}" height="{fh}" href="{data_uri(ASSETS / "grey-sheet.png")}"/></svg>'
    )

    # Title block.
    scene += gradient_text("GREY.DEV", 40, 44, 8, [(range(0, 3), "#FFF0A8"), (range(3, 5), YELLOW), (range(5, 7), ORANGE)], shadow="#1A0F33")
    scene += text("SOFTWARE ENGINEER", 44, 120, 3, INK, shadow="#1A0F33")
    scene += text("WEB · MOBILE · GRAPHIC DESIGN", 44, 150, 2, "#FFE3F0", shadow="#1A0F33")
    scene += f'<g class="bl">{text("▶", 44, 176, 2, GREEN_HI, shadow="#1A0F33")}</g>'
    scene += text("GREY.IS-A.DEV", 60, 176, 2, GREEN_HI, shadow="#1A0F33")

    body += f'<clipPath id="scene"><rect x="{x0}" y="{y0}" width="{iw}" height="{ih}"/></clipPath><g clip-path="url(#scene)">{scene}</g>'
    style = (
        f".sp{{image-rendering:pixelated;animation:sp {sheet['ms'] * frames / 1000:.2f}s steps({frames}) infinite}}"
        f"@keyframes sp{{to{{transform:translateX(-{fw * frames}px)}}}}"
        ".tw{animation:tw 3s steps(2) infinite}@keyframes tw{50%{opacity:.25}}"
        ".fl{animation:fl 5s steps(1) infinite}@keyframes fl{40%{opacity:0}60%{opacity:1}}"
        ".bl{animation:bl 1s steps(1) infinite}@keyframes bl{50%{opacity:0}}"
        ".cl{animation:cl linear infinite}@keyframes cl{from{transform:translateX(-60px)}to{transform:translateX(860px)}}"
    )
    return svg(W, H, "GREY.DEV: software engineer, web, mobile and graphic design. Grey's pixel character types on a laptop on a rooftop at sunset.", f"<defs>{defs}</defs>{body}", style)


def about() -> str:
    H = 252
    top = 16
    body = window(0, top, W - U, H - top - U)
    body += tab("GREY", 24, 0)
    # Portrait.
    body += notched(28, top + 28, 144, 144, OUTLINE) + rect(32, top + 32, 136, 136, LIGHT)
    body += f'<image x="36" y="{top + 36}" width="128" height="128" href="{data_uri(ASSETS / "grey-head.png")}" style="image-rendering:pixelated"/>'
    # Typewriter lines: a panel-colored cover slides off each line in per-char steps.
    tx, ty, lh, scale = 196, top + 36, 30, 2
    adv = 6 * scale
    t = 0.6
    style = ""
    covers = ""
    for i, (line, color) in enumerate(ABOUT):
        y = ty + i * lh
        n = len(line)
        dist = n * adv + 4
        dur = n * 0.035
        body += text(line, tx, y, scale, color)
        covers += rect(tx - 2, y - 2, dist, 7 * scale + 4, PANEL, f' class="tc{i}" style="transform:translateX({dist}px)"')
        style += (
            f".tc{i}{{animation:tc{i} {dur:.2f}s steps({n}) {t:.2f}s both}}"
            f"@keyframes tc{i}{{from{{transform:translateX(0)}}to{{transform:translateX({dist}px)}}}}"
        )
        t += dur + 0.25
    # Covers slide right once a line is typed; the clip keeps them off the frame.
    inner_right = W - U - 2 * U
    body += f'<clipPath id="txt"><rect x="{tx - 4}" y="{top}" width="{inner_right - tx + 4}" height="{H - top}"/></clipPath><g clip-path="url(#txt)">{covers}</g>'
    body += f'<g class="nx" style="animation-delay:{t:.2f}s">{text("▼", W - U - 52, H - U - 36, 2, YELLOW)}</g>'
    style += ".nx{animation:nx 1s steps(1) infinite both}@keyframes nx{0%{opacity:0}50%{opacity:1}}"
    alt = "Hi, I'm Grey! I make the web feel considered. Software engineer, web and graphic designer. Now building agent skills, SMS gateways and BaliFind. Off-screen: scooter rides, sunsets, coffee hops."
    return svg(W, H, alt, body, style)


def inventory() -> str:
    icons = json.loads((ASSETS / "icons.json").read_text())
    cols, slot, gap = 8, 80, 12
    gx = (W - U - (cols * slot + (cols - 1) * gap)) // 2
    gy = 16 + 32
    H = gy + 2 * slot + gap + 24 + 56 + 32
    body = window(0, 16, W - U, H - 16 - U) + tab("INVENTORY", 24, 0)
    positions = []
    for i, ic in enumerate(icons):
        sx, sy = gx + (i % cols) * (slot + gap), gy + (i // cols) * (slot + gap)
        positions.append((sx, sy))
        body += sunken(sx, sy, slot, slot)
        body += grid_art(ic["grid"], ic["palette"], sx + 16, sy + 16, 3)

    # Item description box.
    by = gy + 2 * slot + gap + 20
    bw = cols * slot + (cols - 1) * gap
    body += sunken(gx, by, bw, 56)
    n = len(icons)
    slice_s = 1.6
    period = n * slice_s
    labels = ""
    for i, ic in enumerate(icons):
        delay = 0 if i == 0 else -(period - i * slice_s)
        label = text("▶ " + ic["name"], gx + 20, by + 18, 3, YELLOW) + text(ic["flavor"], gx + bw - 20, by + 22, 2, DIM, anchor="end")
        labels += f'<g class="it{" i0" if i == 0 else ""}" style="animation-delay:{delay:.2f}s">{label}</g>'
    body += labels

    # Selection cursor: corner brackets that hop slot to slot.
    c = YELLOW
    k = 4 * U
    corners = (
        rect(-U, -U, k, U, c) + rect(-U, -U, U, k, c)
        + rect(slot - k + U, -U, k, U, c) + rect(slot, -U, U, k, c)
        + rect(-U, slot, k, U, c) + rect(-U, slot - k + U, U, k, c)
        + rect(slot - k + U, slot, k, U, c) + rect(slot, slot - k + U, U, k, c)
    )
    body += f'<g class="cur" style="transform:translate({positions[0][0]}px,{positions[0][1]}px)">{corners}</g>'
    frames = "".join(f"{i * 100 / n:.4f}%{{transform:translate({x}px,{y}px)}}" for i, (x, y) in enumerate(positions))
    pct = 100 / n
    style = (
        f".it{{opacity:0;animation:it {period:.2f}s step-end infinite}}.i0{{opacity:1}}"
        f"@keyframes it{{0%{{opacity:1}}{pct:.4f}%{{opacity:0}}100%{{opacity:0}}}}"
        f".cur{{animation:cur {period:.2f}s step-end infinite}}@keyframes cur{{{frames}100%{{transform:translate({positions[0][0]}px,{positions[0][1]}px)}}}}"
    )
    alt = "Inventory: " + ", ".join(ic["name"].title() for ic in icons)
    return svg(W, H, alt, body, style)


def quest_card(i: int, quest: dict, meta: dict) -> str:
    w, h = 412, 204
    body = window(0, 0, w - U, h - U)
    body += text(f"QUEST {i + 1:02d}", 24, 24, 2, GREEN_HI)
    body += text(quest["title"], 24, 48, 3, YELLOW, shadow=OUTLINE)
    for li, line in enumerate(textwrap.wrap(quest["desc"].upper(), 30)[:3]):
        body += text(line, 24, 84 + li * 20, 2, INK)
    lang = meta.get("primaryLanguage") or {}
    lname = (quest.get("lang") or lang.get("name") or "CODE").upper()
    lcolor = lang.get("color") or PURPLE
    fy = h - 3 * U - 40  # divider; footer row sits 12px below, 14px above the frame
    body += rect(24, fy, w - U - 48, 2, LINE)
    body += icon7("gem", 24, fy + 12, 2, lcolor) + text(lname, 44, fy + 12, 2, DIM)
    stars = fmt(meta.get("stargazerCount", 0))
    sx = w - U - 24 - text_width(stars, 2)
    body += icon7("star", sx - 22, fy + 12, 2, YELLOW) + text(stars, sx, fy + 12, 2, INK)
    return svg(w, h, f"{quest['title'].title()}: {quest['desc']}", body)


def bar(x: int, y: int, segments: int, filled: int, color: str) -> str:
    out = ""
    for s in range(segments):
        out += rect(x + s * 10, y, 8, 14, color if s < filled else SLOT)
    return out


def stats(data: dict) -> str:
    H = 484
    body = window(0, 16, W - U, H - 16 - U) + tab("PLAYER STATS", 24, 0)
    xp = data["xp"]
    level = int(math.sqrt(xp / 10)) + 1
    lo, hi = 10 * (level - 1) ** 2, 10 * level ** 2
    lx = 36
    body += text("GREY", lx, 52, 3, INK, shadow=OUTLINE)
    body += text(f"LV {level}", 396, 52, 3, YELLOW, anchor="end", shadow=OUTLINE)
    body += text("XP", lx, 86, 2, DIM)
    body += bar(lx + 32, 86, 30, round(30 * (xp - lo) / max(hi - lo, 1)), GREEN)
    body += text(f"{fmt(xp)} / {fmt(hi)} XP", 396, 108, 2, DIM, anchor="end")
    rows = [
        ("heart", PINK, "CONTRIBUTIONS (1Y)", data["contributions"]),
        ("gem", CYAN, "COMMITS (1Y)", data["commits"]),
        ("flag", GREEN, "PRS MERGED", data["prs"]),
        ("star", YELLOW, "STARS EARNED", data["stars"]),
        ("chest", ORANGE, "PUBLIC REPOS", data["repos"]),
        ("person", PURPLE, "FOLLOWERS", data["followers"]),
    ]
    for i, (icon, color, label, value) in enumerate(rows):
        ry = 136 + i * 26
        body += icon7(icon, lx, ry, 2, color) + text(label, lx + 24, ry, 2, INK) + text(fmt(value), 396, ry, 2, YELLOW, anchor="end")

    rx = 444
    body += rect(rx - 24, 44, 2, 268, LINE)
    body += text("TOP LANGUAGES", rx, 52, 2, DIM)
    for i, (name, color, share) in enumerate(data["languages"]):
        ly = 84 + i * 46
        body += text(name, rx, ly, 2, INK) + text(f"{share * 100:.1f}%", 800, ly, 2, DIM, anchor="end")
        body += bar(rx, ly + 20, 36, max(1, round(36 * share)), color)

    # Contribution grid (last year).
    gy = 332
    body += rect(36, gy - 12, W - U - 72, 2, LINE)
    body += text("QUEST LOG", 36, gy, 2, DIM) + text(f"{fmt(data['contributions'])} CONTRIBUTIONS IN THE LAST YEAR", 800, gy, 2, DIM, anchor="end")
    levels = {"NONE": SLOT, "FIRST_QUARTILE": GREEN_DK, "SECOND_QUARTILE": "#2BC22B", "THIRD_QUARTILE": GREEN, "FOURTH_QUARTILE": GREEN_HI}
    weeks = data["weeks"][-53:]
    cell = 14
    ox = 36 + (W - U - 72 - len(weeks) * cell + 4) // 2
    for wi, week in enumerate(weeks):
        col = "".join(rect(ox + wi * cell, gy + 24 + d * cell, 10, 10, levels[lvl]) for d, lvl in enumerate(week))
        body += f'<g class="wk" style="animation-delay:{wi * 0.02:.2f}s">{col}</g>'
    style = ".wk{animation:wk .4s steps(2) both}@keyframes wk{from{opacity:0}}"
    alt = (
        f"Player stats: level {level}, {fmt(xp)} XP, {fmt(data['contributions'])} contributions and {fmt(data['commits'])} commits in the last year, "
        f"{data['prs']} merged PRs, {data['stars']} stars, {data['repos']} public repos, {data['followers']} followers. Top languages: "
        + ", ".join(f"{n} {s * 100:.1f}%" for n, _, s in data["languages"])
    )
    return svg(W, H, alt, body, style)


def button(label: str, icon: str, color: str) -> str:
    w, h = 160, 48
    body = window(0, 0, w - U, h - U)
    tw = 14 + 8 + text_width(label, 2)
    x = (w - U - tw) // 2
    body += icon7(icon, x, 15, 2, color) + text(label, x + 22, 15, 2, INK)
    return svg(w, h, label.title(), body)


def footer(date: str) -> str:
    H = 64
    body = rect(0, 16, W, H - 16, "#2A1C12")
    rng = random.Random(3)
    for x in range(0, W, U):
        tuft = rng.choice([0, 0, 1, 2])
        body += rect(x, 16 - tuft * U, U, (tuft + 2) * U, GREEN if (x // U) % 3 else GREEN_DK)
        if rng.random() < 0.08:
            body += rect(x, 16 + rng.randrange(3, 10) * U, U, U, "#4A3322")
    body += text(f"THANKS FOR VISITING!  ·  GAME SAVED {date}", W // 2, 40, 2, "#F2D8B8", anchor="middle", shadow="#120A06")
    return svg(W, H, f"Thanks for visiting! Last updated {date}.", body)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required (GraphQL API)")
    data = fetch_stats(token)
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "hero.svg": hero(),
        "about.svg": about(),
        "inventory.svg": inventory(),
        "stats.svg": stats(data),
        "footer.svg": footer(data["date"]),
    }
    for i, quest in enumerate(QUESTS):
        files[f"quest-{quest['repo'].lower()}.svg"] = quest_card(i, quest, data["repo_meta"].get(quest["repo"], {}))
    for key, label, icon, color in CONTACTS:
        files[f"btn-{key}.svg"] = button(label, icon, color)
    for name, content in files.items():
        (out / name).write_text(content, encoding="utf-8")
    print(f"rendered {len(files)} files to {out}")


if __name__ == "__main__":
    main()
