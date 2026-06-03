"""
Topic selector with 10 content categories rotating daily.
Each category has its own script mode so the AI writes
in the right style (story, analysis, explainer, etc.)
"""

import logging
import requests
import random
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Content Library ───────────────────────────────────────────────────────────
# Each entry: (topic, mode, category)
# mode: 'educational' | 'trending' | 'story' | 'sports' | 'movie' | 'mythology'

CONTENT_LIBRARY = [

    # ── Indian Mythology ──────────────────────────────────────────────────────
    ("The Real Story of Hanuman — Beyond What You Know",                    "mythology", "Indian Mythology"),
    ("Why Lord Shiva Opened His Third Eye — The Full Story",                "mythology", "Indian Mythology"),
    ("Draupadi's Curse — The Dark Side of the Mahabharata",                "mythology", "Indian Mythology"),
    ("The Secret Birth of Karna — Mahabharata's Greatest Tragedy",         "mythology", "Indian Mythology"),
    ("Why Vishnu Chose to Be Born as Krishna",                             "mythology", "Indian Mythology"),
    ("The Story of Eklavya — The Greatest Student India Never Had",        "mythology", "Indian Mythology"),
    ("Ravana Was Not a Villain — The Untold Story",                        "mythology", "Indian Mythology"),
    ("The Curse of Gandhari — How the Mahabharata War Was Prophesied",     "mythology", "Indian Mythology"),
    ("The Origin of Ganesha — The True Story Behind the Elephant God",     "mythology", "Indian Mythology"),
    ("Shakuntala and Dushyanta — India's Greatest Love Story",             "mythology", "Indian Mythology"),
    ("The Hidden Powers of the Sudarshana Chakra",                         "mythology", "Indian Mythology"),
    ("Why Bhishma Chose to Die — The Vow That Destroyed a Kingdom",        "mythology", "Indian Mythology"),
    ("The 14 Gems from Samudra Manthan — What Were They Really?",          "mythology", "Indian Mythology"),
    ("Ashwatthama — The Immortal Warrior Still Walking the Earth",         "mythology", "Indian Mythology"),
    ("The Real Meaning of the Gayatri Mantra",                             "mythology", "Indian Mythology"),

    # ── Sports ────────────────────────────────────────────────────────────────
    ("Why Virat Kohli is the Greatest Test Batter of His Generation",      "sports",    "Sports"),
    ("How Lionel Messi Became the Greatest Footballer Ever",               "sports",    "Sports"),
    ("The Science Behind Usain Bolt's World Record Sprint",                "sports",    "Sports"),
    ("How Formula 1 Cars Generate More Downforce Than Weight",             "sports",    "Sports"),
    ("Why MS Dhoni's Calmness Under Pressure is Scientifically Unique",    "sports",    "Sports"),
    ("The Real Reason Ronaldo Trains Harder Than Everyone Else",           "sports",    "Sports"),
    ("How the IPL Changed World Cricket Forever",                          "sports",    "Sports"),
    ("The Untold Story of Roger Federer's Last Match",                     "sports",    "Sports"),
    ("Why Chess is the Most Mentally Demanding Sport in the World",        "sports",    "Sports"),
    ("How India Won the 1983 Cricket World Cup Against All Odds",          "sports",    "Sports"),
    ("The Psychology of Penalty Shootouts — Why Teams Win or Lose",       "sports",    "Sports"),
    ("Neeraj Chopra — How India Found Its First Athletics Gold Medal",     "sports",    "Sports"),

    # ── Tech & AI ─────────────────────────────────────────────────────────────
    ("How GPT-4 Thinks — Inside the Most Powerful AI Ever Built",         "educational","Tech"),
    ("Why Apple Silicon is 10 Years Ahead of Intel",                      "educational","Tech"),
    ("How SpaceX Lands Rockets Autonomously — The Engineering Explained", "educational","Tech"),
    ("What is Neuralink and What Happens When Humans Get Chips",          "educational","Tech"),
    ("How DeepMind Solved a 50-Year-Old Biology Problem",                 "educational","Tech"),
    ("The Real Reason Everyone is Scared of AGI",                         "educational","Tech"),
    ("How Tesla's Self-Driving AI Actually Works",                        "educational","Tech"),
    ("Why Quantum Computers Will Break All Encryption",                   "educational","Tech"),
    ("The Tech Behind India's UPI — Why the World Is Copying It",        "educational","Tech"),
    ("How ISRO Built Chandrayaan-3 for Less Than a Hollywood Film",       "educational","Tech"),
    ("What Happens When AI Becomes Smarter Than All Humans Combined",     "educational","Tech"),

    # ── Movies & Entertainment ────────────────────────────────────────────────
    ("Why Inception's Ending Still Divides the Internet",                 "movie",      "Movies"),
    ("The Dark Truth Behind the Making of Interstellar",                  "movie",      "Movies"),
    ("Why RRR Became India's Greatest Film Export",                       "movie",      "Movies"),
    ("How Christopher Nolan Plans a Movie Before Writing a Single Word",  "movie",      "Movies"),
    ("The Psychological Tricks Bollywood Uses to Make You Cry",           "movie",      "Movies"),
    ("Why Baahubali Changed Indian Cinema Forever",                       "movie",      "Movies"),
    ("The Hidden Symbolism in The Dark Knight You Never Noticed",         "movie",      "Movies"),
    ("How Pushpa Became Allu Arjun's Career-Defining Masterpiece",        "movie",      "Movies"),
    ("Why Avengers Endgame Made Everyone Cry — The Psychology Behind It", "movie",      "Movies"),
    ("The Real Story Behind the Making of 3 Idiots",                      "movie",      "Movies"),
    ("How KGF Became a Global Phenomenon from a Regional Language Film",  "movie",      "Movies"),

    # ── Science & Space ───────────────────────────────────────────────────────
    ("What Happens to Your Body in the First 60 Seconds in Outer Space",  "educational","Science"),
    ("The Multiverse Theory — Does Another You Exist Right Now?",         "educational","Science"),
    ("How CRISPR Can Eliminate Genetic Diseases in One Generation",       "educational","Science"),
    ("Why Scientists Think We Might Be Living in a Simulation",           "educational","Science"),
    ("The Real Size of the Universe — Numbers Too Big to Comprehend",     "educational","Science"),
    ("How a Black Hole Would Actually Kill You — Step by Step",           "educational","Science"),
    ("The Science of Déjà Vu — Why Your Brain Glitches",                 "educational","Science"),
    ("How Time Actually Slows Down Near Massive Objects",                 "educational","Science"),
    ("Why Mars Could Support Human Life — The Real Science",              "educational","Science"),

    # ── History & Mysteries ───────────────────────────────────────────────────
    ("The Unsolved Mystery of the Indus Valley Civilization's Collapse",  "story",     "History"),
    ("How Chandragupta Maurya Built India's First Empire at 20",          "story",     "History"),
    ("The Secret Library of Alexandria — What Was Really Lost",           "story",     "History"),
    ("How Genghis Khan Conquered Half the World in 25 Years",             "story",     "History"),
    ("The Real Story of Cleopatra — Not What Hollywood Showed You",       "story",     "History"),
    ("How the Taj Mahal Was Built — The Engineering of a Love Story",     "story",     "History"),
    ("The Bermuda Triangle — What Science Actually Says",                  "story",     "History"),
    ("How Ancient Indians Knew the Earth Was Round 2000 Years Before Europe","story",  "History"),
    ("The Mystery of Mohenjo-daro's Sudden Abandonment",                  "story",     "History"),

    # ── Finance & Business ────────────────────────────────────────────────────
    ("How Mukesh Ambani Turned Reliance Into India's Most Valuable Company","educational","Business"),
    ("The Real Reason Most Startups Fail in Year 2",                      "educational","Business"),
    ("How Zerodha Built India's Biggest Broker With Zero Advertising",    "educational","Business"),
    ("What Warren Buffett Looks For Before Buying Any Stock",             "educational","Business"),
    ("How Narayana Murthy Built Infosys With ₹10,000",                   "story",     "Business"),
    ("Why 90% of People Invest Wrong — The Math Nobody Teaches You",      "educational","Business"),
    ("How the 2008 Financial Crisis Was Predicted and Ignored",           "educational","Business"),

    # ── Health & Psychology ───────────────────────────────────────────────────
    ("Why Your Brain Creates False Memories — And Does It Every Night",   "educational","Psychology"),
    ("The Dopamine Trap — Why Your Phone is More Addictive Than Drugs",   "educational","Psychology"),
    ("How Meditation Physically Changes the Structure of Your Brain",     "educational","Psychology"),
    ("Why Cold Showers Make You Mentally Stronger — The Science",         "educational","Psychology"),
    ("The Real Reason You Procrastinate — It's Not Laziness",             "educational","Psychology"),
    ("How Your Gut Bacteria Control Your Mood More Than Your Brain Does", "educational","Psychology"),
    ("Why Some People Never Get Sick — The Immune System Secret",         "educational","Psychology"),

    # ── Motivational & True Stories ───────────────────────────────────────────
    ("How APJ Abdul Kalam Went From a Newspaper Boy to President of India","story",    "Motivation"),
    ("The Unbelievable Story of Dashrath Manjhi — The Mountain Man",      "story",     "Motivation"),
    ("How Srinivasa Ramanujan Taught Himself Mathematics With No Teacher", "story",    "Motivation"),
    ("Why Elon Musk Almost Lost Everything Before SpaceX Succeeded",      "story",     "Motivation"),
    ("The Real Story of Dhirubhai Ambani — From Nothing to Everything",   "story",     "Motivation"),
    ("How Steve Jobs Got Fired and Came Back to Save Apple",              "story",     "Motivation"),

    # ── Trending (fetched live) ───────────────────────────────────────────────
    (None, "trending", "Trending"),
    (None, "trending", "Trending"),
    (None, "trending", "Trending"),
]

