# app/ranker.py
from __future__ import annotations
from typing import List, Dict
import math
import requests
import config
import re
from datetime import datetime, timezone

# ---------- Embeddings (Ollama) ----------
def _embed_ollama(texts: List[str]) -> List[List[float]]:
    """
    Uses Ollama embeddings endpoint: POST /api/embeddings
    Model: config.EMBED_MODEL (e.g., "nomic-embed-text:latest")
    """
    url = f"{config.OLLAMA_BASE_URL.rstrip('/')}/api/embeddings"
    out: List[List[float]] = []
    for t in texts:
        payload = {"model": config.EMBED_MODEL, "prompt": t[:4000]}
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        emb = r.json().get("embedding")
        if not isinstance(emb, list):
            emb = r.json().get("data", [{}])[0].get("embedding", [])
        out.append(emb or [])
    return out

def _cosine(u: List[float], v: List[float]) -> float:
    if not u or not v or len(u) != len(v):
        return 0.0
    su = sum(x*x for x in u); sv = sum(y*y for y in v)
    if su <= 0 or sv <= 0: return 0.0
    dot = sum(x*y for x, y in zip(u, v))
    return dot / math.sqrt(su*sv)

# ---------- Lightweight keyword score (fallback) ----------
WORD_RE = re.compile(r"[a-z0-9]+")

def _tokens(text: str) -> set[str]:
    return {m.group(0) for m in WORD_RE.finditer(text.lower()) if len(m.group(0)) > 2}

def _keyword_overlap(q: str, t: str) -> float:
    qs, ts = _tokens(q), _tokens(t)
    if not qs or not ts:
        return 0.0
    inter = len(qs & ts)
    return inter / (len(qs) ** 0.5 * len(ts) ** 0.5)

# ---------- Date helpers ----------
def parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None

def recency_factor(published_at_iso: str | None, half_life_hours: float = 72.0) -> float:
    """
    Exponential time decay. Half-life default ~3 days.
    """
    dt = parse_iso(published_at_iso)
    if not dt:
        return 0.8  # mild default
    age_h = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0)
    return 0.5 ** (age_h / half_life_hours)

# ---------- Public API ----------
def rank_articles(query: str, articles: List[Dict], use_embeddings: bool = True) -> List[Dict]:
    """
    Returns a re-ordered copy of articles.
    Score = 0.7 * semantic + 0.2 * recency + 0.1 * keyword_overlap
    Falls back to keyword overlap if embeddings unavailable.
    """
    items = []
    texts = []
    for a in articles:
        title = a.get("title") or ""
        snippet = a.get("snippet") or ""
        texts.append(f"{title}\n\n{snippet}".strip()[:4000])
        items.append(a)

    semantic_scores: List[float] = [0.0] * len(items)
    if use_embeddings:
        try:
            q_emb = _embed_ollama([query])[0]
            a_embs = _embed_ollama(texts)
            semantic_scores = [_cosine(q_emb, e) for e in a_embs]
        except Exception:
            # silently fall back
            semantic_scores = [0.0] * len(items)
            use_embeddings = False

    kw_scores = [_keyword_overlap(query, t) for t in texts]
    recency = [recency_factor(a.get("published_at")) for a in items]

    out = []
    for a, s_sem, s_kw, s_rec in zip(items, semantic_scores, kw_scores, recency):
        if use_embeddings:
            score = 0.7 * s_sem + 0.2 * s_rec + 0.1 * s_kw
        else:
            score = 0.7 * s_kw + 0.3 * s_rec
        b = a.copy()
        b["_score"] = round(float(score), 6)
        out.append(b)

    out.sort(key=lambda x: x["_score"], reverse=True)
    return out
