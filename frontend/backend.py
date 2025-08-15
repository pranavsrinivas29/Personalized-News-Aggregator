from __future__ import annotations
import requests
from typing import Tuple, Optional, Dict, Any

# Import shim: prefer package imports, fallback to local
try:
    from frontend.settings import BACKEND_URL, REQUEST_TIMEOUT
except Exception:  # running as script
    from settings import BACKEND_URL, REQUEST_TIMEOUT

def get_news(query: str, user_id: int) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], int]:
    """
    Returns (data, blocked_detail, status_code)
      - data: dict with {"summary": ..., "articles": ...} when OK
      - blocked_detail: dict like {"blocked": True, "message": "...", "flags": {...}} when 400
      - status_code: HTTP status
    """
    resp = requests.get(
        f"{BACKEND_URL}/get_news",
        params={"query": query, "user_id": user_id, "prefs": ""},
        timeout=REQUEST_TIMEOUT,
    )
    status = resp.status_code

    if status == 400:
        try:
            detail = resp.json().get("detail")
        except Exception:
            detail = {"blocked": True, "message": "Query blocked."}
        return None, (detail if isinstance(detail, dict) else None), status

    resp.raise_for_status()
    return resp.json(), None, status
