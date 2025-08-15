# app/suggest_routes.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
import random

from fastapi import APIRouter, Depends, Query, Header
from sqlalchemy.orm import Session

from database.db import SessionLocal
from database import crud
from .auth import decode_token  # optional auth via bearer

router = APIRouter(prefix="/suggest", tags=["suggestions"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DEFAULT_TRENDING = [
    "AI", "Startups", "US Elections", "Stocks", "Bitcoin", "Sports",
    "Climate", "Space", "Movies", "Football", "Cricket",
]

@router.post("/track")
def track_search(
    user_id: int = Query(..., ge=1),
    query: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    crud.add_search_event(db, user_id=user_id, query=query)
    return {"ok": True}

@router.get("/topics")
def suggest_topics(
    user_id: int = Query(..., ge=1),
    k: int = Query(3, ge=1, le=10),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    # Optional auth (ignore errors)
    if authorization and authorization.lower().startswith("bearer "):
        try:
            _ = decode_token(authorization.split(" ", 1)[1].strip())
        except Exception:
            pass

    user_recent = crud.get_user_recent_queries(db, user_id=user_id, limit=50)
    topics: List[str] = []

    if user_recent:
        # frequency-based personalization
        counts: Dict[str, int] = {}
        for q in user_recent:
            key = q.strip().title()
            if key:
                counts[key] = counts.get(key, 0) + 1
        topics = [t for t, _ in sorted(counts.items(), key=lambda x: x[1], reverse=True)]
    else:
        # new user → trending (randomized so it feels fresh)
        trending = [t for t, _ in crud.get_trending_queries(db, days=30, limit=25)]
        pool = trending or DEFAULT_TRENDING
        random.shuffle(pool)
        topics = pool

    # unique + take top-k
    out, seen = [], set()
    for t in topics:
        key = t.lower().replace(" ", "")
        if key not in seen:
            seen.add(key)
            out.append(t)
        if len(out) >= k:
            break

    return {"topics": out}
