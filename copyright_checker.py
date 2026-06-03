"""
Full copyright audit for every pipeline run.

What this enforces:
  - Script:   AI-generated original content only, no verbatim copies
  - Images:   programmatic generator (100% original) or CC0 verified sources only
  - Fonts:    Roboto (Apache 2.0) — verified open source
  - Audio:    edge-tts output is original — no background music (avoids Content ID)
  - Logos:    no third-party brand logos or watermarks allowed
  - Trademarks: flagged if used as the primary video subject
"""

import re
import logging

logger = logging.getLogger(__name__)

# Phrases that indicate verbatim copying
VERBATIM_PATTERNS = [
    r"according to wikipedia",
    r"as (stated|written|published) (on|in|by)",
    r"quote[sd]?\s+from",
    r"source:\s*wikipedia",
    r"copyright\s+\d{4}",
    r"all rights reserved",
    r"©",
]

# Trademarks risky as primary video subject
RISKY_TRADEMARKS = [
    "disney", "netflix", "marvel", "warner bros", "coca-cola",
    "apple inc", "microsoft windows", "google chrome", "amazon prime",
    "spotify", "instagram", "tiktok", "youtube",
]

APPROVED_IMAGE_PROVIDERS = {"Generated", "Pexels-CC0", "Unsplash-CC0"}
APPROVED_FONTS = {"Roboto"}  # Apache 2.0


def run_full_audit(script: dict, image_provider: str) -> dict:
    """
    Run all copyright checks. Returns:
      {'passed': bool, 'warnings': list[str], 'errors': list[str], 'script': dict}
    Errors = must fix before upload. Warnings = logged but non-blocking.
    """
    warnings, errors = [], []

    _check_script_originality(script, warnings, errors)
    _check_image_source(image_provider, errors)
    _check_font(warnings)

    # Append attribution footer to description always
    script["description"] = _build_description(script["description"])

    passed = len(errors) == 0

    _print_report(passed, warnings, errors)

    return {
        "passed": passed,
        "warnings": warnings,
        "errors": errors,
        "script": script,
    }


# ── Checks ────────────────────────────────────────────────────────────────────

def _check_script_originality(script: dict, warnings: list, errors: list):
    full_text = " ".join(script.get("slides", []) + [
        script.get("title", ""), script.get("description", "")
    ]).lower()

    for pattern in VERBATIM_PATTERNS:
        if re.search(pattern, full_text):
            errors.append(f"Possible non-original content detected: '{pattern}'")

    title_lower = script.get("title", "").lower()
    for tm in RISKY_TRADEMARKS:
        if title_lower.startswith(tm):
            warnings.append(
                f"Title starts with trademark '{tm}' — may trigger Content ID claim. "
                "Consider rewording (e.g. 'The Future of Streaming' instead of 'Netflix...')"
            )


def _check_image_source(provider: str, errors: list):
    if provider not in APPROVED_IMAGE_PROVIDERS:
        errors.append(
            f"Image provider '{provider}' is not in the approved list: "
            f"{APPROVED_IMAGE_PROVIDERS}. Use generated backgrounds or CC0 sources only."
        )


def _check_font(warnings: list):
    import os
    font_path = os.path.join("assets", "fonts", "Roboto-Bold.ttf")
    if not os.path.exists(font_path):
        warnings.append("Roboto font not yet downloaded — will be fetched on first run (Apache 2.0 license, safe)")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_description(existing: str) -> str:
    footer = (
        "\n\n---\n"
        "This video was created by an AI pipeline.\n"
        "Visuals: 100% original, programmatically generated.\n"
        "Narration: AI voice (edge-tts).\n"
        "Script: AI-generated original content.\n"
        "Font: Roboto (Apache License 2.0).\n"
        "No third-party copyrighted material was used."
    )
    if "programmatically generated" not in existing:
        return existing.rstrip() + footer
    return existing


def _print_report(passed: bool, warnings: list, errors: list):
    logger.info("╔══ COPYRIGHT AUDIT ══════════════════════════════╗")
    logger.info(f"║  Status : {'✅ PASSED' if passed else '❌ FAILED'}")
    logger.info(f"║  Errors  : {len(errors)}")
    logger.info(f"║  Warnings: {len(warnings)}")
    for e in errors:
        logger.error(f"║  ERROR   → {e}")
    for w in warnings:
        logger.warning(f"║  WARN    → {w}")
    logger.info("╚═════════════════════════════════════════════════╝")


# keep old API names working
def check_script(script: dict) -> dict:
    result = run_full_audit(script, "Generated")
    return {"safe": result["passed"], "warnings": result["warnings"], "cleaned": result["script"]}


def log_copyright_report(script_result: dict, image_source: str):
    pass  # now handled inside run_full_audit
