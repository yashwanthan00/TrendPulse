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


def generate_script(topic: str, mode: str = "trending", wikipedia_summary: str = None, research: dict = None, category: str = None) -> dict:
    """Returns dict: title, description, tags, slides, mode."""
    prompts = {
        "mythology": _mythology_prompt,
        "story":     _story_prompt,
        "sports":    _sports_prompt,
        "movie":     _movie_prompt,
        "trending":  _trending_prompt,
        "educational": _educational_prompt,
    }
    prompt_fn = prompts.get(mode, _educational_prompt)

    if mode in ("educational", "mythology", "story", "sports", "movie"):
        prompt = prompt_fn(topic, wikipedia_summary, research)
    else:
        prompt = prompt_fn(topic, research)

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

def _mythology_prompt(topic: str, wikipedia_summary: str = None, research: dict = None) -> str:
    return f"""Write a CAPTIVATING Indian mythology script about: "{topic}"

You are an expert storyteller who brings ancient Indian stories to life. Your style blends
the gravitas of the original texts with modern cinematic storytelling — like a documentary
narrator meets a campfire storyteller.

NARRATIVE STRUCTURE:
- SLIDE_1 (THE HOOK): Open with the most dramatic, spine-tingling moment of this story. Drop the viewer straight into the action. Use vivid imagery. Make them feel they are THERE. 2 sentences.
- SLIDE_2 (THE BACKSTORY): Give the essential divine/cosmic context. Why did this event happen? What forces were at play? Reference specific characters, powers, or prophecies. 2 sentences.
- SLIDE_3 (THE TURNING POINT): The moment everything changed. The sacrifice, the battle, the curse, the revelation. Make it visceral and emotional. 2 sentences.
- SLIDE_4 (THE DEEPER MEANING): What does this story teach us that is STILL relevant today? Connect ancient wisdom to modern life. This should feel like a profound insight. 2 sentences.
- SLIDE_5 (THE CTA): End with a question that sparks debate in the comments. Then: "Follow @yeah_shh for more untold stories from India's greatest epics." 2 sentences.

WRITING RULES:
- Use the original Sanskrit names (Arjuna, not Arjun; Krishna, Dharma, Karma)
- Refer to specific events, weapons, divine powers by their exact names
- Write with reverence but also wonder — these stories deserve awe
- Use present tense for dramatic moments ("Arjuna raises his bow...")
- Avoid disrespecting any deity or tradition
- 100% original narrative — inspired by scriptures, not copied

OUTPUT FORMAT (return ONLY this, no markdown):
TITLE: <dramatic title that creates curiosity — e.g. "The Secret Weapon Arjuna Was Never Supposed to Have">
DESCRIPTION: <3 sentences. Hook, what the story reveals, why it matters today. End with #IndianMythology #Hinduism #yeah_shh>
TAGS: <10 tags: mythology, Indian, Hindu, specific character names, epic, etc.>
SLIDE_1: <dramatic opening>
SLIDE_2: <backstory>
SLIDE_3: <turning point>
SLIDE_4: <deeper meaning>
SLIDE_5: <CTA>"""


def _story_prompt(topic: str, wikipedia_summary: str = None, research: dict = None) -> str:
    research_block = f"\n\n{research['research_text']}\n" if research and research.get("research_text") else ""
    wiki_block = f"\nFACTUAL REFERENCE: {wikipedia_summary[:300]}\n" if wikipedia_summary else ""
    return f"""Write a COMPELLING narrative story script about: "{topic}"{research_block}{wiki_block}

You are a master documentary narrator — think Netflix documentary meets BBC storytelling.
Every fact feels like a revelation. Every moment feels cinematic.

NARRATIVE STRUCTURE:
- SLIDE_1 (THE HOOK): Start at the most dramatic moment of the story — in medias res. Drop the viewer into the tension immediately. 2 sentences.
- SLIDE_2 (THE ORIGINS): Where did this all begin? Set the scene with specific details — year, place, circumstances. 2 sentences.
- SLIDE_3 (THE STRUGGLE): What obstacles, failures, or impossible odds did the subject face? Be specific. Make the viewer feel the weight of it. 2 sentences.
- SLIDE_4 (THE TRIUMPH/TWIST): The moment of victory, tragedy, or shocking revelation. This is the emotional peak. 2 sentences.
- SLIDE_5 (THE LEGACY + CTA): What did this story leave behind? Why does it still matter? Then invite comments + "Follow @yeah_shh for more incredible stories." 2 sentences.

WRITING RULES:
- Use specific dates, names, places — details make stories credible
- Write in active, present tense where possible for immediacy
- One specific number or statistic per slide
- Emotional but factually grounded
- 100% original narrative

OUTPUT FORMAT (return ONLY this, no markdown):
TITLE: <cinematic title that sounds like a documentary — under 60 chars>
DESCRIPTION: <3 sentences. Story hook, what's revealed, why it's inspiring. End with #history #truestory #yeah_shh>
TAGS: <10 relevant tags>
SLIDE_1: <dramatic opening>
SLIDE_2: <origins>
SLIDE_3: <struggle>
SLIDE_4: <triumph/twist>
SLIDE_5: <legacy + CTA>"""


