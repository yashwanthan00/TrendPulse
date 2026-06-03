"""
Builds the final MP4 with:
  - Ken Burns zoom/pan on image backgrounds
  - Looping video clips for video backgrounds
  - Animated text: fade-in + slide-up per slide
  - Crossfade transitions between slides
  - Dark overlay for readability
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# MoviePy 1.0.3 uses ANTIALIAS which was removed in Pillow 10+
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS
from moviepy.editor import (
    VideoFileClip, ImageClip, AudioFileClip,
    concatenate_videoclips, CompositeVideoClip,
    ColorClip, VideoClip,
)
from font_manager import get_font
import logging

logger = logging.getLogger(__name__)

VIDEO_SIZE = (1280, 720)
W, H = VIDEO_SIZE
FPS = 24
TRANSITION_DURATION = 0.4   # crossfade between slides
TEXT_FADE_IN = 0.5           # text fade-in duration
MAX_CHARS = 40


# ── Public entry point ────────────────────────────────────────────────────────

def build_video(slides: list, audio_paths: list, bg: dict, output_path: str) -> str:
    """
    bg: {'type': 'video'|'image', 'path': str}
    Assembles all slide clips into a single MP4. Returns output_path.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    clips = []
    for i, (text, audio_path) in enumerate(zip(slides, audio_paths)):
        clip = _build_slide(text, audio_path, bg, i, len(slides))
        clips.append(clip)

    # Crossfade transitions
    final = _crossfade_concat(clips)

    final.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        logger=None,
        threads=2,
    )
    logger.info(f"Video saved: {output_path}")
    return output_path


# ── Slide builder ─────────────────────────────────────────────────────────────

def _build_slide(text: str, audio_path: str, bg: dict, index: int, total: int) -> CompositeVideoClip:
    audio = AudioFileClip(audio_path)
    duration = audio.duration + 0.3

    # 1. Background layer
    if bg["type"] == "video":
        bg_clip = _video_background(bg["path"], duration)
    else:
        bg_clip = _ken_burns(bg["path"], duration, direction=index % 2)

    # 2. Dark overlay
    dark = ColorClip(VIDEO_SIZE, color=[0, 0, 0]).set_duration(duration).set_opacity(0.55)

    # 3. Animated text overlay
    text_clip = _animated_text(text, duration, font_size=48 if index == 0 else 42)

    # 4. Slide number indicator (small, bottom-left)
    num_clip = _slide_number(index + 1, total, duration)

    composite = CompositeVideoClip([bg_clip, dark, text_clip, num_clip]).set_audio(audio)
    return composite.set_fps(FPS)


# ── Background layers ─────────────────────────────────────────────────────────

def _ken_burns(img_path: str, duration: float, direction: int = 0) -> VideoClip:
    """Smooth zoom-in or zoom-out with subtle pan."""
    img = Image.open(img_path).convert("RGB")
    # Slightly oversized so we have room to zoom/pan
    big = img.resize((int(W * 1.15), int(H * 1.15)), Image.LANCZOS)
    arr = np.array(big)
    bh, bw = arr.shape[:2]

    def make_frame(t):
        progress = t / duration
        if direction == 0:
            # zoom in: start wide, end tight
            scale = 1.15 - 0.1 * progress
        else:
            # zoom out: start tight, end wide
            scale = 1.05 + 0.1 * progress

        cw = int(W * scale)
        ch = int(H * scale)
        cw = min(cw, bw)
        ch = min(ch, bh)

        # Subtle pan: drift diagonally
        x0 = int((bw - cw) * (0.3 + 0.4 * progress))
        y0 = int((bh - ch) * (0.2 + 0.3 * progress))
        x0 = max(0, min(x0, bw - cw))
        y0 = max(0, min(y0, bh - ch))

        cropped = arr[y0:y0 + ch, x0:x0 + cw]
        return np.array(Image.fromarray(cropped).resize((W, H), Image.LANCZOS))

    return VideoClip(make_frame, duration=duration).set_fps(FPS)


