# app/auth_routes.py
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import User
from .schemas import UserCreate, UserLogin, TokenOut
from .auth import hash_password, verify_password, create_token
from app.rag import generate_news_response

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=TokenOut)
def register(body: UserCreate, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_token(user.id)
    return {"user_id": user.id, "token": token}

@router.post("/login", response_model=TokenOut)
def login(body: UserLogin, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user.id)
    return {"user_id": user.id, "token": token}

@router.post("/summarize")
async def summarize_articles(payload: dict = Body(...)):
    articles = payload.get("articles", [])
    user_id = payload.get("user_id", 0)
    query = articles[0].get("title", "") if articles else ""

    response = generate_news_response(articles, user_preferences="", query=query, user_id=user_id)

    # Map summaries to links
    summaries = {}
    for top in response.get("top", []):
        summaries[top["link"]] = top["title"] + " — " + response.get("summary", "")

    return {"summaries": summaries}