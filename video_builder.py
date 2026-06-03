"""
Builds the final MP4 from slides + audio + programmatically generated backgrounds.
All visuals are 100% original — no external images, no copyrighted assets.
Font: Roboto (Apache 2.0 — free for commercial use).
"""

import os
from PIL import Image, ImageDraw
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips
from font_manager import get_font
import logging

logger = logging.getLogger(__name__)

VIDEO_SIZE = (1280, 720)
FPS = 24
TEXT_COLOR = (255, 255, 255)
SHADOW_COLOR = (0, 0, 0)
OVERLAY_OPACITY = 150   # 0-255, darkens background so text pops
MAX_CHARS_PER_LINE = 42


def _wrap_text(text: str) -> list:
    words = text.split()
    lines, current = [], ""
    for word in words:
        if len(current) + len(word) + 1 <= MAX_CHARS_PER_LINE:
            current = f"{current} {word}".strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _create_slide_image(text: str, bg_path: str, output_path: str, slide_index: int):
    """Overlay text on the programmatic background. No external assets used."""
    bg = Image.open(bg_path).convert("RGB").resize(VIDEO_SIZE)

    # dark semi-transparent overlay for readability
    overlay = Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, OVERLAY_OPACITY))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(bg)

    # title font for slide 1, body font for the rest
    font_size = 52 if slide_index == 0 else 44
    font = get_font(font_size, weight="bold")

    lines = _wrap_text(text)
    line_height = font_size + 16
    total_height = len(lines) * line_height
    y_start = (VIDEO_SIZE[1] - total_height) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (VIDEO_SIZE[0] - text_w) // 2
        y = y_start + i * line_height

        # drop shadow
        draw.text((x + 2, y + 2), line, font=font, fill=SHADOW_COLOR)
        # main text
        draw.text((x, y), line, font=font, fill=TEXT_COLOR)

    # subtle slide number indicator
    num_font = get_font(20, weight="regular")
    draw.text((30, VIDEO_SIZE[1] - 40), f"{slide_index + 1}", font=num_font, fill=(180, 180, 180))

    bg.save(output_path)


def build_video(
    slides: list,
    audio_paths: list,
    bg_path: str,
    output_path: str,
) -> str:
    """Assemble slide clips into a single MP4. Returns output_path."""
    slide_dir = os.path.join(os.path.dirname(output_path), "slides")
    os.makedirs(slide_dir, exist_ok=True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    clips = []
    for i, (text, audio_path) in enumerate(zip(slides, audio_paths)):
        slide_img_path = os.path.join(slide_dir, f"slide_{i}.png")
        _create_slide_image(text, bg_path, slide_img_path, i)

        audio = AudioFileClip(audio_path)
        duration = audio.duration + 0.4

        clip = ImageClip(slide_img_path, duration=duration).set_audio(audio).set_fps(FPS)
        clips.append(clip)

    final = concatenate_videoclips(clips, method="compose")
    final.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        logger=None,
    )
    logger.info(f"Video saved: {output_path}")
    return output_path
