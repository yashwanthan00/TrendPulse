"""
Daily YouTube Shorts generator.
Picks a random video from @yeah_shh channel, clips 55s, reformats to 9:16,
adds channel branding, and uploads as a YouTube Short.
"""

import os
import json
import random
import logging
import numpy as np
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFilter

# MoviePy 1.0.3 uses ANTIALIAS which was removed in Pillow 10+
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS
from moviepy.editor import (
    VideoFileClip, CompositeVideoClip, ImageClip,
    VideoClip, ColorClip, AudioFileClip,
    concatenate_videoclips,
)
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from font_manager import get_font

logger = logging.getLogger(__name__)

CHANNEL_HANDLE   = "@yeah_shh"
SHORT_W, SHORT_H = 1080, 1920
SHORT_DURATION   = 55        # seconds
FPS              = 30
TOKEN_FILE       = "token.json"
CLIENT_SECRETS   = "client_secrets.json"
SCOPES           = ["https://www.googleapis.com/auth/youtube.upload",
                    "https://www.googleapis.com/auth/youtube.readonly"]
USED_FILE        = "docs/shorts_used.json"


# ── Entry point ───────────────────────────────────────────────────────────────

def run_shorts_pipeline(run_dir: str) -> str | None:
    """Pick a video, make a Short, upload. Returns YouTube URL or None on failure."""
    os.makedirs(run_dir, exist_ok=True)

    creds   = _get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    # Pick a random unused video
    video = _pick_random_video(youtube)
    if not video:
        logger.warning("No unused videos found for Shorts — resetting history")
        _reset_used()
        video = _pick_random_video(youtube)

    if not video:
        logger.error("Could not find any videos on the channel")
        return None

    video_id    = video["id"]
    video_title = video["title"]
    logger.info(f"Creating Short from: {video_title} ({video_id})")

    # Download
    raw_path = os.path.join(run_dir, "raw.mp4")
    if not _download_video(video_id, raw_path):
        return None

    # Create Short
    short_path = os.path.join(run_dir, "short.mp4")
    _create_short(raw_path, short_path, video_title)

    # Upload
    url = _upload_short(youtube, short_path, video_title, video_id)

    # Mark as used
    _mark_used(video_id)

    logger.info(f"Short uploaded: {url}")
    return url


# ── Video picker ──────────────────────────────────────────────────────────────

def _pick_random_video(youtube) -> dict | None:
    used = _load_used()

    # Get uploads playlist
    ch = youtube.channels().list(mine=True, part="contentDetails,snippet").execute()
    items = ch.get("items", [])
    if not items:
        return None

    playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Fetch up to 50 videos
    videos, token = [], None
    while True:
        req = youtube.playlistItems().list(
            playlistId=playlist_id,
            part="snippet",
            maxResults=50,
            pageToken=token,
        )
        resp = req.execute()
        for item in resp.get("items", []):
            vid_id = item["snippet"]["resourceId"]["videoId"]
            title  = item["snippet"]["title"]
            if vid_id not in used:
                videos.append({"id": vid_id, "title": title})
        token = resp.get("nextPageToken")
        if not token:
            break

    if not videos:
        return None
    return random.choice(videos)


# ── Downloader ────────────────────────────────────────────────────────────────

COOKIES_FILE = "yt_cookies.txt"


def _download_video(video_id: str, output_path: str) -> bool:
    try:
        import yt_dlp

        ydl_opts = {
            "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "outtmpl": output_path,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
            "extractor_args": {"youtube": {"skip": ["hls", "dash"]}},
        }

        # Use cookies if available (prevents bot detection in CI)
        if os.path.exists(COOKIES_FILE):
            ydl_opts["cookiefile"] = COOKIES_FILE
            logger.info("Using YouTube cookies for download")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
        return os.path.exists(output_path)
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return False


# ── Short creator ─────────────────────────────────────────────────────────────

