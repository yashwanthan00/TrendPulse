"""Generates a YouTube video script.
Primary: Groq (free, 14,400 req/day, fast).
Fallback: Gemini (if GEMINI_API_KEY is set and working).
"""

import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


def generate_script(topic: str, mode: str = "trending", wikipedia_summary: str = None) -> dict:
    """Returns dict: title, description, tags, slides, mode."""
    prompt = _educational_prompt(topic, wikipedia_summary) if mode == "educational" else _trending_prompt(topic)

    # Try Groq first (free tier, very generous)
    if os.getenv("GROQ_API_KEY"):
        try:
            return _generate_with_groq(prompt, topic, mode)
        except Exception as e:
            logger.warning(f"Groq failed: {e} — trying Gemini")

    # Fallback to Gemini
    if os.getenv("GEMINI_API_KEY"):
        try:
            return _generate_with_gemini(prompt, topic, mode)
        except Exception as e:
            logger.warning(f"Gemini failed: {e} — using default script")

    logger.error("All AI providers failed — using default script")
    return _default_script(topic, mode)


# ── Providers ─────────────────────────────────────────────────────────────────

def _generate_with_groq(prompt: str, topic: str, mode: str) -> dict:
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",  # free, fast, high quality
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=800,
    )
    raw = response.choices[0].message.content
    logger.info("Script generated via Groq")
    return _parse_script(raw, topic, mode)


def _generate_with_gemini(prompt: str, topic: str, mode: str) -> dict:
    from google import genai
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    logger.info("Script generated via Gemini")
    return _parse_script(response.text, topic, mode)


# ── Prompts ───────────────────────────────────────────────────────────────────

def _trending_prompt(topic: str) -> str:
    return f"""You are a YouTube content creator making a 60-second trending news video about: "{topic}".

IMPORTANT RULES:
- Write 100% original content — do not quote or copy from any source verbatim
- Do not mention any copyrighted brand names as the main subject
- Keep language simple, engaging, and factual

Return ONLY this exact format (no markdown, no extra text):

TITLE: <catchy title under 60 chars>
DESCRIPTION: <2-3 sentence description with relevant hashtags>
TAGS: <comma-separated tags, max 10>
SLIDE_1: <attention-grabbing hook, 1-2 sentences>
SLIDE_2: <key background context, 1-2 sentences>
SLIDE_3: <interesting fact or detail, 1-2 sentences>
SLIDE_4: <why this matters to viewers, 1-2 sentences>
SLIDE_5: <call to action — like, subscribe, comment opinion>"""


def _educational_prompt(topic: str, wikipedia_summary: str = None) -> str:
    context = ""
    if wikipedia_summary:
        context = f"\nUse this as factual reference ONLY — do not copy verbatim:\n---\n{wikipedia_summary[:400]}\n---\n"
    return f"""You are an educational YouTube creator making a beginner-friendly 60-second explainer about: "{topic}".
{context}
IMPORTANT RULES:
- Write 100% original explanations in your own words
- Use simple analogies, no jargon
- Make it engaging for a general audience

Return ONLY this exact format (no markdown, no extra text):

TITLE: <clear educational title under 60 chars>
DESCRIPTION: <2-3 sentences with hashtags like #education #learnwithme>
TAGS: <comma-separated tags, max 10>
SLIDE_1: <hook — surprising fact or question>
SLIDE_2: <explain the core concept simply>
SLIDE_3: <real-world analogy or example>
SLIDE_4: <one surprising insight>
SLIDE_5: <recap + call to action>"""


# ── Parser & fallback ─────────────────────────────────────────────────────────

def _parse_script(raw: str, topic: str, mode: str) -> dict:
    label = "Educational:" if mode == "educational" else "Trending:"
    result = {
        "title": f"{label} {topic}",
        "description": f"Learn about {topic}. #trending #education",
        "tags": ["trending", "education", topic.lower()[:30]],
        "slides": [],
        "mode": mode,
    }
    for line in raw.strip().splitlines():
        line = line.strip()
        if line.startswith("TITLE:"):
            result["title"] = line[6:].strip()
        elif line.startswith("DESCRIPTION:"):
            result["description"] = line[12:].strip()
        elif line.startswith("TAGS:"):
            result["tags"] = [t.strip() for t in line[5:].split(",")]
        elif line.startswith("SLIDE_"):
            colon = line.index(":")
            result["slides"].append(line[colon + 1:].strip())

    if not result["slides"]:
        result["slides"] = _default_script(topic, mode)["slides"]

    logger.info(f"Script ready [{mode}]: {result['title']}")
    return result


def _default_script(topic: str, mode: str) -> dict:
    return {
        "title": f"{'Learn About' if mode == 'educational' else 'Trending:'} {topic}",
        "description": f"Today's video covers: {topic}. #trending #education #viral",
        "tags": ["trending", "education", "viral"],
        "slides": [
            f"Today's topic: {topic}",
            "Let's break it down simply.",
            "Here's what you need to know.",
            "This is why it matters to you.",
            "Like and subscribe for daily content!",
        ],
        "mode": mode,
    }
