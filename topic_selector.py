"""
Decides whether today's video should be trending news or an educational lesson,
then returns a topic + mode ('trending' | 'educational').

Alternates daily so the channel has variety.
"""

import logging
import requests
import random
from datetime import datetime

logger = logging.getLogger(__name__)

EDUCATIONAL_TOPICS = [
    # Science
    "How Black Holes Are Formed",
    "What is Quantum Entanglement",
    "How the Human Immune System Works",
    "What is CRISPR Gene Editing",
    "How Solar Panels Generate Electricity",
    "What is Dark Matter",
    "How Vaccines Train Your Immune System",
    "What is the Theory of Relativity",
    # Tech
    "How Machine Learning Works",
    "What is a Neural Network",
    "How Blockchain Technology Works",
    "What is End-to-End Encryption",
    "How GPS Satellites Work",
    "What is Quantum Computing",
    "How the Internet Works",
    "What is the Metaverse",
    # History & Society
    "What Caused the 2008 Financial Crisis",
    "How Democracy Was Born in Ancient Greece",
    "What is the Butterfly Effect",
    "How the Cold War Started",
    # Health
    "How Sleep Affects Your Brain",
    "What Happens When You Fast",
    "How Stress Damages the Body",
    "What is the Gut-Brain Connection",
    # Finance
    "How Compound Interest Works",
    "What is Inflation and Why It Matters",
    "How Stock Markets Work",
    "What is Passive Income",
]


def select_topic_and_mode() -> dict:
    """
    Returns {'topic': str, 'mode': 'trending' | 'educational', 'wikipedia_summary': str | None}
    Alternates between trending and educational every other day.
    """
    day_of_year = datetime.now().timetuple().tm_yday

    if day_of_year % 2 == 0:
        mode = "educational"
        topic = _pick_educational_topic(day_of_year)
        summary = _fetch_wikipedia_summary(topic)
    else:
        mode = "trending"
        topic = None  # trend_fetcher handles this
        summary = None

    return {"mode": mode, "topic": topic, "wikipedia_summary": summary}


def _pick_educational_topic(day_of_year: int) -> str:
    idx = (day_of_year // 2) % len(EDUCATIONAL_TOPICS)
    return EDUCATIONAL_TOPICS[idx]


def _fetch_wikipedia_summary(topic: str) -> str | None:
    """
    Fetch a short Wikipedia summary for factual grounding.
    Wikipedia content is CC BY-SA — we use it as a source, not verbatim copy.
    """
    try:
        search_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + topic.replace(" ", "_")
        resp = requests.get(search_url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            summary = data.get("extract", "")
            # truncate to first 500 chars to avoid verbatim copying
            return summary[:500] if summary else None
    except Exception as e:
        logger.warning(f"Wikipedia fetch failed: {e}")
    return None
