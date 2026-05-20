from __future__ import annotations

import math
import subprocess
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = ROOT.parent
OUTPUT = ROOT / "assets" / "data-scope.gif"
BADGE_CACHE = ROOT / "assets" / "badges"
PATTERN_CACHE = ROOT / "assets" / "bg-pattern.png"
SITE_PATTERN = SITE_ROOT / "static" / "img" / "bg-pattern.svg"

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
CONTOUR_GOLD = (251, 191, 36)

TOOLS = [
    {
        "slug": "python",
        "label": "Python",
        "color": "3776AB",
        "logo": "python",
        "logo_color": "white",
        "image": "assets/python.png",
    },
    {
        "slug": "duckdb",
        "label": "DuckDB",
        "color": "FFF000",
        "logo": "duckdb",
        "logo_color": "black",
        "image": "assets/duckdb.png",
    },
    {
        "slug": "snowflake",
        "label": "Snowflake",
        "color": "29B5E8",
        "logo": "snowflake",
        "logo_color": "white",
        "image": "assets/snowflake.png",
    },
    {
        "slug": "dbt",
        "label": "dbt",
        "color": "FF694B",
        "logo": "dbt",
        "logo_color": "white",
        "image": "assets/dbt.png",
    },
    {
        "slug": "dagster",
        "label": "Dagster",
        "color": "654FF0",
        "logo": "dagster",
        "logo_color": "white",
        "image": "assets/dagster.png",
    },
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


def load_target_image(tool: dict[str, str]) -> Image.Image | None:
    image_path = tool.get("image")
    if not image_path:
        return None

    path = ROOT / image_path
    if not path.exists():
        return None

    logo = Image.open(path).convert("RGBA")
    logo.thumbnail((46, 46), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (56, 56), (0, 0, 0, 0))
    canvas.alpha_composite(logo, ((canvas.width - logo.width) // 2, (canvas.height - logo.height) // 2))
    return canvas


def site_pattern_tile() -> Image.Image | None:
    if not SITE_PATTERN.exists():
        return None

    if not PATTERN_CACHE.exists():
        try:
            subprocess.run(
                [
                    "rsvg-convert",
                    "--width",
                    "600",
                    "--height",
                    "600",
                    "--output",
                    str(PATTERN_CACHE),
                    str(SITE_PATTERN),
                ],
                check=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None

    return Image.open(PATTERN_CACHE).convert("RGBA")


def densest_pattern_crop(tile: Image.Image) -> Image.Image:
    alpha = tile.getchannel("A")
    best_score = -1
    best_box = (0, 0, WIDTH, HEIGHT)

    max_x = max(0, tile.width - WIDTH)
    max_y = max(0, tile.height - HEIGHT)
    for y in range(0, max_y + 1, 24):
        for x in range(0, max_x + 1, 24):
            crop_alpha = alpha.crop((x, y, x + WIDTH, y + HEIGHT))
            score = sum(crop_alpha.get_flattened_data())
            if score > best_score:
                best_score = score
                best_box = (x, y, x + WIDTH, y + HEIGHT)

    return tile.crop(best_box)


def draw_soft_contours(image: Image.Image) -> None:
    scale = 4
    large = Image.new("RGBA", (WIDTH * scale, HEIGHT * scale), (11, 18, 14, 255))
    draw = ImageDraw.Draw(large)

    def s(value: float) -> int:
        return int(value * scale)

    contour_color = (78, 91, 42, 150)
    highlight_color = (111, 96, 44, 110)

    islands = [
        (-18, 34, 150, 58, 0.35),
        (356, 44, 166, 64, 1.2),
        (52, 176, 176, 58, 2.0),
        (348, 176, 140, 46, 2.8),
    ]
    for cx0, cy0, rx, ry, phase in islands:
        for step in range(6):
            rxf = rx - step * 16
            ryf = ry - step * 7
            if rxf <= 0 or ryf <= 0:
                continue
            points = []
            for degree in range(0, 361, 5):
                angle = math.radians(degree)
                wobble = 1 + math.sin(angle * 2.4 + phase) * 0.045 + math.cos(angle * 4.8 - phase) * 0.025
                points.append((s(cx0 + math.cos(angle) * rxf * wobble), s(cy0 + math.sin(angle) * ryf * wobble)))
            draw.line(points, fill=contour_color if step % 2 else highlight_color, width=s(1.2))

    for band, base_y in enumerate(range(-10, HEIGHT + 35, 34)):
        points = []
        phase = band * 0.7
        for x in range(-30, WIDTH + 31, 8):
            y = base_y + math.sin(x * 0.025 + phase) * 5 + math.cos(x * 0.053 - phase) * 2
            points.append((s(x), s(y)))
        draw.line(points, fill=(56, 70, 42, 90), width=s(0.9))

    large = large.filter(ImageFilter.GaussianBlur(s(0.15)))
    image.alpha_composite(large.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS))


def draw_site_background(image: Image.Image) -> None:
    image.paste((11, 18, 14, 255), (0, 0, WIDTH, HEIGHT))

    tile = site_pattern_tile()
    if tile is None:
        draw_soft_contours(image)
        return

    # Use the actual website contour asset as a subdued texture, not foreground art.
    crop = densest_pattern_crop(tile)
    crop = crop.filter(ImageFilter.GaussianBlur(0.2))

    # The SVG has 8% opacity baked in. Boost it for the tiny GIF, but cap it so
    # the sight and badges remain the subject.
    alpha = crop.getchannel("A").point(lambda value: min(92, int(value * 4.25)))
    crop.putalpha(alpha)
    image.alpha_composite(crop)


def make_frame(index: int) -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), BG + (255,))
    draw = ImageDraw.Draw(image)

    draw_site_background(image)

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
        logo = load_target_image(tool)
        badge = None if logo is not None else load_badge(tool)
        x = entry_x - ((phase + item_index * spacing) % cycle_width)
        if x < cx - inner_r - 50:
            x += cycle_width
        if logo is not None:
            target_layer.alpha_composite(logo, (int(x - logo.width / 2), int(y_mid - logo.height / 2)))
        else:
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
