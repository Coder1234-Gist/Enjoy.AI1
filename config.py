"""
Central configuration. All secrets are loaded from environment variables
(via a .env file in development). Never hardcode tokens/keys here.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Required ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# --- Recommendation data sources ---
# TMDb: https://www.themoviedb.org/settings/api  (free)
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")

# Jikan (unofficial MyAnimeList API) needs NO key: https://jikan.moe/
JIKAN_BASE_URL = "https://api.jikan.moe/v4"

# Google Books needs no key for basic search, but one raises your rate limit:
# https://console.cloud.google.com/apis/credentials
GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY", "")

# --- Optional: daily "industry news" digest ---
# https://newsapi.org/ (free tier). If unset, the news section is skipped.
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

# --- Daily notification time (24h, server-local time, "HH:MM") ---
DAILY_NOTIFICATION_TIME = os.getenv("DAILY_NOTIFICATION_TIME", "09:00")

# --- Misc ---
DB_PATH = os.getenv("DB_PATH", "bot_data.db")
REQUEST_TIMEOUT = 10  # seconds, for all outbound API calls

TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w342"

if not BOT_TOKEN:
    # Only warn at import time; main.py will hard-fail on run if missing.
    print("[config] WARNING: BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")
