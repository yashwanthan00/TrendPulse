"""TrendPulse — Daily YouTube content pipeline.
100% copyright-free: generated backgrounds, open-source fonts, AI-original scripts.
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

from topic_selector import select_topic_and_mode
from trend_fetcher import get_trending_topic
from content_researcher import research_topic
from script_generator import generate_script
from tts_generator import synthesize_slides
from media_fetcher import fetch_background
from video_builder import build_video
from copyright_checker import run_full_audit
from youtube_uploader import upload_video
from video_logger import log_run, log_failure
from shorts_pipeline import run_shorts_pipeline

load_dotenv()

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"logs/run_{datetime.now().strftime('%Y%m%d')}.log"),
    ],
)
logger = logging.getLogger(__name__)


def run():
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join("output", date_str)
    audio_dir = os.path.join(run_dir, "audio")
    os.makedirs(run_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)

    logger.info("=== TrendPulse pipeline started ===")

    # Step 1: Select today's mode and topic
    selection = select_topic_and_mode()
    mode      = selection["mode"]
    category  = selection.get("category", "General")
    wikipedia_summary = selection.get("wikipedia_summary")
    topic     = selection["topic"] if mode != "trending" else get_trending_topic()
    logger.info(f"Category: {category} | Mode: {mode} | Topic: {topic}")

    # Step 2: Research topic across Google News, Reddit, HackerNews, Wikipedia
    research = research_topic(topic)

    # Step 3: Generate script grounded in real research
    script = generate_script(topic, mode=mode, wikipedia_summary=wikipedia_summary, research=research, category=category)

    # Step 4: Fetch background media (video clip > image > generated)
    bg = fetch_background(topic, run_dir)

    # Step 5: Full copyright audit — halt on errors
    audit = run_full_audit(script, bg["provider"])
    script = audit["script"]

    if not audit["passed"]:
        logger.error("Copyright audit FAILED — aborting upload to protect the channel.")
        log_failure(topic, mode, "Copyright audit failed: " + str(audit["errors"]))
        sys.exit(1)

    # Step 5: Text-to-speech narration (edge-tts, original audio)
    audio_paths = synthesize_slides(script["slides"], audio_dir)

    # Step 6: Build video
    video_path = os.path.join(run_dir, "video.mp4")
    build_video(script["slides"], audio_paths, bg, video_path, category=category)

    # Step 7: Upload to YouTube
    url = upload_video(
        video_path=video_path,
        title=script["title"],
        description=script["description"],
        tags=script["tags"],
    )

    # Step 8: Log to dashboard
    log_run(
        topic=topic,
        mode=mode,
        title=script["title"],
        youtube_url=url,
        tags=script["tags"],
        category=category,
    )

    logger.info(f"=== Done! Video live at: {url} ===")
    print(f"\nVideo uploaded: {url}")

    # Step 9: Create and upload a Short from existing channel videos
    logger.info("=== Starting Shorts pipeline ===")
    shorts_dir = os.path.join(run_dir, "shorts")
    short_url = run_shorts_pipeline(shorts_dir)
    if short_url:
        logger.info(f"Short uploaded: {short_url}")
        print(f"Short uploaded: {short_url}")
    else:
        logger.warning("Shorts pipeline did not produce a video")


if __name__ == "__main__":
    run()
