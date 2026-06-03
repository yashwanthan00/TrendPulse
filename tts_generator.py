"""Converts text to speech using edge-tts (free, no API key)."""

import asyncio
import edge_tts
import logging
import os

logger = logging.getLogger(__name__)

VOICE = "en-US-AriaNeural"  # natural-sounding free voice


async def _synthesize(text: str, output_path: str):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_path)


def text_to_speech(text: str, output_path: str) -> str:
    """Generate an MP3 file from text. Returns the output path."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    asyncio.run(_synthesize(text, output_path))
    logger.info(f"TTS saved: {output_path}")
    return output_path


def synthesize_slides(slides: list, audio_dir: str) -> list:
    """Generate one audio file per slide. Returns list of audio paths."""
    paths = []
    for i, slide_text in enumerate(slides):
        path = os.path.join(audio_dir, f"slide_{i}.mp3")
        text_to_speech(slide_text, path)
        paths.append(path)
    return paths
