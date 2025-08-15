# database/models.py
from __future__ import annotations
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from .db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class SearchEvent(Base):
    __tablename__ = "search_events"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    query = Column(String(256), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)