# Category rotation order for variety across the week
CATEGORY_CYCLE = [
    "Indian Mythology", "Tech", "Sports", "Movies",
    "Science", "History", "Business", "Psychology",
    "Motivation", "Trending",
]


def select_topic_and_mode() -> dict:
    """
    Returns {'topic': str|None, 'mode': str, 'category': str, 'wikipedia_summary': str|None}
    Rotates through all categories so every type gets covered.
    """
    day_of_year = datetime.now().timetuple().tm_yday

    # Pick category for today
    category = CATEGORY_CYCLE[day_of_year % len(CATEGORY_CYCLE)]

    # Get all topics in that category
    pool = [(t, m, c) for t, m, c in CONTENT_LIBRARY if c == category]

    if not pool or category == "Trending":
        return {"mode": "trending", "topic": None, "category": "Trending", "wikipedia_summary": None}

    # Rotate through pool by week number so same category doesn't repeat same topic
    week = day_of_year // 7
    topic, mode, cat = pool[week % len(pool)]

    summary = _fetch_wikipedia_summary(topic) if mode != "trending" else None

    return {
        "mode": mode,
        "topic": topic,
        "category": cat,
        "wikipedia_summary": summary,
    }


def _fetch_wikipedia_summary(topic: str):
    try:
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + topic.replace(" ", "_")
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            summary = data.get("extract", "")
            return summary[:500] if summary else None
    except Exception as e:
        logger.warning(f"Wikipedia fetch failed: {e}")
    return None
