from __future__ import annotations

import math
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "data-scope.gif"
BADGE_CACHE = ROOT / "assets" / "badges"

WIDTH = 420
HEIGHT = 220
FRAMES = 126
DURATION_MS = 110

BG = (13, 17, 23)
RING_DARK = (18, 24, 30)
RING_MID = (54, 62, 67)
RING_LIGHT = (205, 198, 178)
GREEN = (106, 168, 79)
SOFT_GREEN = (143, 188, 143)
AMBER = (255, 204, 51)
RED = (232, 83, 70)
CYAN = (120, 190, 210)
WHITE = (230, 237, 243)
MUTED = (125, 133, 144)

TOOLS = [
    {"slug": "python", "label": "Python", "color": "14354C", "logo": "python", "logo_color": "white"},
    {"slug": "duckdb", "label": "DuckDB", "color": "FFF000", "logo": "duckdb", "logo_color": "black"},
    {"slug": "motherduck", "label": "MotherDuck", "color": "FFCC33", "logo": "duckdb", "logo_color": "black"},
    {"slug": "dlt", "label": "dlt", "color": "11A683", "logo": "python", "logo_color": "white"},
    {"slug": "sqlmesh", "label": "SQLMesh", "color": "2E3440", "logo": "sqlite", "logo_color": "white"},
    {"slug": "dagster", "label": "Dagster", "color": "654FF0", "logo": "dagster", "logo_color": "white"},
    {"slug": "geopandas", "label": "GeoPandas", "color": "139C5A", "logo": "pandas", "logo_color": "white"},
    {"slug": "pytorch", "label": "PyTorch", "color": "EE4C2C", "logo": "pytorch", "logo_color": "white"},
    {"slug": "osm", "label": "OpenStreetMap", "color": "7EBC6F", "logo": "openstreetmap", "logo_color": "white"},
]


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Courier New Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Courier New.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


FONT_SMALL = font(11)
FONT_SMALL_BOLD = font(11, bold=True)
FONT_LABEL = font(16, bold=True)
FONT_TINY = font(9, bold=True)


