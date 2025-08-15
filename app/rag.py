# app/rag.py
import json
from typing import List, Dict, Any
import requests
import config
from app.content_extractor import fetch_fulltext
from app.vector_store import add_article_chunks, query as vs_query
from langdetect import detect

def chunk_text(s: str, size: int = 900, overlap: int = 150) -> List[str]:
    s = (s or "").strip()
    if not s: return []
    out, i = [], 0
    step = max(size - overlap, 1)
    while i < len(s):
        out.append(s[i:i+size])
        i += step
    return out

def _ollama_generate(prompt: str, temperature: float = 0.7) -> str:
    r = requests.post(
        f"{config.OLLAMA_BASE_URL}/api/generate",
        json={"model": config.LLM_MODEL, "prompt": prompt, "stream": False,
              "options": {"temperature": temperature}},
        timeout=120,
    )
    r.raise_for_status()
    return r.json().get("response", "").strip()

MAP_PROMPT = """
You are a concise journalist and summarizer. From the ARTICLE below, write 3–5 bullet points summarizing key insights.

Rules:
- Summarize in **English** only.
- Do NOT repeat phrases or facts from the article title or link.
- Do NOT quote directly or use exact sentences from the article.
- Avoid generic openings. Be specific and insightful.
- Each bullet must be >= 100 words.
- It should be concise and also informative.
- Do not begin with the acronyms

TITLE: {title}
LINK: {link}
ARTICLE:
{body}
"""

REDUCE_PROMPT = """User preferences: {prefs}
Query: {query}
Synthesize the per-article bullets into a briefing.

Return JSON:
{{"summary":"...", "highlights":[ "...", "..."], "top":[{{"title":"...","link":"..."}}]}}
Per-article bullets:
{bullets}
Only return JSON.
"""

def generate_news_response(news_articles: List[Dict[str, Any]], user_preferences: str, query: str, user_id: int = 0) -> Dict[str, Any]:
    # 1) index / upsert
    for art in news_articles:
        title   = art.get("title") or ""
        link    = art.get("link") or art.get("url") or ""
        snippet = art.get("snippet") or art.get("description") or ""
        if not (title and link): 
            continue
        body = fetch_fulltext(link) or snippet
        try:
            if detect(body) != "en":
                continue  # skip non-English articles
        except:
            pass 
        chunks = chunk_text(body)
        add_article_chunks(user_id=user_id, title=title, link=link, chunks=chunks, snippet=snippet)

    # 2) retrieve
    hits = vs_query(user_id=user_id, query_text=query, k=10)
    if not hits:
        return {"summary": "No relevant content found.", "highlights": [], "top": []}

    # 3) map per article (group by link)
    by_link: Dict[str, Dict[str, Any]] = {}
    for h in hits:
        by_link.setdefault(h["link"], {"title": h["title"], "link": h["link"], "texts": []})
        if len(by_link[h["link"]]["texts"]) < 2:
            by_link[h["link"]]["texts"].append(h["text"])

    mapped = []
    for v in by_link.values():
        body = "\n\n".join(v["texts"])
        bullets = _ollama_generate(MAP_PROMPT.format(title=v["title"], link=v["link"], body=body[:10000]))
        mapped.append({"title": v["title"], "link": v["link"], "bullets": bullets})

    # 4) reduce
    block = "\n\n".join([f"TITLE: {m['title']}\nURL: {m['link']}\nBULLETS:\n{m['bullets']}" for m in mapped])
    raw = _ollama_generate(REDUCE_PROMPT.format(prefs=user_preferences, query=query, bullets=block))
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"summary": raw, "highlights": [], "top": [{"title": m["title"], "link": m["link"]} for m in mapped[:5]]}

def summarize_articles(items: list[dict], user_id: int = 0) -> dict[str, str]:
    """
    items: [{'title','link','snippet',...}, ...]
    Returns {link: concise_summary}
    """
    out = {}
    for it in items:
        title   = it.get("title", "")
        link    = it.get("link", "")
        snippet = it.get("snippet", "")

        # Try to fetch the full article content if possible
        body = fetch_fulltext(link) or snippet or title
        if not body:
            out[link] = snippet or title or ""
            continue

        # Build the summarization prompt
        prompt = (
            "You are a concise news assistant. Write a 2-3 sentence, neutral summary. "
            "Focus on what happened and why it matters. Avoid quotes or clickbait.\n\n"
            f"Title: {title}\nContent: {body[:3000]}"
        )
        try:
            summ = _ollama_generate(prompt)
        except Exception:
            summ = snippet or title or ""

        out[link] = summ.strip()

    return out

