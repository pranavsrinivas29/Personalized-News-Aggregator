from __future__ import annotations
import requests
from typing import Tuple, Optional, Dict, Any
from settings import BACKEND_URL, REQUEST_TIMEOUT

def register(email: str, password: str) -> Tuple[Optional[Dict[str, Any]], int, Optional[str]]:
    try:
        r = requests.post(
            f"{BACKEND_URL}/auth/register",
            json={"email": email, "password": password},
            timeout=REQUEST_TIMEOUT,
        )
        if r.status_code >= 400:
            detail = None
            try:
                detail = r.json().get("detail")
            except Exception:
                pass
            return None, r.status_code, detail or "Registration failed"
        return r.json(), r.status_code, None
    except Exception as e:
        return None, 0, str(e)

def login(email: str, password: str) -> Tuple[Optional[Dict[str, Any]], int, Optional[str]]:
    try:
        r = requests.post(
            f"{BACKEND_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=REQUEST_TIMEOUT,
        )
        if r.status_code >= 400:
            detail = None
            try:
                detail = r.json().get("detail")
            except Exception:
                pass
            return None, r.status_code, detail or "Login failed"
        return r.json(), r.status_code, None
    except Exception as e:
        return None, 0, str(e)
