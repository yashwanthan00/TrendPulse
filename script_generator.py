"""
Generates professional YouTube video scripts using Groq (Llama 3.3 70B).
Scripts follow a proven narrative arc: Hook → Context → Insight → Twist → CTA.
Primary: Groq. Fallback: Gemini.
"""

import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


def generate_script(topic: str, mode: str = "trending", wikipedia_summary: str = None) -> dict:
    """Returns dict: title, description, tags, slides, mode."""
    prompt = _educational_prompt(topic, wikipedia_summary) if mode == "educational" else _trending_prompt(topic)

    if os.getenv("GROQ_API_KEY"):
        try:
            return _generate_with_groq(prompt, topic, mode)
        except Exception as e:
            logger.warning(f"Groq failed: {e} — trying Gemini")

    if os.getenv("GEMINI_API_KEY"):
        try:
            return _generate_with_gemini(prompt, topic, mode)
        except Exception as e:
            logger.warning(f"Gemini failed: {e} — using default script")

    return _default_script(topic, mode)


# ── Providers ─────────────────────────────────────────────────────────────────

def _generate_with_groq(prompt: str, topic: str, mode: str) -> dict:
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a world-class YouTube scriptwriter who has written for channels "
                    "with 10M+ subscribers. You write scripts that hook viewers in the first 3 seconds, "
                    "build tension and curiosity, deliver satisfying payoffs, and always leave viewers "
                    "wanting more. Your writing is conversational, punchy, and emotionally resonant. "
                    "You never use filler words. Every sentence earns its place."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.85,
        max_tokens=1000,
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
    return f"""Write a PROFESSIONAL, high-retention YouTube script about the trending topic: "{topic}".

NARRATIVE STRUCTURE — follow this exact arc:
- SLIDE_1 (THE HOOK): Start with a shocking stat, bold claim, or provocative question that makes it IMPOSSIBLE to scroll past. Use "You", "Here's why", "Nobody talks about". Max 2 sentences. Must create immediate curiosity gap.
- SLIDE_2 (THE CONTEXT): Explain WHY this is happening right now. Give 1 specific fact, number, or date. Make it feel urgent. 2 sentences.
- SLIDE_3 (THE INSIGHT): The surprising truth most people don't know. Flip expectations. Use contrast: "While everyone thinks X... the reality is Y." 2 sentences.
- SLIDE_4 (THE STAKES): Why does this matter to the viewer personally? Connect to their life, money, career, or future. Be specific. 2 sentences.
- SLIDE_5 (THE CTA): End with curiosity + action. Ask a polarizing question to drive comments. Then: "Follow @yeah_shh for daily insights you won't find anywhere else." 2 sentences.

WRITING RULES:
- Write in active voice only
- Use power words: shocking, secret, revealed, exposed, breaking, urgent
- No corporate speak, no filler, no "in conclusion"
- Sound like a smart friend texting you urgent news
- 100% original — no verbatim quotes from any source
- Each slide should feel like it DEMANDS the viewer watch the next one

OUTPUT FORMAT (return ONLY this, no markdown, no extra text):
TITLE: <irresistible title under 60 chars — use numbers, power words, or questions>
DESCRIPTION: <3 punchy sentences. First sentence is a hook. Include relevant hashtags at end.>
TAGS: <10 highly searchable tags, comma-separated>
SLIDE_1: <hook text>
SLIDE_2: <context text>
SLIDE_3: <insight text>
SLIDE_4: <stakes text>
SLIDE_5: <CTA text>"""


def _educational_prompt(topic: str, wikipedia_summary: str = None) -> str:
    context = ""
    if wikipedia_summary:
        context = f"\nFACTUAL REFERENCE (use as inspiration only — never copy verbatim):\n---\n{wikipedia_summary[:400]}\n---\n"

    return f"""Write a PROFESSIONAL educational YouTube script that explains: "{topic}"
{context}
NARRATIVE STRUCTURE — follow this exact arc:
- SLIDE_1 (THE HOOK): Open with the most mind-blowing fact or counterintuitive truth about this topic. Make people feel they've been missing something their whole life. Start with "Most people don't know..." or "This changes everything about..." or a shocking number. Max 2 sentences.
- SLIDE_2 (SIMPLE EXPLANATION): Break down the core concept like explaining to a smart 15-year-old. Use an unexpected, vivid analogy from everyday life. No jargon. 2 sentences.
- SLIDE_3 (THE REAL WORLD): Give a concrete, specific real-world example that makes this click instantly. Use a story or scenario the viewer can visualize. 2 sentences.
- SLIDE_4 (THE DEEPER TRUTH): Share the one insight that completely changes how you see this topic. This should feel like a revelation. Make them think "I never thought of it that way." 2 sentences.
- SLIDE_5 (THE CTA): Summarize the key takeaway in one powerful sentence. Then invite engagement: ask viewers to share what surprised them most. End with "Subscribe to @yeah_shh — we make complex things simple, daily." 2 sentences.

WRITING RULES:
- Conversational and warm — like a brilliant friend explaining something over coffee
- Use "you", "your", "we", "imagine" to create personal connection
- Include 1 specific number, statistic, or date per slide where natural
- Every sentence should make the viewer feel smarter for watching
- Build genuine curiosity — don't give everything away in SLIDE_1
- 100% original explanations in your own words

OUTPUT FORMAT (return ONLY this, no markdown, no extra text):
TITLE: <clear, curiosity-driven title under 60 chars — e.g. "The Truth About X Nobody Tells You">
DESCRIPTION: <3 sentences. Hook, what they'll learn, why it matters. End with hashtags #education #learnwithme #yeah_shh>
TAGS: <10 relevant tags, comma-separated>
SLIDE_1: <hook text>
SLIDE_2: <simple explanation text>
SLIDE_3: <real world example text>
SLIDE_4: <deeper truth text>
SLIDE_5: <CTA text>"""


# ── Parser & fallback ─────────────────────────────────────────────────────────

def _parse_script(raw: str, topic: str, mode: str) -> dict:
    result = {
        "title": f"{'The Truth About' if mode == 'educational' else 'Breaking:'} {topic}",
        "description": f"Everything you need to know about {topic}. #trending #education #yeah_shh",
        "tags": ["trending", "education", "yeah_shh", topic.lower()[:20]],
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
        "title": f"The Truth About {topic} Nobody Tells You",
        "description": f"Everything you need to know about {topic}. #trending #education #yeah_shh",
        "tags": ["trending", "education", "yeah_shh"],
        "slides": [
            f"Most people have no idea what's really happening with {topic} right now.",
            "Here's the context that changes everything — and why it matters today.",
            "The surprising truth most people completely miss about this.",
            "Here's why this directly affects your life more than you think.",
            f"What do YOU think about this? Comment below. Follow @yeah_shh for more daily insights.",
        ],
        "mode": mode,
    }