def _sports_prompt(topic: str, wikipedia_summary: str = None, research: dict = None) -> str:
    research_block = f"\n\n{research['research_text']}\n" if research and research.get("research_text") else ""
    return f"""Write a HIGH-ENERGY sports script about: "{topic}"{research_block}

You are the most passionate sports commentator meets analytical expert. Your writing
makes non-sports fans care and sports fans go crazy.

NARRATIVE STRUCTURE:
- SLIDE_1 (THE HOOK): Start with the most jaw-dropping stat, record, or moment related to this topic. Something that makes fans say "I never knew that." 2 sentences.
- SLIDE_2 (THE CONTEXT): Why is this athlete/team/event extraordinary? Give the specific numbers — records broken, odds overcome, years of struggle. 2 sentences.
- SLIDE_3 (THE SECRET): What does this athlete do differently that others don't? Training secret, mental edge, technique, sacrifice. Be specific. 2 sentences.
- SLIDE_4 (THE IMPACT): How has this changed the sport forever? What do today's players owe to this? 2 sentences.
- SLIDE_5 (THE CTA): Ask a polarizing sports debate question to drive comments. Then: "Follow @yeah_shh for daily sports breakdowns." 2 sentences.

WRITING RULES:
- Use exact statistics, match scores, world records where relevant
- Write with infectious energy — exclamation where natural
- Reference specific matches, tournaments, years
- Accessible to both hardcore fans and casual viewers
- 100% original content

OUTPUT FORMAT (return ONLY this, no markdown):
TITLE: <punchy sports title with a number or superlative — under 60 chars>
DESCRIPTION: <3 sentences. Stat hook, analysis, debate question. End with #sports #cricket #football #yeah_shh>
TAGS: <10 tags including sport name, athlete name, tournament, etc.>
SLIDE_1: <jaw-dropping hook>
SLIDE_2: <context with numbers>
SLIDE_3: <the secret>
SLIDE_4: <the impact>
SLIDE_5: <debate CTA>"""


def _movie_prompt(topic: str, wikipedia_summary: str = None, research: dict = None) -> str:
    research_block = f"\n\n{research['research_text']}\n" if research and research.get("research_text") else ""
    return f"""Write an ENGAGING movie/entertainment script about: "{topic}"{research_block}

You are a film critic meets pop culture analyst — you love movies deeply and know
how to make anyone excited about cinema.

NARRATIVE STRUCTURE:
- SLIDE_1 (THE HOOK): Start with the most surprising behind-the-scenes fact, box office record, or hidden detail about this film/director. Something casual viewers don't know. 2 sentences.
- SLIDE_2 (THE GENIUS): What makes this film/director technically or artistically brilliant? Reference specific scenes, cinematography, music, writing. 2 sentences.
- SLIDE_3 (THE HIDDEN LAYER): A deeper meaning, symbolism, or Easter egg most people completely missed. This should make viewers want to rewatch. 2 sentences.
- SLIDE_4 (THE IMPACT): How did this film change cinema, culture, or the industry forever? Specific examples. 2 sentences.
- SLIDE_5 (THE CTA): Ask viewers what their favourite scene/moment is. Then: "Follow @yeah_shh for daily film breakdowns and hidden details." 2 sentences.

WRITING RULES:
- Reference specific scenes, characters, directors by name
- Mix film analysis with emotional connection
- Include box office numbers, awards, or cultural impact stats
- Accessible to casual movie fans, not just cinephiles
- 100% original analysis — not copied from reviews

OUTPUT FORMAT (return ONLY this, no markdown):
TITLE: <intriguing movie title with "Hidden", "Secret", "Truth" or a question — under 60 chars>
DESCRIPTION: <3 sentences. Hook, what's revealed, why fans should watch. End with #movies #cinema #bollywood #yeah_shh>
TAGS: <10 tags including film title, director, genre, language>
SLIDE_1: <surprising hook>
SLIDE_2: <the genius>
SLIDE_3: <hidden layer>
SLIDE_4: <the impact>
SLIDE_5: <CTA>"""


def _trending_prompt(topic: str, research: dict = None) -> str:
    research_block = f"\n\n{research['research_text']}\n" if research and research.get("research_text") else ""
    return f"""Write a PROFESSIONAL, high-retention YouTube script about the trending topic: "{topic}".{research_block}

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


def _educational_prompt(topic: str, wikipedia_summary: str = None, research: dict = None) -> str:
    context = ""
    if research and research.get("research_text"):
        context = f"\n\n{research['research_text']}\n"
    elif wikipedia_summary:
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
