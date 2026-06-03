"""
Original YouTube Shorts generator — no downloading needed.
Creates a fresh 45-second vertical (9:16) video daily from a different
topic than the main video, with @yeah_shh branding.
"""

import os
import sys
import logging
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from moviepy.editor import (
    VideoFileClip, ImageClip, AudioFileClip,
    concatenate_videoclips, CompositeVideoClip,
    ColorClip, VideoClip,
)
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from font_manager import get_font
from background_generator import generate_background
from media_fetcher import fetch_background
from tts_generator import text_to_speech
from script_generator import generate_script
from content_researcher import research_topic

if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS

logger = logging.getLogger(__name__)

# 9:16 vertical format for Shorts
SW, SH       = 1080, 1920
FPS          = 30
CHANNEL      = "@yeah_shh"
ACCENT       = (99, 102, 241)
WHITE        = (255, 255, 255)
TOKEN_FILE   = "token.json"
CLIENT_SECRETS = "client_secrets.json"
SCOPES       = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

# Shorts topic pool — different from main video categories
SHORTS_TOPICS = [
    ("Did You Know This About the Mahabharata?",        "mythology"),
    ("Virat Kohli's Secret Morning Routine",            "sports"),
    ("This AI Fact Will Blow Your Mind",                "educational"),
    ("The Hidden Meaning in Inception",                 "movie"),
    ("Why India's Moon Landing Made History",           "educational"),
    ("Hanuman's Power Nobody Talks About",              "mythology"),
    ("Messi vs Ronaldo — Who Really Won?",              "sports"),
    ("Your Phone is Changing Your Brain Right Now",     "educational"),
    ("The Real Villain of Mahabharata",                 "mythology"),
    ("How RRR Conquered the World",                     "movie"),
    ("Dhoni's Calm — The Science Behind It",            "sports"),
    ("Why Sleep is Your Superpower",                    "educational"),
    ("Karna's Curse — The Saddest Story Ever Told",     "mythology"),
    ("One Habit That Changed APJ Kalam's Life",         "story"),
    ("Why India's UPI Is Beating the World",            "educational"),
    ("The Dark Knight's Hidden Message",                "movie"),
    ("Neeraj Chopra's Journey Nobody Knows",            "sports"),
    ("What Happens to Your Body When You Meditate",     "educational"),
    ("The Real Power of the Gayatri Mantra",            "mythology"),
    ("How Pushpa Became a Global Icon",                 "movie"),
    ("Roger Federer's Last Match — A Legend Bows Out",  "sports"),
    ("Why Stress is Slowly Killing You",                "educational"),
    ("Ravana Was Actually a Genius",                    "mythology"),
    ("How Baahubali Changed Indian Cinema Forever",     "movie"),
    ("The Stock Market Secret Nobody Tells You",        "educational"),
    ("Sachin Tendulkar's Desert Storm — 1998",          "sports"),
    ("The Butterfly Effect — One Moment Changes Everything", "educational"),
    ("Why the Taj Mahal Is More Than a Love Story",     "story"),
]


# ── Entry point ───────────────────────────────────────────────────────────────

def run_shorts_pipeline(run_dir: str):
    os.makedirs(run_dir, exist_ok=True)

    # Pick today's Short topic (different rotation from main video)
    from datetime import datetime
    day  = datetime.now().timetuple().tm_yday
    idx  = (day + 13) % len(SHORTS_TOPICS)   # offset so it never matches main video day
    topic, mode = SHORTS_TOPICS[idx]

    logger.info(f"Creating Short: [{mode}] {topic}")

    # Generate 3-slide script (hook + insight + CTA)
    research = research_topic(topic)
    script   = _generate_short_script(topic, mode, research)

    # Background — try Pexels video, else generated
    bg = fetch_background(topic, run_dir)

    # TTS for each slide
    audio_paths = []
    for i, slide in enumerate(script["slides"]):
        path = os.path.join(run_dir, f"slide_{i}.mp3")
        text_to_speech(slide, path)
        audio_paths.append(path)

    # Build 9:16 Short video
    short_path = os.path.join(run_dir, "short.mp4")
    _build_short(script, audio_paths, bg, short_path)

    # Upload
    creds   = _get_credentials()
    youtube = build("youtube", "v3", credentials=creds)
    url     = _upload(youtube, short_path, script["title"], script["description"], script["tags"])

    logger.info(f"Short uploaded: {url}")
    return url


