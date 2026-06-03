"""
Content Research Engine — scrapes 4 free sources before script generation.
Feeds real current data into the AI prompt for specific, high-quality scripts.

Sources:
  1. Google News RSS      — latest news headlines + summaries
  2. Reddit (JSON API)    — viral community discussions + angles
  3. HackerNews (Algolia) — tech/startup trending stories
  4. Wikipedia            — factual background + key stats
"""

import re
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "TrendPulse/1.0 (content aggregator bot)"}
TIMEOUT = 10


def research_topic(topic: str) -> dict:
    """
    Returns a rich research bundle:
    {
        'topic': str,
        'headlines': list[dict],   # {title, source, summary}
        'reddit_posts': list[dict],# {title, score, subreddit, top_comment}
        'hn_stories': list[dict],  # {title, score, url}
        'wiki_summary': str,
        'research_text': str,      # formatted for prompt injection
    }
    """
    logger.info(f"Researching topic: {topic}")

    headlines    = _google_news(topic)
    reddit_posts = _reddit(topic)
    hn_stories   = _hackernews(topic)
    wiki_summary = _wikipedia(topic)

    research_text = _format_for_prompt(topic, headlines, reddit_posts, hn_stories, wiki_summary)

    logger.info(
        f"Research complete — {len(headlines)} news, "
        f"{len(reddit_posts)} reddit, {len(hn_stories)} HN"
    )

    return {
        "topic": topic,
        "headlines": headlines,
        "reddit_posts": reddit_posts,
        "hn_stories": hn_stories,
        "wiki_summary": wiki_summary,
        "research_text": research_text,
    }


# ── Source 1: Google News RSS ─────────────────────────────────────────────────

def _google_news(topic: str) -> list:
    try:
        url = f"https://news.google.com/rss/search?q={requests.utils.quote(topic)}&hl=en-US&gl=US&ceid=US:en"
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")[:6]

        results = []
        for item in items:
            title   = (item.findtext("title") or "").strip()
            source  = (item.findtext("source") or "Google News").strip()
            desc    = (item.findtext("description") or "").strip()
            # Strip HTML tags from description
            desc = re.sub(r"<[^>]+>", "", desc)[:200]
            if title:
                results.append({"title": title, "source": source, "summary": desc})

        logger.info(f"Google News: {len(results)} headlines")
        return results
    except Exception as e:
        logger.warning(f"Google News failed: {e}")
        return []


# ── Source 2: Reddit ──────────────────────────────────────────────────────────

def _reddit(topic: str) -> list:
    try:
        url = "https://www.reddit.com/search.json"
        params = {"q": topic, "sort": "hot", "limit": 8, "type": "link", "t": "week"}
        resp = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        posts = resp.json()["data"]["children"]

        results = []
        for p in posts[:5]:
            d = p["data"]
            title      = d.get("title", "").strip()
            score      = d.get("score", 0)
            subreddit  = d.get("subreddit", "")
            selftext   = d.get("selftext", "")[:150].strip()
            if title and score > 10:
                results.append({
                    "title":     title,
                    "score":     score,
                    "subreddit": subreddit,
                    "snippet":   selftext,
                })

        logger.info(f"Reddit: {len(results)} posts")
        return results
    except Exception as e:
        logger.warning(f"Reddit failed: {e}")
        return []


# ── Source 3: HackerNews (Algolia API) ───────────────────────────────────────

def _hackernews(topic: str) -> list:
    try:
        url = "https://hn.algolia.com/api/v1/search"
        params = {"query": topic, "tags": "story", "hitsPerPage": 5}
        resp = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])

        results = []
        for h in hits:
            title = (h.get("title") or h.get("story_title") or "").strip()
            score = h.get("points", 0) or 0
            url_  = h.get("url", "")
            if title and score > 5:
                results.append({"title": title, "score": score, "url": url_})

        logger.info(f"HackerNews: {len(results)} stories")
        return results
    except Exception as e:
        logger.warning(f"HackerNews failed: {e}")
        return []


# ── Source 4: Wikipedia ───────────────────────────────────────────────────────

def _wikipedia(topic: str) -> str:
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(topic.replace(' ', '_'))}"
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 200:
            data    = resp.json()
            extract = data.get("extract", "")
            return extract[:600] if extract else ""
    except Exception as e:
        logger.warning(f"Wikipedia failed: {e}")
    return ""


# ── Formatter ─────────────────────────────────────────────────────────────────

def _format_for_prompt(
    topic: str,
    headlines: list,
    reddit_posts: list,
    hn_stories: list,
    wiki_summary: str,
) -> str:
    sections = [f'REAL-TIME RESEARCH DATA FOR TOPIC: "{topic}"']
    sections.append(f"Research date: {datetime.now().strftime('%B %d, %Y')}\n")

    if headlines:
        sections.append("=== LATEST NEWS HEADLINES ===")
        for h in headlines[:5]:
            sections.append(f"• [{h['source']}] {h['title']}")
            if h["summary"]:
                sections.append(f"  {h['summary']}")
        sections.append("")

    if reddit_posts:
        sections.append("=== TRENDING ON REDDIT ===")
        for p in reddit_posts[:4]:
            sections.append(f"• r/{p['subreddit']} ({p['score']:,} upvotes): {p['title']}")
            if p["snippet"]:
                sections.append(f"  \"{p['snippet']}\"")
        sections.append("")

    if hn_stories:
        sections.append("=== HACKERNEWS DISCUSSION ===")
        for h in hn_stories[:3]:
            sections.append(f"• ({h['score']} pts) {h['title']}")
        sections.append("")

    if wiki_summary:
        sections.append("=== FACTUAL BACKGROUND (Wikipedia) ===")
        sections.append(wiki_summary[:400])
        sections.append("")

    sections.append("USE THIS DATA TO: ground your script in real facts, reference specific headlines, "
                    "use actual numbers and dates, reflect what people are actually discussing right now. "
                    "Do NOT copy any text verbatim — synthesize into original writing.")

    return "\n".join(sections)
