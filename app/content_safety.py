from __future__ import annotations
import re
from typing import Dict, Tuple
import config

# lazy global
_DETOX = None
_DETOX_ERR = None

BLOCKLIST_ADULT = [
    r"\b(ns?fw|porn|pornhub|xvideos|xxx)\b",
    r"\bsex(ual|ually)?\b", r"\berot(ic|ica)\b", r"\bfetish\b",
]
BLOCKLIST_HATE = [
    r"\b(hate\s*speech|ethnic\s*cleansing|genocide)\b",
]
BLOCKLIST_VIOLENCE = [
    r"\b(gore|beheading|dismemberment|graphic\s+violence)\b",
]

def _ensure_detox():
    global _DETOX, _DETOX_ERR
    if _DETOX is not None or _DETOX_ERR is not None:
        return
    try:
        from detoxify import Detoxify
        _DETOX = Detoxify('original')
    except Exception as e:
        _DETOX_ERR = e

def _regex_block(text: str) -> Dict[str, bool]:
    flags = {"adult": False, "hate": False, "violence": False}
    t = text.lower()
    if config.BLOCK_ADULT:
        flags["adult"] = any(re.search(p, t) for p in BLOCKLIST_ADULT)
    if config.BLOCK_HATE:
        flags["hate"] = any(re.search(p, t) for p in BLOCKLIST_HATE)
    if config.BLOCK_VIOLENCE:
        flags["violence"] = any(re.search(p, t) for p in BLOCKLIST_VIOLENCE)
    return flags

def moderate_text(text: str) -> Tuple[bool, Dict[str, float], Dict[str, bool]]:
    """(is_safe, model_scores, regex_flags)"""
    if not text.strip():
        return True, {}, {"adult": False, "hate": False, "violence": False}

    flags = _regex_block(text)
    if any(flags.values()):
        return False, {}, flags

    if config.SAFETY_ENABLED:
        _ensure_detox()
        if _DETOX is not None:
            scores = _DETOX.predict(text)
            tox = float(scores.get("toxicity", 0.0))
            severe = float(scores.get("severe_toxicity", 0.0))
            sexual = float(scores.get("sexual_explicit", 0.0))
            threat = float(scores.get("threat", 0.0))
            if tox >= config.TOXICITY_THRESHOLD or severe >= config.TOXICITY_THRESHOLD:
                return False, scores, flags
            if config.BLOCK_ADULT and sexual >= 0.5:
                return False, scores, flags
            if config.BLOCK_VIOLENCE and threat >= 0.5:
                return False, scores, flags
            return True, scores, flags

    return True, {}, flags

def redact_profanity(text: str) -> str:
    profane = [r"\bfuck\b", r"\bshit\b", r"\basshole\b", r"\bbitch\b"]
    out = text
    for p in profane:
        out = re.sub(p, lambda m: m.group(0)[0] + "★"*(len(m.group(0))-1), out, flags=re.I)
    return out
