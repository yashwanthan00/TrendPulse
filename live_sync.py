"""Daily live-stream polish for the GTA 6 PS5 walkthrough channel.

For every finished GTA 6 stream that has not been processed yet it:
  1. rewrites the title / description / tags,
  2. adds the video to the end of the walkthrough playlist,
  3. builds and uploads a custom thumbnail.

Each step is tracked per video in live_sync_state.json so a quota error or a
missing preview frame is simply retried on the next run.

Usage:  python live_sync.py [--dry-run] [--max N]
Auth:   YOUTUBE_LIVE_TOKEN env var (contents of an authorized-user token.json
        with the full "youtube" scope), or a token.json file next to this script.
"""

import argparse
import io
import json
import logging
import os
import re
import sys
import textwrap
from datetime import datetime, timezone

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageStat

log = logging.getLogger("live_sync")

SCOPES = ["https://www.googleapis.com/auth/youtube"]
PLAYLIST_ID = os.getenv("GTA_PLAYLIST_ID", "PLRMj66ZlCZZU")
STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live_sync_state.json")

TAGS = ["GTA 6", "GTA VI", "GTA 6 gameplay", "GTA 6 PS5", "GTA 6 walkthrough", "Grand Theft Auto 6",
        "Grand Theft Auto VI", "Vice City", "Lucia", "PS5 gameplay", "GTA 6 story mode", "GTA 6 missions"]

CLEAN_PREFIX = "GTA 6 Walkthrough - "
MARKER = "GTA 6 PS5 gameplay:"  # first words of every description we write
# "GTA 6 - Chapter 2 | Slam Dunk", "GTA 6 | Chapter 1 | Island Dreams", "GTA 6 - Chapter 3 |Mission"
TITLE_RE = re.compile(r"^\s*GTA\s*6\s*[-|:–]\s*Chapter\s*(\d+)\s*[-|:–]\s*(.+?)\s*$", re.I)
ACCENTS = {0: (255, 61, 154), 1: (255, 204, 0), 2: (0, 214, 255), 3: (160, 255, 60)}
FONT_CANDIDATES = [
    "fonts/thumb.ttf",
    "/System/Library/Fonts/Supplemental/Impact.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


class QuotaExceeded(Exception):
    pass


# --------------------------------------------------------------------------- pure helpers
def parse_title(title):
    """Return (chapter:int, mission:str) for a raw stream title, else None."""
    m = TITLE_RE.match(title or "")
    if not m:
        return None
    mission = re.sub(r"\s+", " ", m.group(2)).strip(" |-")
    return int(m.group(1)), mission


def is_clean(title):
    return (title or "").startswith(CLEAN_PREFIX)


def build_title(chapter, mission):
    return f"{CLEAN_PREFIX}Chapter {chapter}: {mission} | PS5 Gameplay"[:100]


def duration_minutes(iso):
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    h, mi, s = (int(x or 0) for x in m.groups())
    return h * 60 + mi + (1 if s >= 30 else 0)


def build_description(chapter, mission, minutes, existing=""):
    length = f" ({minutes} min)" if minutes else ""
    block = f"""{MARKER} Chapter {chapter} - "{mission}"{length}.

Full story-mode playthrough of Grand Theft Auto VI on PlayStation 5, recorded mission by mission. Watch the whole mission start to finish, or use this as a reference if you're stuck on "{mission}".

New GTA 6 PS5 gameplay is uploaded every day. Subscribe so you don't miss the next mission, and drop a comment if you want a particular mission or tip covered.

Playlist - GTA 6 Full Walkthrough (PS5): https://www.youtube.com/playlist?list={PLAYLIST_ID}

#GTA6 #GTAVI #GTA6Gameplay #PS5 #ViceCity #GTA6Walkthrough
"""
    existing = (existing or "").strip()
    if existing and MARKER not in existing:
        block += f"\n---\n{existing}\n"  # never throw away text the owner wrote
    return block


def frame_ok(img):
    """Reject black / near-uniform frames (loading screens, pause menus, fades)."""
    g = img.convert("L").resize((160, 90))
    st = ImageStat.Stat(g)
    return st.mean[0] > 18 and st.stddev[0] > 20


def strip_letterbox(img):
    g = img.convert("L")
    w, h = g.size
    rows = [y for y in range(h) if g.crop((0, y, w, y + 1)).getextrema()[1] > 12]
    if not rows or (rows[-1] - rows[0]) > h * 0.97:
        return img
    return img.crop((0, rows[0], w, rows[-1] + 1))


def load_font(size):
    here = os.path.dirname(os.path.abspath(__file__))
    for p in FONT_CANDIDATES:
        p = p if os.path.isabs(p) else os.path.join(here, p)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def render_thumbnail(frame, chapter, mission):
    """1280x720 thumbnail: mission name, GTA 6 tag, chapter ribbon. Only states true facts."""
    im = strip_letterbox(frame.convert("RGB")).resize((1280, 720), Image.LANCZOS)
    im = ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(1.25)).enhance(1.1)
    if ImageStat.Stat(im.convert("L")).mean[0] < 70:  # lift dark night-time footage
        im = im.point([int(255 * ((i / 255) ** 0.65)) for i in range(256)] * 3)
    ramp = Image.new("L", (1, 720))
    for y in range(720):
        ramp.putpixel((0, y), int(max(0, (y - 280) / 440) ** 1.4 * 235))
    im = Image.composite(Image.new("RGB", (1280, 720), (0, 0, 0)), im, ramp.resize((1280, 720)))
    d = ImageDraw.Draw(im)
    acc = ACCENTS.get(chapter, ACCENTS[1])
    name = mission.upper()

    size = 150
    while size > 70:
        lines = textwrap.wrap(name, width=max(8, int(1180 / (size * 0.50))))
        f = load_font(size)
        if len(lines) <= 2 and max(d.textlength(l, font=f) for l in lines) <= 1180:
            break
        size -= 6
    lines = textwrap.wrap(name, width=max(8, int(1180 / (size * 0.50))))
    f = load_font(size)
    top = 600 - len(lines) * (size + 4)
    y = top
    for line in lines:
        for dx in range(-6, 7, 2):
            for dy in range(-6, 7, 2):
                d.text((50 + dx, y + dy), line, font=f, fill=(0, 0, 0))
        d.text((50, y), line, font=f, fill=(255, 255, 255))
        y += size + 4
    d.rounded_rectangle((50, top - 88, 300, top - 8), 14, fill=acc)
    d.text((72, top - 88), "GTA 6", font=load_font(72), fill=(15, 15, 15))
    d.rectangle((0, 640, 1280, 720), fill=acc)
    d.text((50, 650), f"CHAPTER {chapter}  |  FULL MISSION  |  PS5 GAMEPLAY", font=load_font(50), fill=(15, 15, 15))
    return im


