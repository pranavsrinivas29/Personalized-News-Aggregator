# app/news_fetcher.py
from __future__ import annotations
import requests, feedparser, re
from typing import List, Dict, Any
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from datetime import datetime, timezone, timedelta
import config
from .content_safety import moderate_text
from .ranker import rank_articles

REGION_META = {
    "us": {"google_domain": "google.com",   "location": "United States",     "lang": "en"},
    "gb": {"google_domain": "google.co.uk", "location": "United Kingdom",    "lang": "en"},
    "de": {"google_domain": "google.de",    "location": "Germany",           "lang": "de"},
    "fr": {"google_domain": "google.fr",    "location": "France",            "lang": "fr"},
    "es": {"google_domain": "google.es",    "location": "Spain",             "lang": "es"},
    "in": {"google_domain": "google.co.in", "location": "India",             "lang": "en"},
}

# ---------- URL normalization / dedupe ----------
def _normalize_url(url: str) -> str:
    try:
        u = urlparse(url)
        # strip tracking query params
        q = [(k, v) for (k, v) in parse_qsl(u.query, keep_blank_values=False)
             if not k.lower().startswith(("utm_", "fbclid", "gclid", "mc_cid", "mc_eid"))]
        return urlunparse((u.scheme, u.netloc.lower(), u.path, "", urlencode(q), ""))
    except Exception:
        return url

