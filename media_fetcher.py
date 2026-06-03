"""
Fetches the best available background media for the video.
Priority: Pexels video clip → Pexels image → programmatic background.
All sources are CC0 / 100% original.
"""

import os
import requests
import logging
from dotenv import load_dotenv
from background_generator import generate_background
from datetime import datetime

load_dotenv()
logger = logging.getLogger(__name__)

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")


def fetch_background(query: str, save_dir: str) -> dict:
    """
    Returns {'type': 'video'|'image', 'path': str, 'provider': str}
    """
    os.makedirs(save_dir, exist_ok=True)
    seed = datetime.now().timetuple().tm_yday

    if PEXELS_API_KEY:
        # Try video first
        try:
            path = _pexels_video(query, os.path.join(save_dir, "background.mp4"))
            logger.info(f"Background video from Pexels: {query}")
            return {"type": "video", "path": path, "provider": "Pexels-CC0"}
        except Exception as e:
            logger.warning(f"Pexels video failed: {e}")

        # Try image
        try:
            path = _pexels_image(query, os.path.join(save_dir, "background.jpg"))
            logger.info(f"Background image from Pexels: {query}")
            return {"type": "image", "path": path, "provider": "Pexels-CC0"}
        except Exception as e:
            logger.warning(f"Pexels image failed: {e}")

    # Programmatic background — always works, zero copyright
    path = generate_background(os.path.join(save_dir, "background.jpg"), seed=seed)
    logger.info("Using programmatically generated background")
    return {"type": "image", "path": path, "provider": "Generated"}


def _pexels_video(query: str, save_path: str) -> str:
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": 3, "orientation": "landscape", "size": "medium"}
    resp = requests.get("https://api.pexels.com/videos/search", headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    videos = resp.json().get("videos", [])
    if not videos:
        raise ValueError("No Pexels videos found")

    # Pick best HD file
    video_files = videos[0]["video_files"]
    hd = next((f for f in video_files if f.get("quality") == "hd"), video_files[0])
    url = hd["link"]

    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
    return save_path


def _pexels_image(query: str, save_path: str) -> str:
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": 1, "orientation": "landscape"}
    resp = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    photos = resp.json().get("photos", [])
    if not photos:
        raise ValueError("No Pexels images found")
    img_url = photos[0]["src"]["large2x"]
    data = requests.get(img_url, timeout=15).content
    with open(save_path, "wb") as f:
        f.write(data)
    return save_path
