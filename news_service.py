"""
Optional "industry news / awards" feed for the daily digest, via NewsAPI.org.
If NEWSAPI_KEY isn't set, this quietly returns an empty list — the rest of
the daily digest (trending movies/tv/manga) still works fine without it.
"""
import aiohttp
from config import NEWSAPI_KEY, REQUEST_TIMEOUT

BASE_URL = "https://newsapi.org/v2/everything"

QUERY = (
    '("box office" OR "streaming release" OR "manga chapter" OR '
    '"light novel" OR "book award" OR "film award" OR "Emmy" OR "Oscar")'
)


async def get_industry_news(limit: int = 5) -> list[dict]:
    if not NEWSAPI_KEY:
        return []

    params = {
        "q": QUERY,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": limit,
        "apiKey": NEWSAPI_KEY,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                BASE_URL, params=params,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
    except Exception:
        return []

    return [
        {"title": a.get("title"), "url": a.get("url"), "source": a.get("source", {}).get("name")}
        for a in data.get("articles", [])[:limit]
    ]
