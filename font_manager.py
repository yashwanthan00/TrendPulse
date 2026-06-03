"""
Downloads and caches open-source fonts (SIL Open Font License — free for any use).
Uses Roboto from Google Fonts, which is Apache 2.0 licensed (100% free, commercial use OK).
"""

import os
import logging
import requests
from PIL import ImageFont

logger = logging.getLogger(__name__)

FONTS_DIR = os.path.join(os.path.dirname(__file__), "assets", "fonts")

# Roboto — Apache License 2.0, free for any use including commercial YouTube
# Roboto variable font — covers all weights (Apache 2.0)
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/roboto/Roboto%5Bwdth%2Cwght%5D.ttf"
FONT_URLS = {
    "regular": FONT_URL,
    "bold":    FONT_URL,
}


def get_font(size: int, weight: str = "bold") -> ImageFont.FreeTypeFont:
    """Return a Roboto font at the given size. Downloads once, cached locally."""
    os.makedirs(FONTS_DIR, exist_ok=True)
    font_path = os.path.join(FONTS_DIR, f"Roboto-{weight.capitalize()}.ttf")

    if not os.path.exists(font_path):
        _download_font(weight, font_path)

    try:
        return ImageFont.truetype(font_path, size)
    except Exception as e:
        logger.warning(f"Font load failed: {e} — using default")
        return ImageFont.load_default()


def _download_font(weight: str, save_path: str):
    url = FONT_URLS.get(weight, FONT_URLS["bold"])
    logger.info(f"Downloading Roboto ({weight}) from Google Fonts...")
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    with open(save_path, "wb") as f:
        f.write(resp.content)
    logger.info(f"Font saved: {save_path}")