def rounded_rect(draw: ImageDraw.ImageDraw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text_center(draw: ImageDraw.ImageDraw, xy, text: str, fill, font_obj):
    bbox = draw.textbbox((0, 0), text, font=font_obj)
    x = xy[0] - (bbox[2] - bbox[0]) / 2
    y = xy[1] - (bbox[3] - bbox[1]) / 2
    draw.text((x, y), text, fill=fill, font=font_obj)


def badge_url(tool: dict[str, str]) -> str:
    label = quote(tool["label"].replace("-", "--"), safe="")
    color = tool["color"]
    logo = quote(tool["logo"], safe="")
    logo_color = quote(tool["logo_color"], safe="")
    return (
        f"https://img.shields.io/badge/{label}-{color}.png"
        f"?style=flat-square&logo={logo}&logoColor={logo_color}"
    )


def fallback_badge(tool: dict[str, str], path: Path) -> None:
    color = tuple(int(tool["color"][i : i + 2], 16) for i in (0, 2, 4))
    image = Image.new("RGBA", (106, 26), (12, 16, 18, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, 105, 25), radius=4, fill=(20, 24, 28, 255), outline=color + (255,), width=1)
    draw.rectangle((0, 0, 27, 25), fill=color + (255,))
    text_center(draw, (13, 13), tool["label"][:1].upper(), (255, 255, 255, 255), FONT_TINY)
    text_center(draw, (66, 13), tool["label"], WHITE + (255,), FONT_SMALL)
    image.save(path)


def load_badge(tool: dict[str, str]) -> Image.Image:
    BADGE_CACHE.mkdir(parents=True, exist_ok=True)
    path = BADGE_CACHE / f"{tool['slug']}.png"
    if not path.exists():
        try:
            with urlopen(badge_url(tool), timeout=20) as response:
                path.write_bytes(response.read())
        except Exception:
            fallback_badge(tool, path)

    badge = Image.open(path).convert("RGBA")
    max_width = 74
    max_height = 20
    scale = min(max_width / badge.width, max_height / badge.height)
    size = (max(1, int(badge.width * scale)), max(1, int(badge.height * scale)))
    return badge.resize(size, Image.Resampling.LANCZOS)


def make_frame(index: int) -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), BG + (255,))
    draw = ImageDraw.Draw(image)

    # Weathered target-board background, dark enough to stay README-friendly.
    for y in range(0, HEIGHT, 18):
        shade = 24 + (y // 18 % 2) * 6
        draw.rectangle((0, y, WIDTH, y + 17), fill=(shade, shade + 5, shade + 7, 255))
        draw.line((0, y, WIDTH, y), fill=(70, 76, 78, 90), width=1)
    for x in range(-40, WIDTH, 95):
        draw.line((x, 0, x + 90, HEIGHT), fill=(255, 255, 255, 18), width=1)

    cx, cy = WIDTH // 2, 108
    outer_r = 86
    inner_r = 64

    # Circular aperture rings.
    draw.ellipse((cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r), fill=RING_DARK + (255,), outline=(5, 7, 9, 255), width=4)
    draw.ellipse((cx - 76, cy - 76, cx + 76, cy + 76), fill=RING_LIGHT + (255,))
    draw.ellipse((cx - 69, cy - 69, cx + 69, cy + 69), fill=RING_MID + (255,))
    draw.ellipse((cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r), fill=(20, 25, 28, 255))

    # Ticks around the sight ring.
    for tick in range(0, 360, 15):
        a = math.radians(tick)
        r1 = 70
        r2 = 77 if tick % 45 == 0 else 74
        p1 = (cx + math.cos(a) * r1, cy + math.sin(a) * r1)
        p2 = (cx + math.cos(a) * r2, cy + math.sin(a) * r2)
        draw.line((p1, p2), fill=(105, 110, 112, 210), width=2 if tick % 45 == 0 else 1)

    # Clip animated targets to the open aperture.
    target_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    target_draw = ImageDraw.Draw(target_layer)
    aperture_mask = Image.new("L", (WIDTH, HEIGHT), 0)
    mask_draw = ImageDraw.Draw(aperture_mask)
    mask_draw.ellipse((cx - inner_r + 3, cy - inner_r + 3, cx + inner_r - 3, cy + inner_r - 3), fill=255)

    spacing = 92
    cycle_width = len(TOOLS) * spacing
    phase = (index / FRAMES) * cycle_width
    entry_x = cx + inner_r + 38
    y_mid = cy - 4
    for item_index, tool in enumerate(TOOLS):
        color = tuple(int(tool["color"][i : i + 2], 16) for i in (0, 2, 4))
        badge = load_badge(tool)
        x = entry_x - ((phase + item_index * spacing) % cycle_width)
        if x < cx - inner_r - 50:
            x += cycle_width
        card = (x - 40, y_mid - 13, x + 40, y_mid + 13)
        rounded_rect(target_draw, card, 9, (12, 16, 18, 225), color + (255,), 2)
        target_layer.alpha_composite(badge, (int(x - badge.width / 2), int(y_mid - badge.height / 2)))
        target_draw.ellipse((x - 4, y_mid + 12, x + 4, y_mid + 20), fill=color + (240,))

    image.alpha_composite(Image.composite(target_layer, Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0)), aperture_mask))

    # Archery sight pins: fibers attach to the right side of the sight ring.
    for dy, color in [(-16, AMBER), (0, RED), (16, AMBER)]:
        pin_origin_x = cx + math.sqrt((inner_r - 5) ** 2 - dy**2)
        draw.line((pin_origin_x, cy + dy, cx + 4, cy + dy), fill=(5, 8, 10, 255), width=4)
        draw.line((pin_origin_x, cy + dy, cx + 7, cy + dy), fill=color + (170,), width=1)
        glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.ellipse((cx + 1, cy + dy - 3, cx + 7, cy + dy + 3), fill=color + (220,))
        glow = glow.filter(ImageFilter.GaussianBlur(1.3))
        image.alpha_composite(glow)
        draw.ellipse((cx + 1, cy + dy - 2, cx + 5, cy + dy + 2), fill=color + (255,))

    # Bubble level at the bottom of the sight.
    level_box = (cx - 38, cy + 56, cx + 38, cy + 78)
    rounded_rect(draw, level_box, 8, (13, 28, 24, 255), (45, 58, 49, 255), 2)
    draw.rounded_rectangle((cx - 30, cy + 62, cx + 30, cy + 70), radius=4, fill=(123, 146, 39, 210), outline=(170, 190, 80, 180), width=1)
    draw.ellipse((cx - 7, cy + 61, cx + 7, cy + 71), fill=(190, 220, 80, 185))
    draw.line((cx, cy + 58, cx, cy + 74), fill=(230, 237, 243, 120), width=1)

    # Small bolt highlights and fiber housing.
    # Aperture shine and outer shadow.
    shine = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    shine_draw = ImageDraw.Draw(shine)
    shine_draw.arc((cx - 72, cy - 72, cx + 72, cy + 72), 205, 330, fill=(255, 255, 255, 65), width=7)
    image.alpha_composite(shine)

    draw.text((WIDTH - 122, HEIGHT - 24), "Lough on Data", fill=GREEN + (245,), font=FONT_SMALL_BOLD)

    return image.convert("P", palette=Image.ADAPTIVE)


def main() -> None:
    frames = [make_frame(i) for i in range(FRAMES)]
    frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=frames[1:],
        duration=DURATION_MS,
        loop=0,
        optimize=True,
    )
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
