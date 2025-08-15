from __future__ import annotations
import re

# Client-side safety (defense in depth)
ADULT_PAT = re.compile(r"\b(ns?fw|porn|pornhub|xvideos|xxx|sex(ual|ually)?|erot(ic|ica)|fetish)\b", re.I)
HATE_PAT  = re.compile(r"\b(hate\s*speech|ethnic\s*cleansing|genocide)\b", re.I)
VIOL_PAT  = re.compile(r"\b(gore|beheading|dismemberment|graphic\s+violence)\b", re.I)

def is_client_safe(text: str) -> bool:
    t = text or ""
    if ADULT_PAT.search(t): return False
    if HATE_PAT.search(t): return False
    if VIOL_PAT.search(t): return False
    return True
