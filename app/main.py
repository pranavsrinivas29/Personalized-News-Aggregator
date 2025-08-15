from __future__ import annotations
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .content_safety import moderate_text, redact_profanity
from . import news_fetcher
from database.db import Base, engine            
import database.models as db_models  
from .auth_routes import router as auth_router      
from .auth import decode_token 
from .suggest_routes import router as suggest_router
import config
try:
    # use your RAG pipeline if present
    from .rag import generate_news_response as rag_generate
except Exception:
    rag_generate = None  # graceful fallback

app = FastAPI(title="Personalized News Aggregator API", version="1.0.0")

@app.on_event("startup")
def _startup():
    # Import models module so SQLAlchemy knows about tables
    _ = db_models
    Base.metadata.create_all(bind=engine)
    
# ✅ mount the auth routes
app.include_router(auth_router) 
app.include_router(suggest_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only; tighten for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Article(BaseModel):
    title: str
    link: str
    snippet: Optional[str] = ""
    source: Optional[str] = ""
    published_at: Optional[str] = ""

class Summary(BaseModel):
    summary: str
    highlights: List[str] = []
    top: List[Dict[str, str]] = []

class GetNewsResponse(BaseModel):
    articles: List[Article]
    summary: Summary

class SummItem(BaseModel):
    title: str
    link: str
    snippet: str | None = ""
    source: str | None = ""
    published_at: str | None = ""

class SummBatchIn(BaseModel):
    items: list[SummItem]


@app.get("/health")
def health():
    return {"ok": True}

@app.get("/get_news", response_model=GetNewsResponse)
def get_news(
    query: str = Query(..., min_length=1),
    user_id: int = 0,
    prefs: str = "",
    token: str | None = None,
    authorization: str | None = Header(default=None, alias="Authorization"),
    lang: str = Query(config.DEFAULT_LANG, description="Language (SerpAPI hl)"),
    region: str = Query(config.DEFAULT_REGION, description="Country/region (SerpAPI gl; also RSS)"),
    timeframe: str = Query("7d"),
    sort: str = Query("date"),
):
    # resolve user_id from token/header if present
    resolved_user_id = user_id or 0
    jwt_token = None
    if authorization and authorization.lower().startswith("bearer "):
        jwt_token = authorization.split(" ", 1)[1].strip()
    elif token:
        jwt_token = token.strip()
    if jwt_token:
        try:
            resolved_user_id = int(decode_token(jwt_token))
        except Exception:
            pass

    # fetch
    try:
        articles = news_fetcher.fetch_news_from_sources(
            query,
            lang=lang,
            region=region,
            timeframe=timeframe,
            sort=sort,
            limit=50,
        )
    except ValueError as ve:
        # safety blocked path (from news_fetcher)
        detail = {"message": "Query blocked by content safety", "blocked": True, "flags": {}}
        msg = str(ve)
        if "blocked by safety:" in msg:
            # extract flags dict if present
            try:
                import ast
                flags = ast.literal_eval(msg.split("blocked by safety:", 1)[1].strip())
                if isinstance(flags, dict):
                    detail["flags"] = flags
            except Exception:
                pass
        raise HTTPException(status_code=400, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"fetch error: {e}")

    # force source to string for schema
    for a in articles:
        src = a.get("source")
        if isinstance(src, dict):
            a["source"] = src.get("name", "")
        elif src is None:
            a["source"] = ""
        else:
            a["source"] = str(src)

    default_summary: Dict[str, Any] = {
        "summary": f"{len(articles)} articles found for '{query}'.",
        "highlights": [a["title"] for a in articles[:5]],
        "top": [{"title": a["title"], "link": a["link"]} for a in articles[:5]],
    }

    if rag_generate:
        try:
            s = rag_generate(articles, prefs, query, user_id=resolved_user_id)
            if not isinstance(s, dict):
                s = default_summary
            else:
                s.setdefault("summary", default_summary["summary"])
                s.setdefault("highlights", [])
                s.setdefault("top", [])
        except Exception:
            s = default_summary
    else:
        s = default_summary

    # app/main.py, right before `return {"articles": articles, "summary": s}`
    s["summary"] = s.get("summary", "")
    s["summary"] += f" (region={region}, lang={lang}, timeframe={timeframe}, sort={sort})"
    return {"articles": articles, "summary": s}

    print(s)
    return {"articles": articles, "summary": s}


@app.post("/summarize_batch")
def summarize_batch(payload: SummBatchIn, user_id: int = 0):
    items = [i.model_dump() for i in payload.items if i.link]
    if not items:
        return {"summaries": {}}

    # Prefer your RAG/LLM if available; graceful fallback otherwise
    summaries: dict[str, str] = {}
    if rag_generate:
        try:
            from .rag import summarize_articles  # new helper (see rag.py below)
            summaries = summarize_articles(items, user_id=user_id)
        except Exception:
            summaries = {i["link"]: (i.get("snippet") or i.get("title") or "") for i in items}
    else:
        summaries = {i["link"]: (i.get("snippet") or i.get("title") or "") for i in items}

    return {"summaries": summaries}
