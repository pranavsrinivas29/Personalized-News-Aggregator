# app/auth.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

import jwt
from passlib.context import CryptContext

import config

# Password hashing context (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Return a bcrypt hash for the given plaintext password."""
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plaintext password against a bcrypt hash."""
    return pwd_context.verify(password, password_hash)


def create_token(
    user_id: int,
    *,
    expires_minutes: Optional[int] = None,
    extra_claims: Optional[Dict] = None,
) -> str:
    """
    Create a signed JWT for the given user_id.

    Args:
        user_id: The user's DB id.
        expires_minutes: Override token lifetime. Defaults to config.ACCESS_TOKEN_EXPIRE_MINUTES.
        extra_claims: Optional extra claims to include in the payload.

    Returns:
        Encoded JWT string.
    """
    exp_minutes = (
        int(expires_minutes)
        if expires_minutes is not None
        else int(config.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    now = datetime.now(timezone.utc)
    payload: Dict = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=exp_minutes)).timestamp()),
        "typ": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, config.SECRET_KEY, algorithm=ALGORITHM)
    # PyJWT returns str on PyJWT>=2, bytes on very old versions; normalize to str
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def decode_token(token: str) -> int:
    """
    Decode and validate a JWT. Returns the user_id (int) on success.

    Raises:
        jwt.ExpiredSignatureError, jwt.InvalidTokenError on invalid tokens.
    """
    data = jwt.decode(token, config.SECRET_KEY, algorithms=[ALGORITHM])
    return int(data["sub"])


def user_id_from_authorization_header(authorization: Optional[str]) -> Optional[int]:
    """
    Utility to extract user_id from a typical 'Authorization: Bearer <token>' header.
    Returns None if header is missing/invalid/expired.
    """
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1]
    try:
        return decode_token(token)
    except Exception:
        return None


def make_auth_headers(token: str) -> Dict[str, str]:
    """Convenience for client code to set the Authorization header."""
    return {"Authorization": f"Bearer {token}"}
