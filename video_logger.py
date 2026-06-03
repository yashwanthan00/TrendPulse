"""Logs each pipeline run to docs/history.json for the dashboard."""

import json
import os
from datetime import datetime, timezone

HISTORY_FILE = os.path.join("docs", "history.json")


def log_run(topic: str, mode: str, title: str, youtube_url: str, tags: list, status: str = "success", error: str = "", category: str = "General"):
    os.makedirs("docs", exist_ok=True)

    history = _load()
    history.insert(0, {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "topic": topic,
        "mode": mode,
        "category": category,
        "title": title,
        "youtube_url": youtube_url,
        "video_id": _extract_id(youtube_url),
        "tags": tags,
        "status": status,
        "error": error,
    })

    # keep last 90 days
    history = history[:90]
    _save(history)


def log_failure(topic: str, mode: str, error: str):
    log_run(topic, mode, topic, "", [], status="failed", error=str(error))


def _extract_id(url: str) -> str:
    if "v=" in url:
        return url.split("v=")[-1].split("&")[0]
    return ""


def _load() -> list:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return []


def _save(history: list):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)
