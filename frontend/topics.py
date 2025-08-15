from __future__ import annotations
import re
from collections import Counter, defaultdict
from typing import List

STOPWORDS = {
    "the","a","an","for","and","or","of","to","in","on","with","by","from","at","as","is","are",
    "it","its","that","this","these","those","be","was","were","will","shall","can","could",
    "has","have","had","but","not","no","you","your","our","their","they","he","she","we",
    "about","after","before","over","under","into","out","more","most","new","news","how",
    "why","what","when","where","which","who","vs","via","–","—","’s","&","’","“","”","amp"
}
WORD_RE   = re.compile(r"[a-z0-9\-]+")
PROPER_RE = re.compile(r"\b([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*)\b")

def _normalize(text: str) -> str:
    text = text or ""
    return text.replace("—", " ").replace("–", " ").replace("’", "'")

def _tokenize(text: str):
    for m in WORD_RE.finditer((text or "").lower()):
        w = m.group(0).strip("-")
        if len(w) < 3: 
            yield None  # boundary for RAKE
            continue
        if w in STOPWORDS:
            yield None
        else:
            yield w

def _rake_phrases(text: str, query_tokens: set[str]):
    tokens = list(_tokenize(text))
    phrases, cur = [], []
    for tok in tokens:
        if tok is None:
            if cur: phrases.append(cur); cur = []
        else:
            if tok not in query_tokens: cur.append(tok)
    if cur: phrases.append(cur)

    if not phrases: return []

    # degree/frequency scoring
    freq = Counter()
    degree = defaultdict(int)
    for ph in phrases:
        L = len(ph)
        uniq = set(ph)
        for w in uniq:
            freq[w] += ph.count(w)
            degree[w] += (L - 1)

    scored = []
    for ph in phrases:
        if 1 <= len(ph) <= 3:
            score = sum((degree[w] + 1) / max(freq[w], 1) for w in ph)
            scored.append((" ".join(ph).title(), score))

    seen, out = set(), []
    for p, s in sorted(scored, key=lambda x: x[1], reverse=True):
        key = p.lower().replace(" ", "")
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out

def suggest_topics(articles: List[dict], query: str, k: int = 3) -> List[str]:
    titles   = [(a.get("title")   or "") for a in articles]
    snippets = [(a.get("snippet") or "") for a in articles]
    raw      = " . ".join(titles + snippets)

    query_tokens = set(t for t in _tokenize(query.lower()) if t)

    # 1) RAKE candidates
    candidates = _rake_phrases(_normalize(raw), query_tokens)

    # 2) Proper nouns from titles
    if len(candidates) < k:
        proper = []
        for t in titles:
            proper += PROPER_RE.findall(t)
        proper = [
            p.strip() for p in proper
            if len(p) > 2 and p.lower() not in STOPWORDS and p.lower() not in query_tokens
        ]
        for p, _ in Counter(proper).most_common():
            key = p.lower().replace(" ", "")
            if key not in {c.lower().replace(" ", "") for c in candidates}:
                candidates.append(p)

    # 3) Frequent unigrams
    if len(candidates) < k:
        toks = [t for t in _tokenize(raw) if t and t not in query_tokens and t not in STOPWORDS]
        for w, _ in Counter(toks).most_common():
            w = w.title()
            key = w.lower().replace(" ", "")
            if key not in {c.lower().replace(" ", "") for c in candidates}:
                candidates.append(w)

    # First k unique
    out, seen = [], set()
    for c in candidates:
        key = c.lower().replace(" ", "")
        if key not in seen:
            seen.add(key)
            out.append(c)
        if len(out) >= k: break
    return out
