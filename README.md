# TrendPulse 🎬

Automated daily YouTube channel — fetches trending topics, generates a script, narrates it, builds a video, and uploads — all for free.

## Stack (100% Free)

| Step | Tool |
|---|---|
| Trending topic | pytrends (Google Trends) |
| Script | Gemini 1.5 Flash API (free tier) |
| Narration | edge-tts (Microsoft, no key needed) |
| Background image | Pexels API (free tier) |
| Video rendering | MoviePy + Pillow |
| Upload | YouTube Data API v3 |
| Scheduling | GitHub Actions (cron) |

## Setup

### 1. Get free API keys

- **Gemini**: https://aistudio.google.com/app/apikey
- **Pexels**: https://www.pexels.com/api/

### 2. Set up YouTube OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → enable **YouTube Data API v3**
3. Create OAuth 2.0 credentials → Desktop App
4. Download as `client_secrets.json` → place in project root
5. Run `python main.py` once locally to authorize (creates `token.json`)

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env`

```bash
cp .env.example .env
# fill in GEMINI_API_KEY and PEXELS_API_KEY
```

### 5. Run locally

```bash
python main.py
```

### 6. Set up GitHub Actions (daily automation)

1. Push this repo to GitHub
2. Go to **Settings → Secrets and variables → Actions**
3. Add these secrets:
   - `GEMINI_API_KEY`
   - `PEXELS_API_KEY`
   - `CLIENT_SECRETS` — paste contents of `client_secrets.json`
   - `YOUTUBE_TOKEN` — paste contents of `token.json` (after first local run)

GitHub Actions will run every day at 10:00 AM UTC automatically.

## Project Structure

```
TrendPulse/
├── main.py              # pipeline entrypoint
├── trend_fetcher.py     # Google Trends → trending topic
├── script_generator.py  # Gemini → video script
├── tts_generator.py     # edge-tts → MP3 narration
├── image_fetcher.py     # Pexels → background image
├── video_builder.py     # MoviePy → MP4 video
├── youtube_uploader.py  # YouTube API → upload
├── requirements.txt
├── .env.example
├── .github/workflows/daily_upload.yml
├── output/              # generated videos (gitignored)
└── logs/                # run logs (gitignored)
```
