"""
TMDb (themoviedb.org) integration — covers Movies and Web Series (TV).
Docs: https://developer.themoviedb.org/reference/intro/getting-started
"""
import aiohttp
from config import TMDB_API_KEY, REQUEST_TIMEOUT, TMDB_IMAGE_BASE

BASE_URL = "https://api.themoviedb.org/3"


async def _get(session: aiohttp.ClientSession, path: str, params: dict) -> dict:
    params = {**params, "api_key": TMDB_API_KEY}
    async with session.get(
        f"{BASE_URL}{path}", params=params,
        timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
    ) as resp:
        resp.raise_for_status()
        return await resp.json()


def _poster_url(path: str | None) -> str | None:
    return f"{TMDB_IMAGE_BASE}{path}" if path else None


async def discover(kind: str, genre_id: int | None, year: int | None, limit: int) -> list[dict]:
    """
    kind: "movie" or "tv"
    Returns a normalized list of dicts, best-rated first, capped at `limit`.
    """
    params = {
        "sort_by": "vote_average.desc",
        "vote_count.gte": 100,   # filter out obscure/zero-review entries
        "page": 1,
    }
    if genre_id:
        params["with_genres"] = genre_id
    if year:
        params["primary_release_year" if kind == "movie" else "first_air_date_year"] = year

    async with aiohttp.ClientSession() as session:
        data = await _get(session, f"/discover/{kind}", params)

    results = []
    for item in data.get("results", [])[:limit]:
        title = item.get("title") or item.get("name")
        date = item.get("release_date") or item.get("first_air_date") or ""
        results.append({
            "source": "tmdb",
            "kind": kind,
            "id": item["id"],
            "title": title,
            "rating": round(item.get("vote_average", 0), 1),
            "year": date[:4] if date else "N/A",
            "poster": _poster_url(item.get("poster_path")),
            "overview": item.get("overview") or "No summary available.",
        })
    return results


async def get_details(kind: str, item_id: int) -> dict:
    async with aiohttp.ClientSession() as session:
        data = await _get(session, f"/{kind}/{item_id}", {"append_to_response": "credits"})

    cast = [c["name"] for c in data.get("credits", {}).get("cast", [])[:5]]
    genres = [g["name"] for g in data.get("genres", [])]
    return {
        "title": data.get("title") or data.get("name"),
        "overview": data.get("overview") or "No summary available.",
        "genres": genres,
        "cast": cast,
        "rating": round(data.get("vote_average", 0), 1),
        "popularity": data.get("popularity"),
        "poster": _poster_url(data.get("poster_path")),
    }


async def trending(kind: str, limit: int = 3) -> list[dict]:
    """Used by the daily digest. kind: 'movie' or 'tv'."""
    async with aiohttp.ClientSession() as session:
        data = await _get(session, f"/trending/{kind}/day", {})
    out = []
    for item in data.get("results", [])[:limit]:
        out.append({
            "title": item.get("title") or item.get("name"),
            "rating": round(item.get("vote_average", 0), 1),
        })
    return out