def _create_short(input_path: str, output_path: str, title: str):
    clip = VideoFileClip(input_path)

    # Pick best 55s window: skip first 15% and last 10%
    start = max(0, clip.duration * 0.15)
    end   = clip.duration * 0.90
    available = end - start
    if available <= SHORT_DURATION:
        start = max(0, clip.duration - SHORT_DURATION)
    else:
        # Random start within the good zone
        start = start + random.uniform(0, available - SHORT_DURATION)

    clip = clip.subclip(start, min(start + SHORT_DURATION, clip.duration))

    # ── Build 9:16 frame ──────────────────────────────────────────────────────

    # Blurred background (fill full 9:16)
    bg_scale = max(SHORT_W / clip.w, SHORT_H / clip.h)
    bg_base  = clip.resize(bg_scale)
    bg_base  = bg_base.crop(
        x_center=bg_base.w / 2,
        y_center=bg_base.h / 2,
        width=SHORT_W,
        height=SHORT_H,
    )

    def blur_frame(f):
        return np.array(Image.fromarray(f).filter(ImageFilter.GaussianBlur(radius=18)))

    bg = bg_base.fl_image(blur_frame)

    # Main video — scale to fit width
    vid_scale = SHORT_W / clip.w
    vid       = clip.resize(vid_scale)
    vid_y     = (SHORT_H - vid.h) // 2
    vid       = vid.set_position(("center", vid_y))

    # Branding overlays
    top_bar    = _top_branding(clip.duration)
    bottom_bar = _bottom_branding(clip.duration)

    final = CompositeVideoClip(
        [bg, vid, top_bar, bottom_bar],
        size=(SHORT_W, SHORT_H),
    ).set_audio(clip.audio)

    final.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        logger=None,
        threads=2,
    )
    clip.close()


def _top_branding(duration: float) -> ImageClip:
    """Channel name banner at the top."""
    img    = Image.new("RGBA", (SHORT_W, 160), (0, 0, 0, 0))
    draw   = ImageDraw.Draw(img)
    font   = get_font(52, "bold")
    handle = CHANNEL_HANDLE

    # Gradient bar
    for y in range(140):
        a = int(180 * (1 - y / 140))
        draw.line([(0, y), (SHORT_W, y)], fill=(0, 0, 0, a))

    bbox = draw.textbbox((0, 0), handle, font=font)
    tw   = bbox[2] - bbox[0]
    draw.text(((SHORT_W - tw) // 2 + 2, 22), handle, font=font, fill=(0, 0, 0, 220))
    draw.text(((SHORT_W - tw) // 2, 20), handle, font=font, fill=(255, 255, 255, 255))

    return ImageClip(np.array(img.convert("RGB"))).set_duration(duration).set_position((0, 0)).fadein(0.3)


def _bottom_branding(duration: float) -> ImageClip:
    """Subscribe CTA at the bottom."""
    img  = Image.new("RGBA", (SHORT_W, 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = get_font(46, "bold")
    sub  = get_font(34, "regular")

    # Gradient bar (bottom)
    for y in range(200):
        a = int(190 * (y / 200))
        draw.line([(0, y), (SHORT_W, y)], fill=(0, 0, 0, a))

    # Subscribe text
    label = "Subscribe for more  🔔"
    bbox  = draw.textbbox((0, 0), label, font=sub)
    tw    = bbox[2] - bbox[0]
    draw.text(((SHORT_W - tw) // 2, 110), label, font=sub, fill=(255, 220, 0, 255))

    # Channel handle
    bbox2 = draw.textbbox((0, 0), CHANNEL_HANDLE, font=font)
    tw2   = bbox2[2] - bbox2[0]
    draw.text(((SHORT_W - tw2) // 2, 150), CHANNEL_HANDLE, font=font, fill=(255, 255, 255, 200))

    arr   = np.array(img.convert("RGB"))
    return (ImageClip(arr)
            .set_duration(duration)
            .set_position((0, SHORT_H - 200))
            .fadein(0.3))


# ── Uploader ──────────────────────────────────────────────────────────────────

def _upload_short(youtube, short_path: str, original_title: str, original_id: str) -> str:
    short_title = f"{original_title[:45]} #Shorts"
    description = (
        f"Check out the full video on {CHANNEL_HANDLE}!\n\n"
        f"Watch full video: https://youtube.com/watch?v={original_id}\n\n"
        f"Subscribe to {CHANNEL_HANDLE} for daily content!\n\n"
        f"#Shorts #YouTube #{CHANNEL_HANDLE.replace('@', '')}"
    )
    body = {
        "snippet": {
            "title": short_title,
            "description": description,
            "tags": ["shorts", "yeah_shh", "viral", "youtube"],
            "categoryId": "22",
        },
        "status": {"privacyStatus": "public"},
    }
    media   = MediaFileUpload(short_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        _, response = request.next_chunk()

    return f"https://www.youtube.com/watch?v={response['id']}"


# ── Credentials ───────────────────────────────────────────────────────────────

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


# ── Used-video tracker ────────────────────────────────────────────────────────

def _load_used() -> set:
    if os.path.exists(USED_FILE):
        with open(USED_FILE) as f:
            return set(json.load(f))
    return set()


def _mark_used(video_id: str):
    used = _load_used()
    used.add(video_id)
    os.makedirs("docs", exist_ok=True)
    with open(USED_FILE, "w") as f:
        json.dump(list(used), f)


def _reset_used():
    os.makedirs("docs", exist_ok=True)
    with open(USED_FILE, "w") as f:
        json.dump([], f)
