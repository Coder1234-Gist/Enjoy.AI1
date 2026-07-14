"""
Standalone diagnostic — tests connectivity to each data source independently
and prints the exact error (if any) instead of a generic fallback message.
Run with: python test_connectivity.py
"""
import asyncio
import aiohttp

URLS = [
    ("TMDb", "https://api.themoviedb.org/3/discover/movie?api_key=test"),
    ("Jikan (MyAnimeList)", "https://api.jikan.moe/v4/manga?limit=1"),
    ("Google Books", "https://www.googleapis.com/books/v1/volumes?q=fiction"),
]


async def test():
    async with aiohttp.ClientSession() as session:
        for name, url in URLS:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    print(f"[OK]    {name}: HTTP {resp.status}")
            except Exception as e:
                print(f"[FAIL]  {name}: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(test())