# ── Short script generator ────────────────────────────────────────────────────

def _generate_short_script(topic: str, mode: str, research: dict) -> dict:
    """3-slide punchy script for a 45-second Short."""
    from groq import Groq
    import os as _os
    client = Groq(api_key=_os.getenv("GROQ_API_KEY"))

    research_block = research.get("research_text", "")[:600] if research else ""

    prompt = f"""Write a 3-slide YouTube Shorts script about: "{topic}"
Mode: {mode}

{research_block}

Shorts are vertical 9:16 videos watched on mobile. Each slide is read aloud in ~12-15 seconds.
Be PUNCHY, VISUAL, and HOOK-DRIVEN. Every word must earn its place.

STRUCTURE:
- SLIDE_1: The most shocking/curious hook possible. 1-2 short punchy sentences. Make them stop scrolling.
- SLIDE_2: The single most surprising fact or insight. 1-2 sentences. Make them feel smarter.
- SLIDE_3: Payoff + CTA. End with "Follow {CHANNEL} for more." 2 sentences max.

OUTPUT FORMAT (no markdown, exactly this):
TITLE: <punchy Shorts title under 50 chars with #Shorts>
DESCRIPTION: <2 sentences + #Shorts #yeah_shh and 3 more relevant hashtags>
TAGS: shorts, yeah_shh, viral, <5 more relevant tags comma-separated>
SLIDE_1: <hook>
SLIDE_2: <insight>
SLIDE_3: <payoff + CTA>"""

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You write viral YouTube Shorts scripts. Every word counts. You write for mobile viewers with a 2-second attention span."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.9,
            max_tokens=400,
        )
        raw = resp.choices[0].message.content
        return _parse(raw, topic)
    except Exception as e:
        logger.warning(f"Groq failed for Short: {e}")
        return {
            "title": f"{topic} #Shorts",
            "description": f"{topic} #Shorts #yeah_shh #viral",
            "tags": ["shorts", "yeah_shh", "viral"],
            "slides": [
                f"You won't believe this about {topic}.",
                "Here's the one thing nobody tells you.",
                f"Follow {CHANNEL} for more daily facts.",
            ],
        }


def _parse(raw: str, topic: str) -> dict:
    result = {"title": f"{topic} #Shorts", "description": "", "tags": [], "slides": []}
    for line in raw.strip().splitlines():
        line = line.strip()
        if line.startswith("TITLE:"):
            result["title"] = line[6:].strip()
        elif line.startswith("DESCRIPTION:"):
            result["description"] = line[12:].strip()
        elif line.startswith("TAGS:"):
            result["tags"] = [t.strip() for t in line[5:].split(",")]
        elif line.startswith("SLIDE_"):
            result["slides"].append(line[line.index(":")+1:].strip())
    if not result["slides"]:
        result["slides"] = [f"Amazing fact about {topic}.", "Here's what you missed.", f"Follow {CHANNEL}!"]
    return result


# ── Short video builder ───────────────────────────────────────────────────────

def _build_short(script: dict, audio_paths: list, bg: dict, output_path: str):
    """Builds a cinematic 9:16 vertical Short."""
    clips = []
    total = len(script["slides"])

    for i, (text, audio_path) in enumerate(zip(script["slides"], audio_paths)):
        audio    = AudioFileClip(audio_path)
        duration = audio.duration + 0.3

        def make_frame(t, _text=text, _i=i, _dur=duration):
            return _short_frame(_text, t, _dur, _i, total, bg)

        clip = VideoClip(make_frame, duration=duration).set_fps(FPS).set_audio(audio)
        clips.append(clip)

    # Simple concat with crossfade
    TD = 0.25
    final = clips[0].crossfadeout(TD)
    for c in clips[1:]:
        c2 = c.crossfadein(TD)
        final = concatenate_videoclips([final, c2], padding=-TD, method="compose")

    final.write_videofile(output_path, fps=FPS, codec="libx264",
                          audio_codec="aac", logger=None, threads=2)
    logger.info(f"Short saved: {output_path}")


