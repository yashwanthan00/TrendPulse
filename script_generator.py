"""Generates a YouTube video script using Gemini API.
Supports two modes: 'trending' (news-style) and 'educational' (explainer-style).
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def generate_script(topic: str, mode: str = "trending", wikipedia_summary: str = None) -> dict:
    """
    Returns dict: title, description, tags, slides (list of strings).
    mode: 'trending' | 'educational'
    """
    model = genai.GenerativeModel("gemini-1.5-flash")

    if mode == "educational":
        prompt = _educational_prompt(topic, wikipedia_summary)
    else:
        prompt = _trending_prompt(topic)

    response = model.generate_content(prompt)
    return _parse_script(response.text, topic, mode)


# ── Prompts ───────────────────────────────────────────────────────────────────

def _trending_prompt(topic: str) -> str:
    return f"""
You are a YouTube content creator making a 60-second trending news video about: "{topic}".

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
SLIDE_5: <call to action — like, subscribe, comment opinion>
"""


def _educational_prompt(topic: str, wikipedia_summary: str = None) -> str:
    context = ""
    if wikipedia_summary:
        context = f"""
Use this factual reference as inspiration ONLY — do not copy it verbatim:
---
{wikipedia_summary}
---
"""
    return f"""
You are an educational YouTube creator making a clear, beginner-friendly 60-second explainer about: "{topic}".

{context}
IMPORTANT RULES:
- Write 100% original explanations — rephrase all facts in your own words
- Use simple analogies to explain complex ideas
- Do not quote copyrighted textbooks or courses verbatim
- Make it engaging for a general audience

Return ONLY this exact format (no markdown, no extra text):

TITLE: <clear educational title, under 60 chars, e.g. "How X Works Explained in 60 Seconds">
DESCRIPTION: <2-3 sentences explaining what viewers will learn, with hashtags like #education #learnwithme>
TAGS: <comma-separated tags, max 10>
SLIDE_1: <hook — surprising fact or question to grab attention>
SLIDE_2: <explain the core concept in simple terms>
SLIDE_3: <give a real-world analogy or example>
SLIDE_4: <one surprising or advanced insight>
SLIDE_5: <recap + call to action — like for more explainers, subscribe>
"""


# ── Parser ────────────────────────────────────────────────────────────────────

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
        result["slides"] = [
            f"Today we explore: {topic}",
            "Let's break it down simply.",
            "Here's what you need to know.",
            "This matters more than you think.",
            "Like and subscribe for daily content!",
        ]

    logger.info(f"Script generated [{mode}]: {result['title']}")
    return result
