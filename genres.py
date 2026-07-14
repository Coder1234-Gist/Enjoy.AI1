"""
Genre + category definitions for every content type.

Each API has a different genre taxonomy, so we keep one map per category.
Keys are the labels shown to the user; values are what gets sent to the
underlying API (a TMDb/MAL genre id, or a plain search keyword for Books).
"""

CATEGORIES = ["Movies", "Web Series", "Novels", "Light Novels", "Manga"]

# TMDb genre ids — movies
GENRES_MOVIES = {
    "Action": 28, "Adventure": 12, "Animation": 16, "Comedy": 35,
    "Crime": 80, "Documentary": 99, "Drama": 18, "Family": 10751,
    "Fantasy": 14, "History": 36, "Horror": 27, "Mystery": 9648,
    "Romance": 10749, "Sci-Fi": 878, "Thriller": 53, "War": 10752,
}

# TMDb genre ids — tv (slightly different taxonomy from movies)
GENRES_WEB_SERIES = {
    "Action & Adventure": 10759, "Animation": 16, "Comedy": 35,
    "Crime": 80, "Documentary": 99, "Drama": 18, "Family": 10751,
    "Kids": 10762, "Mystery": 9648, "Reality": 10764,
    "Sci-Fi & Fantasy": 10765, "War & Politics": 10768,
}

# Google Books has no genre ids — we just search by subject keyword.
GENRES_NOVELS = {
    "Fiction": "fiction", "Romance": "romance", "Fantasy": "fantasy",
    "Mystery": "mystery", "Thriller": "thriller", "Sci-Fi": "science fiction",
    "Horror": "horror", "Historical": "historical fiction",
    "Young Adult": "young adult", "Biography": "biography",
    "Classics": "classics",
}

# Jikan/MAL genre ids — shared vocabulary for light novels & manga
GENRES_MAL = {
    "Action": 1, "Adventure": 2, "Comedy": 4, "Drama": 8,
    "Fantasy": 10, "Horror": 14, "Mystery": 7, "Romance": 22,
    "Sci-Fi": 24, "Slice of Life": 36, "Sports": 30,
    "Supernatural": 37, "Thriller": 41,
}

GENRE_MAP = {
    "Movies": GENRES_MOVIES,
    "Web Series": GENRES_WEB_SERIES,
    "Novels": GENRES_NOVELS,
    "Light Novels": GENRES_MAL,
    "Manga": GENRES_MAL,
}


def genres_for(category: str) -> dict:
    return GENRE_MAP.get(category, {})
