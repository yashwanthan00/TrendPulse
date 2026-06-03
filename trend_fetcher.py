"""
Fetches today's trending topic with triple-redundant fallback:
  1. Google Trends (pytrends)
  2. Reddit r/popular (no API key needed)
  3. BBC News RSS feed
  4. Hardcoded rotating topics (last resort)
"""

import logging
import random
import xml.etree.ElementTree as ET
from datetime import datetime

import requests
from pytrends.request import TrendReq

logger = logging.getLogger(__name__)

FALLBACK_TOPICS = [
    "Artificial Intelligence", "Climate Change", "Space Exploration",
    "Electric Vehicles", "Cryptocurrency", "Mental Health Awareness",
    "Renewable Energy", "Quantum Computing", "Cybersecurity",
    "Gene Editing", "Social Media Trends", "Remote Work Future",
    "Inflation and Economy", "Robotics", "Augmented Reality",
]


def get_trending_topic() -> str:
    """Try each source in order; return the first successful topic."""
    sources = [
        ("Google Trends", _from_google_trends),
        ("Reddit r/popular", _from_reddit),
        ("BBC News RSS", _from_bbc_rss),
        ("Rotating fallback", _from_fallback),
    ]

    for name, fn in sources:
        try:
            topic = fn()
            if topic:
                logger.info(f"Trending topic from {name}: {topic}")
                return topic
        except Exception as e:
            logger.warning(f"{name} failed: {e}")

    return "Today's Big Story"  # absolute last resort


# ── Source 1: Google Trends ──────────────────────────────────────────────────

def _from_google_trends() -> str:
    pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
    trending = pytrends.trending_searches(pn="united_states")
    topic = trending.iloc[0, 0]
    if not topic:
        raise ValueError("Empty response")
    return str(topic)


# ── Source 2: Reddit r/popular (public JSON, no key needed) ──────────────────

def _from_reddit() -> str:
    headers = {"User-Agent": "TrendPulse/1.0 (automated content bot)"}
    resp = requests.get(
        "https://www.reddit.com/r/popular.json?limit=5",
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    posts = resp.json()["data"]["children"]

    # pick the top post title, strip flair/junk
    for post in posts:
        title = post["data"].get("title", "").strip()
        if len(title) > 10:
            # shorten to a usable search query (first 6 words)
            words = title.split()[:6]
            return " ".join(words)

    raise ValueError("No usable Reddit posts found")


# ── Source 3: BBC News RSS ────────────────────────────────────────────────────

def _from_bbc_rss() -> str:
    resp = requests.get("https://feeds.bbci.co.uk/news/rss.xml", timeout=10)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    items = root.findall(".//item/title")
    for item in items:
        title = (item.text or "").strip()
        if len(title) > 10 and title.lower() != "bbc news":
            return title
    raise ValueError("No usable BBC headlines")


# ── Source 4: Rotating hardcoded topics (always works) ───────────────────────

def _from_fallback() -> str:
    # rotate by day of year so it doesn't repeat the same topic consecutively
    idx = datetime.now().timetuple().tm_yday % len(FALLBACK_TOPICS)
    return FALLBACK_TOPICS[idx]
