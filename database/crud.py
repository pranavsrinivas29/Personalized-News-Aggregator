# database/crud.py
from __future__ import annotations
from typing import List, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session
from .models import SearchEvent

def add_search_event(db: Session, user_id: int, query: str) -> None:
    db.add(SearchEvent(user_id=user_id, query=query.strip()[:256]))
    db.commit()

def get_user_recent_queries(db: Session, user_id: int, limit: int = 20) -> List[str]:
    q = (
        select(SearchEvent.query)
        .where(SearchEvent.user_id == user_id)
        .order_by(desc(SearchEvent.created_at))
        .limit(limit)
    )
    rows = db.execute(q).all()
    return [r[0] for r in rows]

def get_trending_queries(db: Session, days: int = 30, limit: int = 25) -> List[Tuple[str,int]]:
    cutoff = datetime.utcnow() - timedelta(days=days)
    q = (
        select(SearchEvent.query, func.count().label("c"))
        .where(SearchEvent.created_at >= cutoff)
        .group_by(SearchEvent.query)
        .order_by(desc("c"))
        .limit(limit)
    )
    rows = db.execute(q).all()
    return [(r[0], r[1]) for r in rows]