def _video_background(video_path: str, duration: float) -> VideoFileClip:
    """Loop / trim a video clip to match duration."""
    clip = VideoFileClip(video_path).without_audio().resize(VIDEO_SIZE)
    if clip.duration < duration:
        # Loop
        loops = int(duration / clip.duration) + 2
        from moviepy.editor import concatenate_videoclips
        clip = concatenate_videoclips([clip] * loops).subclip(0, duration)
    else:
        clip = clip.subclip(0, duration)
    return clip


# ── Text overlay ──────────────────────────────────────────────────────────────

def _animated_text(text: str, duration: float, font_size: int = 42) -> VideoClip:
    """
    Text that fades in and slides up over TEXT_FADE_IN seconds.
    Rendered as a VideoClip with transparent background composited onto the scene.
    """
    font = get_font(font_size, "bold")
    lines = _wrap_text(text)
    line_h = font_size + 14
    total_text_h = len(lines) * line_h
    y_center = (H - total_text_h) // 2
    SLIDE_OFFSET = 22  # px to slide up from

    def make_frame(t):
        alpha = min(1.0, t / TEXT_FADE_IN)
        offset = int(SLIDE_OFFSET * (1 - alpha))

        # Transparent RGBA canvas
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            x = (W - tw) // 2
            y = y_center + i * line_h + offset

            # Subtle text shadow
            shadow_a = int(200 * alpha)
            draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, shadow_a))
            # Main text
            text_a = int(255 * alpha)
            draw.text((x, y), line, font=font, fill=(255, 255, 255, text_a))

        # Convert to RGB + mask
        rgb = np.array(canvas.convert("RGB"))
        mask = np.array(canvas.split()[3]) / 255.0  # alpha channel as float mask
        return rgb, mask

    # Build clip frame by frame
    def rgb_frame(t):
        return make_frame(t)[0]

    def mask_frame(t):
        return make_frame(t)[1]

    clip = VideoClip(rgb_frame, duration=duration).set_fps(FPS)
    clip = clip.set_mask(VideoClip(mask_frame, duration=duration, ismask=True).set_fps(FPS))
    return clip


def _slide_number(current: int, total: int, duration: float) -> VideoClip:
    """Small slide counter in bottom-left corner."""
    font = get_font(18, "regular")

    def make_frame(t):
        alpha = min(1.0, t / TEXT_FADE_IN)
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        label = f"{current} / {total}"
        a = int(160 * alpha)
        draw.text((28, H - 38), label, font=font, fill=(200, 200, 200, a))
        rgb = np.array(canvas.convert("RGB"))
        mask = np.array(canvas.split()[3]) / 255.0
        return rgb, mask

    def rgb_f(t): return make_frame(t)[0]
    def msk_f(t): return make_frame(t)[1]

    clip = VideoClip(rgb_f, duration=duration).set_fps(FPS)
    clip = clip.set_mask(VideoClip(msk_f, duration=duration, ismask=True).set_fps(FPS))
    return clip


# ── Transitions ───────────────────────────────────────────────────────────────

def _crossfade_concat(clips: list) -> VideoClip:
    """Concatenate clips with crossfade transitions between each."""
    if len(clips) == 1:
        return clips[0]

    result = clips[0].crossfadeout(TRANSITION_DURATION)
    for i in range(1, len(clips)):
        next_clip = clips[i]
        if i < len(clips) - 1:
            next_clip = next_clip.crossfadeout(TRANSITION_DURATION)
        next_clip = next_clip.crossfadein(TRANSITION_DURATION)
        result = concatenate_videoclips(
            [result, next_clip],
            padding=-TRANSITION_DURATION,
            method="compose",
        )
    return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _wrap_text(text: str) -> list:
    words = text.split()
    lines, current = [], ""
    for word in words:
        if len(current) + len(word) + 1 <= MAX_CHARS:
            current = f"{current} {word}".strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines
