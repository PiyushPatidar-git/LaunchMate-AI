"""Tavily web search (official API). Only real responses mark LIVE SEARCH."""
from datetime import datetime
import httpx
from ..config import settings

state = {"live_ok_at": None, "last_error": ""}

class SearchUnavailable(Exception):
    pass

def configured() -> bool:
    return bool(settings.tavily_key)

def search(query: str, max_results: int = 8) -> list[dict]:
    if not configured():
        raise SearchUnavailable("TAVILY_API_KEY is not set.")
    try:
        r = httpx.post("https://api.tavily.com/search", timeout=settings.timeout,
                       headers={"Authorization": f"Bearer {settings.tavily_key}"},
                       json={"query": query, "max_results": max_results, "search_depth": "basic"})
        if r.status_code in (401, 403):
            raise SearchUnavailable("Tavily rejected the API key (HTTP %d)." % r.status_code)
        r.raise_for_status()
        results = r.json().get("results", [])
    except SearchUnavailable as e:
        state["last_error"] = str(e)
        raise
    except Exception as e:
        state["last_error"] = type(e).__name__
        raise SearchUnavailable(f"Web search failed ({type(e).__name__}). Check your connection and TAVILY_API_KEY.") from e
    state.update(live_ok_at=datetime.utcnow().isoformat(timespec="seconds"), last_error="")
    return [{"title": x.get("title") or x.get("url", ""), "url": x["url"], "snippet": (x.get("content") or "")[:600],
             "published": (x.get("published_date") or "")[:10]} for x in results if x.get("url", "").startswith("http")]

DEMO = [
    {"title": "Sample Hackathon: Campus AI Builders", "url": "https://example.com/demo/campus-ai-builders",
     "snippet": "DEMO DATA. Illustrative hackathon for students building AI agents with Python and FastAPI."},
    {"title": "Sample Internship: Junior Backend Developer", "url": "https://example.com/demo/junior-backend",
     "snippet": "DEMO DATA. Illustrative internship using Python, SQL and REST APIs."},
    {"title": "Sample Scholarship: Women in Computing Grant", "url": "https://example.com/demo/computing-grant",
     "snippet": "DEMO DATA. Illustrative scholarship for early-career developers; eligibility is fictional."},
]
