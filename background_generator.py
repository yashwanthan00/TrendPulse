"""
Generates beautiful original backgrounds using Pillow — zero copyright risk.
All output is 100% programmatically created, owned by the channel.

Styles rotate daily so videos don't look identical:
  gradient | mesh | radial | geometric | particles
"""

import math
import random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFilter

WIDTH, HEIGHT = 1280, 720
PALETTES = [
    [(10, 10, 40), (30, 0, 80), (0, 60, 120)],    # deep blue-purple
    [(5, 30, 20), (0, 80, 60), (10, 120, 80)],     # dark teal-green
    [(40, 10, 10), (100, 20, 40), (60, 0, 80)],    # deep crimson-purple
    [(20, 20, 50), (50, 30, 100), (10, 80, 150)],  # midnight blue
    [(10, 30, 10), (30, 70, 30), (60, 100, 20)],   # dark forest green
]


def generate_background(save_path: str, seed: int = None) -> str:
    """Generate a unique background and save to save_path. Returns save_path."""
    if seed is None:
        seed = datetime.now().timetuple().tm_yday

    random.seed(seed)
    palette = PALETTES[seed % len(PALETTES)]

    style_idx = seed % 5
    styles = [_gradient, _mesh, _radial, _geometric, _particles]
    img = styles[style_idx](palette)

    # slight blur for depth
    img = img.filter(ImageFilter.GaussianBlur(radius=1))
    img.save(save_path, quality=95)
    return save_path


# ── Styles ────────────────────────────────────────────────────────────────────

def _gradient(palette) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    c1, c2 = palette[0], palette[1]
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
    return img


def _mesh(palette) -> Image.Image:
    img = _gradient(palette)
    draw = ImageDraw.Draw(img)
    c3 = palette[2]
    for i in range(0, WIDTH, 80):
        draw.line([(i, 0), (i + 200, HEIGHT)], fill=(*c3, 40), width=1)
    for j in range(0, HEIGHT, 60):
        draw.line([(0, j), (WIDTH, j + 100)], fill=(*c3, 30), width=1)
    return img


def _radial(palette) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), palette[0])
    draw = ImageDraw.Draw(img)
    cx, cy = WIDTH // 2, HEIGHT // 2
    max_r = int(math.hypot(cx, cy))
    c1, c2 = palette[0], palette[1]
    for r in range(max_r, 0, -4):
        t = r / max_r
        color = (
            int(c1[0] * t + c2[0] * (1 - t)),
            int(c1[1] * t + c2[1] * (1 - t)),
            int(c1[2] * t + c2[2] * (1 - t)),
        )
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    return img


def _geometric(palette) -> Image.Image:
    img = _gradient(palette)
    draw = ImageDraw.Draw(img)
    c3 = palette[2]
    rng = random.Random(42)
    for _ in range(12):
        x = rng.randint(0, WIDTH)
        y = rng.randint(0, HEIGHT)
        size = rng.randint(60, 200)
        alpha = rng.randint(20, 60)
        points = [
            (x, y - size),
            (x + size * 0.866, y + size * 0.5),
            (x - size * 0.866, y + size * 0.5),
        ]
        draw.polygon(points, fill=(*c3, alpha))
    return img


def _particles(palette) -> Image.Image:
    img = _gradient(palette)
    draw = ImageDraw.Draw(img)
    c2, c3 = palette[1], palette[2]
    rng = random.Random(99)
    for _ in range(120):
        x = rng.randint(0, WIDTH)
        y = rng.randint(0, HEIGHT)
        r = rng.randint(2, 8)
        color = rng.choice([c2, c3])
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)
    return img
