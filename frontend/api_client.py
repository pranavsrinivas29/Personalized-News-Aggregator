# frontend/api_client.py
import requests
import settings  # same folder as app.py

BACKEND_URL = settings.BACKEND_URL

def get_news(query: str, user_id: int, token: str | None = None,
             page: int = 1, page_size: int = 10,
             region: str | None = None, lang: str | None = None,
             timeframe: str | None = None, sort: str | None = None) -> dict:

    params = {
        "query": query,
        "user_id": user_id,
        "page": page,
        "page_size": page_size,
    }
    if region:    params["region"] = region
    if lang:      params["lang"] = lang
    if timeframe: params["timeframe"] = timeframe
    if sort:      params["sort"] = sort

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    r = requests.get(f"{BACKEND_URL}/get_news", params=params, headers=headers, timeout=60)
    r.raise_for_status()
    return r.json()

def track_search(user_id: int, query: str, token: str | None = None) -> None:
    params = {"user_id": user_id, "query": query}
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.post(f"{BACKEND_URL}/suggest/track", params=params, headers=headers, timeout=30)
    r.raise_for_status()

def get_personal_topics(user_id: int, k: int = 3, token: str | None = None) -> list[str]:
    params = {"user_id": user_id, "k": k}
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(f"{BACKEND_URL}/suggest/topics", params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json().get("topics", [])


def summarize_batch(articles, user_id, token=None):
    url = f"{BACKEND_URL}/summarize"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = requests.post(url, json={"articles": articles, "user_id": user_id}, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json().get("summaries", {})  # Expected: {link: summary}