def _short_frame(text: str, t: float, duration: float, slide_idx: int, total: int, bg: dict) -> np.ndarray:
    """Render one frame of the Short at time t."""
    # Background
    if bg["type"] == "video":
        clip = VideoFileClip(bg["path"]).without_audio()
        raw  = clip.get_frame(t % clip.duration)
        base = Image.fromarray(raw.astype("uint8")).resize((SW, SH), Image.LANCZOS)
    else:
        base = Image.open(bg["path"]).convert("RGB").resize((SW, SH), Image.LANCZOS)

    # Blur + darken background for readability
    base = base.filter(ImageFilter.GaussianBlur(radius=3))
    dark = Image.new("RGBA", (SW, SH), (0, 0, 0, 130))
    base = Image.alpha_composite(base.convert("RGBA"), dark).convert("RGB")

    draw  = ImageDraw.Draw(base)
    alpha = min(1.0, t / 0.4)
    offset = int(25 * (1 - alpha))

    # ── Top branding ──
    top_grad = Image.new("RGBA", (SW, 200), (0,0,0,0))
    tg = ImageDraw.Draw(top_grad)
    for y in range(200):
        tg.line([(0,y),(SW,y)], fill=(0,0,0, int(160*(1-y/200))))
    base = Image.alpha_composite(base.convert("RGBA"), top_grad).convert("RGB")
    draw = ImageDraw.Draw(base)

    ch_font = get_font(52, "bold")
    cb = draw.textbbox((0,0), CHANNEL, font=ch_font)
    cx = (SW - (cb[2]-cb[0])) // 2
    draw.text((cx+2, 44), CHANNEL, font=ch_font, fill=(0,0,0))
    draw.text((cx,   42), CHANNEL, font=ch_font, fill=(*ACCENT, int(255*alpha)))

    # ── Progress bar ──
    draw.rectangle([0, SH-8, SW, SH], fill=(30,30,50))
    prog = (slide_idx + min(1.0, t/duration)) / total
    draw.rectangle([0, SH-8, int(SW*prog), SH], fill=ACCENT)

    # ── Main text — centred ──
    font  = get_font(62, "bold")
    lines = _wrap_short(text, 22)
    lh    = 80
    y0    = (SH - len(lines)*lh) // 2 + offset
    for i, line in enumerate(lines):
        lb = draw.textbbox((0,0), line, font=font)
        x  = (SW - (lb[2]-lb[0])) // 2
        y  = y0 + i*lh
        draw.text((x+3, y+3), line, font=font, fill=(0,0,0,int(200*alpha)))
        draw.text((x,   y  ), line, font=font, fill=(*WHITE, int(255*alpha)))

    # ── Bottom CTA strip ──
    bot = Image.new("RGBA", (SW, 180), (0,0,0,0))
    bd  = ImageDraw.Draw(bot)
    for y in range(180):
        bd.line([(0,y),(SW,y)], fill=(0,0,0, int(170*(y/180))))
    base = Image.alpha_composite(base.convert("RGBA"), bot).convert("RGB")
    draw = ImageDraw.Draw(base)

    sub_font = get_font(44, "bold")
    sub_text = "Subscribe  🔔"
    sb = draw.textbbox((0,0), sub_text, font=sub_font)
    sx = (SW - (sb[2]-sb[0])) // 2
    draw.text((sx, SH-140), sub_text, font=sub_font, fill=(255, 220, 0))

    return np.array(base)


def _wrap_short(text: str, max_chars: int = 22) -> list:
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


# ── YouTube upload ────────────────────────────────────────────────────────────

def _upload(youtube, path: str, title: str, description: str, tags: list) -> str:
    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": "22",
        },
        "status": {"privacyStatus": "public"},
    }
    media = MediaFileUpload(path, chunksize=-1, resumable=True, mimetype="video/mp4")
    req   = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    resp  = None
    while resp is None:
        _, resp = req.next_chunk()
    return f"https://www.youtube.com/watch?v={resp['id']}"


def _get_credentials() -> Credentials:
    from google_auth_oauthlib.flow import InstalledAppFlow
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow  = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=8080)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return creds
