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
from script_generator import generate_script
from tts_generator import synthesize_slides
from image_fetcher import fetch_image
from video_builder import build_video
from copyright_checker import run_full_audit
from youtube_uploader import upload_video
from video_logger import log_run, log_failure

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
    mode = selection["mode"]
    wikipedia_summary = selection.get("wikipedia_summary")
    topic = selection["topic"] if mode == "educational" else get_trending_topic()
    logger.info(f"Mode: {mode} | Topic: {topic}")

    # Step 2: Generate original AI script
    script = generate_script(topic, mode=mode, wikipedia_summary=wikipedia_summary)

    # Step 3: Generate 100% original background (no external images)
    bg_path = os.path.join(run_dir, "background.jpg")
    image_result = fetch_image(topic, bg_path)

    # Step 4: Full copyright audit — halt on errors
    audit = run_full_audit(script, image_result["provider"])
    script = audit["script"]

    if not audit["passed"]:
        logger.error("Copyright audit FAILED — aborting upload to protect the channel.")
        log_failure(topic, mode, "Copyright audit failed: " + str(audit["errors"]))
        sys.exit(1)

    # Step 5: Text-to-speech narration (edge-tts, original audio)
    audio_paths = synthesize_slides(script["slides"], audio_dir)

    # Step 6: Build video
    video_path = os.path.join(run_dir, "video.mp4")
    build_video(script["slides"], audio_paths, image_result["path"], video_path)

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
    )

    logger.info(f"=== Done! Video live at: {url} ===")
    print(f"\nVideo uploaded: {url}")


if __name__ == "__main__":
    run()