def _dedupe(articles: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for a in articles:
        link = a.get("link") or ""
        k = _normalize_url(link)
        if k and k not in seen:
            seen.add(k)
            out.append(a)
    return out

# ---------- Date parsing ----------
_REL_RE = re.compile(r"(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago", re.I)

def _to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _parse_serp_date(s: str | None) -> str | None:
    # SerpAPI date often like "2 hours ago" or "Aug 14, 2025"
    if not s:
        return None
    s = s.strip()
    m = _REL_RE.search(s)
    if m:
        n = int(m.group(1))
        unit = m.group(2).lower()
        delta = {
            "minute": timedelta(minutes=n),
            "hour": timedelta(hours=n),
            "day": timedelta(days=n),
            "week": timedelta(weeks=n),
            "month": timedelta(days=30*n),
            "year": timedelta(days=365*n),
        }.get(unit, timedelta())
        return _to_iso(datetime.now(timezone.utc) - delta)
    # try absolute formats that Google returns
    try:
        return _to_iso(datetime.strptime(s, "%b %d, %Y").replace(tzinfo=timezone.utc))
    except Exception:
        return None

# ---------- SerpAPI: Google News ----------
def fetch_from_serpapi_news(
    query: str,
    *,
    lang: str = "en",
    region: str = "us",
    timeframe: str = "7d",
    sort: str = "date"
) -> List[Dict[str, Any]]:
    if not config.SERPAPI_KEY:
        return []

    meta = REGION_META.get(region.lower(), REGION_META["us"])
    google_domain = meta["google_domain"]
    location_str  = meta["location"]
    # If caller didn't pass lang explicitly, default to region default
    lang = (lang or meta["lang"]).lower()

    # Build tbs with recency + language restriction (lr:lang_1xx)
    # lr codes: en→lang_1en, de→lang_1de, fr→lang_1fr, es→lang_1es
    lang_code = f"lr:lang_1{lang.lower()}"
    tbs_parts = [lang_code]
    if timeframe:
        unit = timeframe[-1].lower(); qty = timeframe[:-1]
        if unit in {"h","d","w","m","y"} and qty.isdigit():
            tbs_parts.append(f"qdr:{unit}")
    if sort == "date":
        tbs_parts.append("sbd:1")
    tbs = ",".join(tbs_parts)

    params = {
        "engine": "google",
        "tbm": "nws",
        "q": query,
        "api_key": config.SERPAPI_KEY,
        "google_domain": google_domain,
        "location": location_str,   # stronger geo
        "hl": lang,                 # UI language
        "gl": region.lower(),       # country hint
        "tbs": tbs,                 # language + recency + sort
        "num": 20,
        "no_cache": True,           # avoid SerpAPI cache
    }

    r = requests.get("https://serpapi.com/search.json", params=params, timeout=60)
    r.raise_for_status()
    data = r.json()

    out: List[Dict[str, Any]] = []
    for it in data.get("news_results", []) or []:
        out.append({
            "title": it.get("title", ""),
            "link": it.get("link", "") or (it.get("source", {}) or {}).get("link", ""),
            "snippet": it.get("snippet", "") or it.get("summary", ""),
            "source": (it.get("source", "") or it.get("publisher", "")) or "",
            "published_at": _parse_serp_date(it.get("date")),
        })

    for it in data.get("top_stories", []) or []:
        out.append({
            "title": it.get("title", ""),
            "link": it.get("link", ""),
            "snippet": it.get("snippet", ""),
            "source": it.get("source", ""),
            "published_at": _parse_serp_date(it.get("date")),
        })

    for it in data.get("organic_results", []) or []:
        if it.get("title") and it.get("link"):
            out.append({
                "title": it.get("title", ""),
                "link": it.get("link", ""),
                "snippet": it.get("snippet", ""),
                "source": it.get("source", "") or ((it.get("rich_snippet", {}) or {}).get("top", {}) or {}).get("name", ""),
                "published_at": None,
            })

    out = [a for a in out if a.get("title") and a.get("link")]
    return _dedupe(out)


# ---------- RSS fallback (free) ----------
DEFAULT_RSS = [
    "https://rss.cnn.com/rss/edition.rss",
    "https://feeds.reuters.com/reuters/topNews",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.theverge.com/rss/index.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
]
REGION_RSS: dict[str, list[str]] = {
    "us": [
        "https://feeds.reuters.com/reuters/topNews",
        "https://rss.cnn.com/rss/edition.rss",
        "https://www.npr.org/rss/rss.php?id=1001",
        "https://feeds.foxnews.com/foxnews/latest",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.theverge.com/rss/index.xml",
    ],
    "gb": [
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://www.theguardian.com/uk/rss",
        "https://www.ft.com/rss/home",
        "https://www.telegraph.co.uk/news/rss.xml",
    ],
    "de": [
        "https://www.dw.com/atom/rss-en-top",
        "https://www.spiegel.de/international/index.rss",
        "https://www.tagesschau.de/xml/rss2",
        "https://www.handelsblatt.com/contentexport/feed/home",
    ],
    "fr": [
        "https://www.lemonde.fr/rss/une.xml",
        "https://www.lefigaro.fr/rss/figaro_actualites.xml",
        "https://www.france24.com/fr/rss",
    ],
    "es": [
        "https://elpais.com/feed/",
        "https://www.eldiario.es/rss/",
        "https://www.elmundo.es/rss/portada.xml",
    ],
    "in": [
        "https://feeds.feedburner.com/ndtvnews-top-stories",
        "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
        "https://indianexpress.com/section/india/feed/",
        "https://www.thehindu.com/news/feeder/default.rss",
    ],
}
def fetch_from_rss(query: str, region: str | None = None) -> List[Dict[str, Any]]:
    q = (query or "").lower()
    feeds = REGION_RSS.get((region or "").lower(), DEFAULT_RSS)

    out: List[Dict[str, Any]] = []
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries:
                title = getattr(e, "title", "") or ""
                link = getattr(e, "link", "") or ""
                summ = getattr(e, "summary", "") or ""
                text = f"{title}\n{summ}".lower()
                # Loose match: prefer titles that contain the query, else include if snippet matches
                if (q and (q in title.lower() or q in summ.lower())) or not q:
                    # Try published date
                    published_at = None
                    if getattr(e, "published_parsed", None):
                        try:
                            dt = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
                            published_at = dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")
                        except Exception:
                            pass
                    out.append({
                        "title": title,
                        "link": link,
                        "snippet": summ,
                        "source": feed.feed.get("title", ""),
                        "published_at": published_at,
                    })
        except Exception:
            continue
    return _dedupe(out)

# ---------- Public entry ----------
def fetch_news_from_sources(
    query: str,
    *,
    lang: str = "en",
    region: str = "us",
    timeframe: str = "7d",
    sort: str = "date",
    limit: int = 50
) -> List[Dict[str, Any]]:
    safe, scores, flags = moderate_text(query)
    if not safe:
        raise ValueError(f"blocked by safety: {flags}")

    serp = fetch_from_serpapi_news(query, lang=lang, region=region, timeframe=timeframe, sort=sort)
    rss  = fetch_from_rss(query, region=region)   # <-- region-aware now

    combined = _dedupe(serp + rss)
    ranked = rank_articles(query, combined, use_embeddings=True)
    if limit and limit > 0:
        ranked = ranked[:limit]
    for a in ranked:
        a.setdefault("snippet", "")
        a.setdefault("source", "")
        a.setdefault("published_at", None)
    return ranked
