"""
Background image provider.
Primary: programmatically generated (background_generator.py) — zero copyright risk.
Images from Pexels/Unsplash are disabled by default to avoid any licensing ambiguity.
Set USE_EXTERNAL_IMAGES=true in .env only if you accept CC0 license terms.
"""

import os
import logging
from dotenv import load_dotenv
from background_generator import generate_background
from datetime import datetime

load_dotenv()
logger = logging.getLogger(__name__)

USE_EXTERNAL_IMAGES = os.getenv("USE_EXTERNAL_IMAGES", "false").lower() == "true"
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")


def fetch_image(query: str, save_path: str) -> dict:
    """
    Returns {'path': str, 'source_url': str, 'provider': str}.
    By default uses generated backgrounds (100% original, no copyright).
    """
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    seed = datetime.now().timetuple().tm_yday

    if USE_EXTERNAL_IMAGES and PEXELS_API_KEY:
        try:
            result = _from_pexels(query, save_path)
            logger.info(f"External image (CC0 Pexels): {result['source_url']}")
            return result
        except Exception as e:
            logger.warning(f"Pexels failed: {e} — falling back to generated background")

    # Default: fully original programmatic background
    path = generate_background(save_path, seed=seed)
    logger.info("Using programmatically generated background (100% original)")
    return {"path": path, "source_url": "generated", "provider": "Generated"}


def _from_pexels(query: str, save_path: str) -> dict:
    import requests
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": 1, "orientation": "landscape"}
    resp = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    photos = resp.json().get("photos", [])
    if not photos:
        raise ValueError("No Pexels results")
    img_url = photos[0]["src"]["large"]
    source_url = photos[0]["url"]
    data = requests.get(img_url, timeout=15).content
    with open(save_path, "wb") as f:
        f.write(data)
    return {"path": save_path, "source_url": source_url, "provider": "Pexels-CC0"}
