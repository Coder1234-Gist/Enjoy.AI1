"""
Sends a daily digest (trending movies/tv, top manga & light novels, and
optional industry news) to every subscribed user via PTB's JobQueue.

Requires: pip install "python-telegram-bot[job-queue]"
"""
import logging
import datetime as dt
from telegram.ext import ContextTypes

import database
from config import DAILY_NOTIFICATION_TIME
from services import tmdb_service, jikan_service, news_service

logger = logging.getLogger(__name__)


async def _build_digest_text() -> str:
    lines = ["*Your Daily Digest*", ""]

    try:
        movies = await tmdb_service.trending("movie", 3)
        if movies:
            lines.append("*Trending Movies*")
            lines += [f"- {m['title']} ({m['rating']}/10)" for m in movies]
            lines.append("")
    except Exception:
        logger.exception("Failed to fetch trending movies for digest")

    try:
        tv = await tmdb_service.trending("tv", 3)
        if tv:
            lines.append("*Trending Web Series*")
            lines += [f"- {t['title']} ({t['rating']}/10)" for t in tv]
            lines.append("")
    except Exception:
        logger.exception("Failed to fetch trending tv for digest")

    try:
        manga = await jikan_service.top("manga", 3)
        if manga:
            lines.append("*Top Manga Right Now*")
            lines += [f"- {m['title']} ({m['rating']})" for m in manga]
            lines.append("")
    except Exception:
        logger.exception("Failed to fetch top manga for digest")

    try:
        novels = await jikan_service.top("lightnovel", 3)
        if novels:
            lines.append("*Top Light Novels Right Now*")
            lines += [f"- {n['title']} ({n['rating']})" for n in novels]
            lines.append("")
    except Exception:
        logger.exception("Failed to fetch top light novels for digest")

    try:
        news = await news_service.get_industry_news(3)
        if news:
            lines.append("*Industry News*")
            lines += [f"- {n['title']} ({n['source']})" for n in news]
            lines.append("")
    except Exception:
        logger.exception("Failed to fetch industry news for digest")

    if len(lines) <= 2:
        return ""  # nothing fetched successfully, skip sending
    return "\n".join(lines)


async def send_daily_digest(context: ContextTypes.DEFAULT_TYPE):
    user_ids = database.get_subscribed_user_ids()
    if not user_ids:
        return

    text = await _build_digest_text()
    if not text:
        logger.warning("Digest was empty (all sources failed); skipping send.")
        return

    for user_id in user_ids:
        try:
            await context.bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown")
        except Exception:
            logger.warning("Could not deliver digest to user %s (may have blocked the bot)", user_id)


def schedule_daily_job(job_queue):
    hour, minute = (int(p) for p in DAILY_NOTIFICATION_TIME.split(":"))
    job_queue.run_daily(
        send_daily_digest,
        time=dt.time(hour=hour, minute=minute),
        name="daily_digest",
    )
    logger.info("Daily digest scheduled for %02d:%02d server time", hour, minute)