def fetch_frame(video_id):
    """Best usable preview frame, or None if YouTube has not generated one yet."""
    for name in ("maxresdefault", "sd1", "sd2", "sd3", "hq720", "hqdefault"):
        r = requests.get(f"https://i.ytimg.com/vi/{video_id}/{name}.jpg", timeout=20,
                         headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200 or len(r.content) < 5000:
            continue
        img = strip_letterbox(Image.open(io.BytesIO(r.content)).convert("RGB"))
        if img.width >= 600 and frame_ok(img):
            return img
    return None


# --------------------------------------------------------------------------- state
def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {"videos": {}}


def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


# --------------------------------------------------------------------------- YouTube
def get_service():
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    raw = os.getenv("YOUTUBE_LIVE_TOKEN")
    if raw:
        creds = Credentials.from_authorized_user_info(json.loads(raw), SCOPES)
    elif os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    else:
        sys.exit("No credentials: set YOUTUBE_LIVE_TOKEN or provide token.json")
    if not creds.valid:
        try:
            creds.refresh(Request())
        except RefreshError as e:
            sys.exit(f"YouTube token refresh failed ({e}). Re-run the one-time auth and update the "
                     "YOUTUBE_LIVE_TOKEN secret. If this repeats weekly, publish the OAuth consent "
                     "screen (Testing-mode refresh tokens expire after 7 days).")
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def call(req):
    from googleapiclient.errors import HttpError
    try:
        return req.execute()
    except HttpError as e:
        if e.resp.status == 403 and b"quotaExceeded" in e.content:
            raise QuotaExceeded() from e
        raise


def recent_uploads(yt, limit=50):
    ch = call(yt.channels().list(part="contentDetails", mine=True))["items"][0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids = [i["contentDetails"]["videoId"] for i in
           call(yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=limit))["items"]]
    out = []
    for i in range(0, len(ids), 50):
        out += call(yt.videos().list(part="snippet,contentDetails,status,liveStreamingDetails",
                                     id=",".join(ids[i:i + 50])))["items"]
    return out


def playlist_video_ids(yt):
    ids, tok = [], None
    while True:
        r = call(yt.playlistItems().list(part="contentDetails", playlistId=PLAYLIST_ID,
                                         maxResults=50, pageToken=tok))
        ids += [i["contentDetails"]["videoId"] for i in r["items"]]
        tok = r.get("nextPageToken")
        if not tok:
            return ids


def start_key(v):
    d = v.get("liveStreamingDetails", {})
    return d.get("actualStartTime") or v["snippet"]["publishedAt"]


def pick_work(videos, state):
    """Videos needing work: new finished GTA 6 streams, plus ones with an unfinished step."""
    work = []
    for v in videos:
        vid, sn = v["id"], v["snippet"]
        entry = state["videos"].get(vid)
        if entry:
            if not all(entry["steps"].values()):
                work.append((v, entry["chapter"], entry["mission"]))
            continue
        if is_clean(sn["title"]):
            continue  # polished by hand / earlier tooling
        if sn.get("liveBroadcastContent") in ("live", "upcoming"):
            continue
        if v["status"].get("privacyStatus") == "private":
            continue
        parsed = parse_title(sn["title"])
        if not parsed:
            if re.search(r"gta\s*6", sn["title"], re.I):
                log.warning("Skipping %s: title %r does not look like 'GTA 6 - Chapter N | Mission'", vid, sn["title"])
            continue
        work.append((v, *parsed))
    work.sort(key=lambda w: start_key(w[0]))
    return work


def process(yt, v, chapter, mission, state, dry_run):
    vid = v["id"]
    entry = state["videos"].setdefault(vid, {"chapter": chapter, "mission": mission,
                                             "steps": {"metadata": False, "playlist": False, "thumbnail": False}})
    steps = entry["steps"]
    log.info("%s -> Chapter %s: %s  (todo: %s)", vid, chapter, mission, [k for k, ok in steps.items() if not ok])

    if not steps["metadata"]:
        sn = v["snippet"]
        new = dict(sn, title=build_title(chapter, mission), tags=TAGS,
                   description=build_description(chapter, mission, duration_minutes(v["contentDetails"]["duration"]),
                                                 sn.get("description")))
        if not dry_run:
            call(yt.videos().update(part="snippet", body={"id": vid, "snippet": new}))
        steps["metadata"] = True

    if not steps["playlist"]:
        if not dry_run:
            present = playlist_video_ids(yt)
            if vid not in present:
                call(yt.playlistItems().insert(part="snippet", body={"snippet": {
                    "playlistId": PLAYLIST_ID, "position": len(present),
                    "resourceId": {"kind": "youtube#video", "videoId": vid}}}))
        steps["playlist"] = True

    if not steps["thumbnail"]:
        frame = fetch_frame(vid)
        if frame is None:
            log.warning("%s: no usable preview frame yet; thumbnail retried next run", vid)
        else:
            im = render_thumbnail(frame, chapter, mission)
            if not dry_run:
                from googleapiclient.http import MediaIoBaseUpload
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=92)
                buf.seek(0)
                call(yt.thumbnails().set(videoId=vid, media_body=MediaIoBaseUpload(buf, "image/jpeg")))
            else:
                os.makedirs("dry_run_thumbs", exist_ok=True)
                im.save(f"dry_run_thumbs/{vid}.jpg", quality=92)
            steps["thumbnail"] = True

    entry["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="plan only: no YouTube writes, no state changes")
    ap.add_argument("--max", type=int, default=15, help="max videos per run (quota safety)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    yt = get_service()
    state = load_state()
    try:
        work = pick_work(recent_uploads(yt), state)[:args.max]
        log.info("%d video(s) to process%s", len(work), " (dry run)" if args.dry_run else "")
        for v, chapter, mission in work:
            process(yt, v, chapter, mission, state, args.dry_run)
            if not args.dry_run:
                save_state(state)
    except QuotaExceeded:
        log.warning("YouTube API quota exhausted; unfinished steps resume on the next run")
    finally:
        if not args.dry_run:
            save_state(state)


if __name__ == "__main__":
    main()
