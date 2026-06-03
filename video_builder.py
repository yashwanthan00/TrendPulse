"""
Professional YouTube video builder.
Looks like a real broadcast/documentary — NOT a presentation.

Visual design:
  - Cinematic Pexels video or Ken Burns image background
  - Vignette + colour grade overlay
  - Slide 1: Full-screen title card with category badge
  - Slides 2-4: Lower-third text box (slides in from left like news)
  - Slide 5: Branded CTA card with subscribe animation
  - Progress bar across the top
  - Channel handle watermark bottom-right
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from moviepy.editor import (
    VideoFileClip, ImageClip, AudioFileClip,
    concatenate_videoclips, CompositeVideoClip,
    ColorClip, VideoClip,
)
from font_manager import get_font
import logging

# Pillow 10+ compatibility
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS

logger = logging.getLogger(__name__)

VIDEO_SIZE   = (1280, 720)
W, H         = VIDEO_SIZE
FPS          = 24
CHANNEL      = "@yeah_shh"
ACCENT       = (99, 102, 241)      # indigo
ACCENT_DARK  = (49,  46, 129)
WHITE        = (255, 255, 255)
BLACK        = (0,   0,   0)


# ── Entry point ───────────────────────────────────────────────────────────────

def build_video(slides: list, audio_paths: list, bg: dict, output_path: str, category: str = "") -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    clips = []
    total = len(slides)
    for i, (text, audio) in enumerate(zip(slides, audio_paths)):
        if i == 0:
            clip = _title_card(text, audio, bg, category, total)
        elif i == total - 1:
            clip = _cta_card(text, audio, bg, total)
        else:
            clip = _content_card(text, audio, bg, i, total)
        clips.append(clip)

    final = _crossfade(clips)
    final.write_videofile(output_path, fps=FPS, codec="libx264",
                          audio_codec="aac", logger=None, threads=2)
    logger.info(f"Video saved: {output_path}")
    return output_path


# ── Card builders ─────────────────────────────────────────────────────────────

def _title_card(text: str, audio_path: str, bg: dict, category: str, total: int) -> CompositeVideoClip:
    """Slide 1 — full-screen dramatic title."""
    audio    = AudioFileClip(audio_path)
    duration = audio.duration + 0.4
    bg_clip  = _background(bg, duration)

    def frame(t):
        img = _base_frame(bg_clip, t, duration, 1, total)
        draw = ImageDraw.Draw(img)

        # Category badge top-centre
        if category:
            badge_font = get_font(22, "bold")
            badge_text = f"  {category.upper()}  "
            bb = draw.textbbox((0,0), badge_text, font=badge_font)
            bw = bb[2]-bb[0]+20
            bx = (W - bw) // 2
            alpha = min(1.0, t / 0.3)
            br = int(80 * alpha); bg_a = int(60 * alpha)
            draw.rounded_rectangle([bx, 36, bx+bw, 72], radius=8,
                                   fill=(*ACCENT, bg_a), outline=(*ACCENT, br))
            draw.text((bx+10, 42), badge_text, font=badge_font,
                      fill=(*WHITE, int(255*alpha)))

        # Main title — big, bold, centred
        alpha  = min(1.0, t / 0.5)
        offset = int(30 * (1 - alpha))
        font   = get_font(58, "bold")
        lines  = _wrap(text, 32)
        lh     = 70
        y0     = (H - len(lines)*lh) // 2 + offset
        for i2, line in enumerate(lines):
            bb  = draw.textbbox((0,0), line, font=font)
            x   = (W - (bb[2]-bb[0])) // 2
            y   = y0 + i2*lh
            # soft shadow
            draw.text((x+3, y+3), line, font=font, fill=(0,0,0,int(180*alpha)))
            draw.text((x,   y  ), line, font=font, fill=(*WHITE, int(255*alpha)))

        return np.array(img.convert("RGB"))

    return _make_clip(frame, duration, audio)


def _content_card(text: str, audio_path: str, bg: dict, idx: int, total: int) -> CompositeVideoClip:
    """Slides 2-4 — lower-third news style with slide-in animation."""
    audio    = AudioFileClip(audio_path)
    duration = audio.duration + 0.4
    bg_clip  = _background(bg, duration)

    def frame(t):
        img  = _base_frame(bg_clip, t, duration, idx+1, total)
        draw = ImageDraw.Draw(img)

        # Slide-in progress: 0→1 over 0.4s
        alpha   = min(1.0, t / 0.4)
        slide_x = int((1 - alpha) * -W * 0.6)   # slides in from left

        # Lower-third box (bottom 38% of screen)
        box_y = int(H * 0.62)
        box_h = H - box_y

        # Gradient box
        box = Image.new("RGBA", (W, box_h), (0,0,0,0))
        bd  = ImageDraw.Draw(box)
        for y in range(box_h):
            a = int(200 * (y / box_h))
            bd.line([(0,y),(W,y)], fill=(0,0,0,a))
        img = Image.alpha_composite(img.convert("RGBA"), Image.new("RGBA", (W,H), (0,0,0,0)))

        # Re-get full frame since we need composite
        img = _base_frame(bg_clip, t, duration, idx+1, total)
        base_arr = np.array(img.convert("RGBA"))
        overlay  = np.zeros_like(base_arr)
        for y2 in range(box_y, H):
            a2 = int(210 * ((y2 - box_y) / (H - box_y)))
            overlay[y2,:] = [0, 0, 0, a2]
        combined = Image.alpha_composite(
            Image.fromarray(base_arr),
            Image.fromarray(overlay.astype(np.uint8))
        ).convert("RGB")
        img = combined

        draw = ImageDraw.Draw(img)

        # Accent line
        accent_a = int(255 * alpha)
        draw.rectangle([slide_x, box_y, slide_x + 5, H],
                       fill=(*ACCENT, accent_a))

        # Text
        font  = get_font(40, "bold")
        lines = _wrap(text, 48)
        lh    = 52
        total_h = len(lines) * lh
        y0 = box_y + (box_h - total_h) // 2 + 10
        for i2, line in enumerate(lines):
            tx = slide_x + 24
            ty = y0 + i2 * lh
            draw.text((tx+2, ty+2), line, font=font, fill=(0,0,0))
            draw.text((tx,   ty  ), line, font=font, fill=WHITE)

        return np.array(img)

    return _make_clip(frame, duration, audio)


def _cta_card(text: str, audio_path: str, bg: dict, total: int) -> CompositeVideoClip:
    """Last slide — branded CTA with subscribe button."""
    audio    = AudioFileClip(audio_path)
    duration = audio.duration + 0.4
    bg_clip  = _background(bg, duration)

    def frame(t):
        img  = _base_frame(bg_clip, t, duration, total, total)
        draw = ImageDraw.Draw(img)
        alpha = min(1.0, t / 0.5)

        # Dark centre panel
        panel_w, panel_h = 700, 260
        px = (W - panel_w) // 2
        py = (H - panel_h) // 2
        panel = Image.new("RGBA", (W, H), (0,0,0,0))
        pd    = ImageDraw.Draw(panel)
        pd.rounded_rectangle([px, py, px+panel_w, py+panel_h], radius=18,
                             fill=(0,0,0, int(190*alpha)))
        pd.rounded_rectangle([px, py, px+panel_w, py+panel_h], radius=18,
                             outline=(*ACCENT, int(180*alpha)), width=2)
        img = Image.alpha_composite(img.convert("RGBA"), panel).convert("RGB")
        draw = ImageDraw.Draw(img)

        # Subscribe button
        btn_w, btn_h = 260, 52
        bx = (W - btn_w) // 2
        by = py + 28
        draw.rounded_rectangle([bx, by, bx+btn_w, by+btn_h], radius=26,
                               fill=(200, 0, 0))
        sub_font = get_font(22, "bold")
        draw.text((bx + btn_w//2 - 55, by + 14), "▶  Subscribe", font=sub_font, fill=WHITE)

        # Channel handle
        h_font = get_font(36, "bold")
        handle = CHANNEL
        hb     = draw.textbbox((0,0), handle, font=h_font)
        hx     = (W - (hb[2]-hb[0])) // 2
        draw.text((hx+2, py+102), handle, font=h_font, fill=(0,0,0))
        draw.text((hx,   py+100), handle, font=h_font, fill=(*ACCENT, int(255*alpha)))

        # CTA text
        cta_font  = get_font(26, "regular")
        cta_lines = _wrap(text, 42)
        cy = py + 155
        for line in cta_lines:
            cb  = draw.textbbox((0,0), line, font=cta_font)
            cx2 = (W - (cb[2]-cb[0])) // 2
            draw.text((cx2, cy), line, font=cta_font,
                      fill=(*WHITE, int(200*alpha)))
            cy += 34

        return np.array(img)

    return _make_clip(frame, duration, audio)


# ── Background engine ─────────────────────────────────────────────────────────

def _background(bg: dict, duration: float):
    if bg["type"] == "video":
        return _video_bg(bg["path"], duration)
    return _ken_burns(bg["path"], duration)


def _video_bg(path: str, duration: float) -> VideoFileClip:
    clip = VideoFileClip(path).without_audio().resize(VIDEO_SIZE)
    if clip.duration < duration:
        from moviepy.editor import concatenate_videoclips as cc
        loops = int(duration / clip.duration) + 2
        clip  = cc([clip] * loops).subclip(0, duration)
    else:
        clip = clip.subclip(0, duration)
    return clip


def _ken_burns(path: str, duration: float) -> VideoClip:
    img   = Image.open(path).convert("RGB")
    big   = img.resize((int(W*1.15), int(H*1.15)), Image.LANCZOS)
    arr   = np.array(big)
    bh, bw = arr.shape[:2]

    def frame(t):
        p  = t / duration
        scale = 1.15 - 0.10 * p
        cw = min(int(W * scale), bw)
        ch = min(int(H * scale), bh)
        x0 = max(0, min(int((bw-cw) * 0.4 * p), bw-cw))
        y0 = max(0, min(int((bh-ch) * 0.3 * p), bh-ch))
        return np.array(Image.fromarray(arr[y0:y0+ch, x0:x0+cw]).resize((W,H), Image.LANCZOS))

    return VideoClip(frame, duration=duration).set_fps(FPS)


# ── Base frame (bg + vignette + progress + watermark) ────────────────────────

def _base_frame(bg_clip, t: float, duration: float, slide_num: int, total: int) -> Image.Image:
    # Background
    raw = bg_clip.get_frame(min(t, bg_clip.duration - 0.01))
    img = Image.fromarray(raw.astype("uint8")).convert("RGBA")

    # Subtle colour grade — slight cool blue tint
    grade = Image.new("RGBA", (W, H), (10, 20, 40, 40))
    img   = Image.alpha_composite(img, grade)

    # Vignette
    img = _apply_vignette(img)

    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    # Progress bar at top
    progress = slide_num / total
    draw.rectangle([0, 0, W, 4], fill=(30, 30, 50))
    draw.rectangle([0, 0, int(W * progress), 4], fill=ACCENT)

    # Channel watermark bottom-right
    wm_font = get_font(18, "regular")
    wm_text = CHANNEL
    wb = draw.textbbox((0,0), wm_text, font=wm_font)
    wx = W - (wb[2]-wb[0]) - 16
    draw.text((wx+1, H-30), wm_text, font=wm_font, fill=(0,0,0,180))
    draw.text((wx,   H-31), wm_text, font=wm_font, fill=(200,200,200,160))

    return img


def _apply_vignette(img: Image.Image) -> Image.Image:
    vignette = Image.new("RGBA", (W, H), (0,0,0,0))
    draw     = ImageDraw.Draw(vignette)
    steps    = 60
    for i in range(steps):
        alpha = int(130 * ((steps - i) / steps) ** 2.5)
        margin = i * 6
        draw.rectangle([margin, margin, W-margin, H-margin],
                      outline=(0,0,0,alpha), width=1)
    return Image.alpha_composite(img.convert("RGBA"), vignette)


# ── Transitions ───────────────────────────────────────────────────────────────

def _crossfade(clips: list) -> VideoClip:
    TD = 0.35
    if len(clips) == 1:
        return clips[0]
    result = clips[0].crossfadeout(TD)
    for i in range(1, len(clips)):
        nxt = clips[i].crossfadein(TD)
        if i < len(clips)-1:
            nxt = nxt.crossfadeout(TD)
        result = concatenate_videoclips([result, nxt], padding=-TD, method="compose")
    return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_clip(frame_fn, duration: float, audio: AudioFileClip) -> CompositeVideoClip:
    clip = VideoClip(frame_fn, duration=duration).set_fps(FPS).set_audio(audio)
    return clip


def _wrap(text: str, max_chars: int = 40) -> list:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_chars:
            cur = f"{cur} {w}".strip()
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines
