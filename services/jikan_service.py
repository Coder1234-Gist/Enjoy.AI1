"""
Jikan (unofficial MyAnimeList API) integration — covers Light Novels and Manga.
No API key required. Docs: https://docs.api.jikan.moe/

Rate limit is strict (~3 req/sec, 60/min) — we keep calls minimal and
avoid hammering it in a loop.
"""
import asyncio
import aiohttp
from config import JIKAN_BASE_URL, REQUEST_TIMEOUT

# MAL "type" filter on the /manga endpoint distinguishes manga from light novels.
TYPE_MAP = {
    "Manga": "manga",
    "Light Novels": "lightnovel",
}


async def _get(session: aiohttp.ClientSession, path: str, params: dict) -> dict:
    async with session.get(
        f"{JIKAN_BASE_URL}{path}", params=params,
        timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
    ) as resp:
        resp.raise_for_status()
        return await resp.json()


async def discover(category: str, genre_id: int | None, year: int | None, limit: int) -> list[dict]:
    mal_type = TYPE_MAP.get(category, "manga")
    params = {
        "type": mal_type,
        "order_by": "score",
        "sort": "desc",
        "limit": limit,
    }
    if genre_id:
        params["genres"] = genre_id
    if year:
        # Jikan supports a date range filter
        params["start_date"] = f"{year}-01-01"
        params["end_date"] = f"{year}-12-31"

    async with aiohttp.ClientSession() as session:
        data = await _get(session, "/manga", params)

    results = []
    for item in data.get("data", [])[:limit]:
        published = item.get("published", {}).get("from") or ""
        results.append({
            "source": "jikan",
            "kind": mal_type,
            "id": item["mal_id"],
            "title": item.get("title"),
            "rating": item.get("score") or "N/A",
            "year": published[:4] if published else "N/A",
            "poster": (item.get("images", {}).get("jpg", {}) or {}).get("image_url"),
            "overview": (item.get("synopsis") or "No summary available.")[:600],
        })
    return results


async def get_details(mal_id: int) -> dict:
    async with aiohttp.ClientSession() as session:
        data = await _get(session, f"/manga/{mal_id}/full", {})
    d = data.get("data", {})
    authors = [a["name"] for a in d.get("authors", [])]
    genres = [g["name"] for g in d.get("genres", [])]
    return {
        "title": d.get("title"),
        "overview": d.get("synopsis") or "No summary available.",
        "genres": genres,
        "authors": authors,
        "rating": d.get("score") or "N/A",
        "popularity": d.get("popularity"),
        "poster": (d.get("images", {}).get("jpg", {}) or {}).get("image_url"),
    }


async def top(mal_type: str, limit: int = 3) -> list[dict]:
    """Used by the daily digest (top-ranked manga or light novels right now)."""
    async with aiohttp.ClientSession() as session:
        data = await _get(session, "/top/manga", {"type": mal_type, "limit": limit})
    return [{"title": i.get("title"), "rating": i.get("score") or "N/A"}
            for i in data.get("data", [])[:limit]]
