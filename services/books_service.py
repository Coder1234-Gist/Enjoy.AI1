"""
Google Books integration — covers Novels.
Docs: https://developers.google.com/books/docs/v1/using

Google Books search can't sort server-side by rating, and ratings are
sparse, so we over-fetch a batch and sort client-side, falling back to
relevance order when nothing has a rating yet.
"""
import aiohttp
from config import GOOGLE_BOOKS_API_KEY, REQUEST_TIMEOUT

BASE_URL = "https://www.googleapis.com/books/v1/volumes"


async def discover(genre_keyword: str | None, year: int | None, limit: int) -> list[dict]:
    query_parts = []
    if genre_keyword:
        query_parts.append(f"subject:{genre_keyword}")
    else:
        query_parts.append("subject:fiction")
    q = "+".join(query_parts)

    params = {"q": q, "maxResults": 40, "printType": "books", "langRestrict": "en"}
    if year:
        params["q"] += f"+publishedDate:{year}"
    if GOOGLE_BOOKS_API_KEY:
        params["key"] = GOOGLE_BOOKS_API_KEY

    async with aiohttp.ClientSession() as session:
        async with session.get(
            BASE_URL, params=params,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

    items = data.get("items", [])

    def score(it):
        info = it.get("volumeInfo", {})
        return (info.get("averageRating", 0), info.get("ratingsCount", 0))

    items.sort(key=score, reverse=True)

    results = []
    for it in items[:limit]:
        info = it.get("volumeInfo", {})
        published = info.get("publishedDate", "")
        authors = ", ".join(info.get("authors", [])) or "Unknown author"
        results.append({
            "source": "google_books",
            "kind": "book",
            "id": it.get("id"),
            "title": info.get("title", "Untitled"),
            "rating": info.get("averageRating", "N/A"),
            "year": published[:4] if published else "N/A",
            "poster": info.get("imageLinks", {}).get("thumbnail"),
            "overview": info.get("description", "No summary available.")[:600],
            "authors": authors,
        })
    return results


async def get_details(volume_id: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/{volume_id}",
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

    info = data.get("volumeInfo", {})
    return {
        "title": info.get("title"),
        "overview": info.get("description", "No summary available."),
        "genres": info.get("categories", []),
        "authors": info.get("authors", []),
        "rating": info.get("averageRating", "N/A"),
        "popularity": info.get("ratingsCount"),
        "poster": info.get("imageLinks", {}).get("thumbnail"),
    }
