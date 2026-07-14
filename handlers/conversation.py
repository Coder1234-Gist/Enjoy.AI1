"""
The core recommendation wizard, implemented as a python-telegram-bot
ConversationHandler. States flow linearly but every step has a "Back"
button, and results/details are revisitable without losing your place.
"""
import logging
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters,
)

import database
from genres import genres_for
from keyboards import (
    category_keyboard, genre_keyboard, year_mode_keyboard, year_keyboard,
    count_keyboard, results_keyboard, detail_keyboard,
)
from services import tmdb_service, jikan_service, books_service

logger = logging.getLogger(__name__)

CATEGORY, GENRE, YEAR_MODE, YEAR, YEAR_CUSTOM, COUNT, RESULTS = range(7)

WELCOME = (
    "Hi! I'll help you find something great to watch or read.\n\n"
    "Pick a category to get started:"
)


# ---------- entry points ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    database.upsert_user(user.id, user.username, user.first_name)
    context.user_data.clear()
    await update.message.reply_text(WELCOME, reply_markup=category_keyboard())
    return CATEGORY


async def restart_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.callback_query.edit_message_text(WELCOME, reply_markup=category_keyboard())
    return CATEGORY


# ---------- step handlers ----------

async def choose_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    category = query.data.split(":", 1)[1]
    context.user_data["category"] = category
    await query.edit_message_text(
        f"Category: {category}\n\nNow pick a genre:",
        reply_markup=genre_keyboard(category),
    )
    return GENRE


async def choose_genre(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    genre = query.data.split(":", 1)[1]
    context.user_data["genre"] = genre
    category = context.user_data["category"]
    database.save_last_filters(update.effective_user.id, category, genre)
    await query.edit_message_text(
        f"Category: {category} | Genre: {genre}\n\nWhich time range?",
        reply_markup=year_mode_keyboard(),
    )
    return YEAR_MODE


async def choose_year_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    mode = query.data.split(":", 1)[1]
    if mode == "all":
        context.user_data["year"] = None
        await query.edit_message_text(
            _summary_line(context) + "\n\nHow many results?",
            reply_markup=count_keyboard(),
        )
        return COUNT
    await query.edit_message_text(
        _summary_line(context) + "\n\nPick a year:",
        reply_markup=year_keyboard(),
    )
    return YEAR


async def choose_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    value = query.data.split(":", 1)[1]
    if value == "custom":
        await query.edit_message_text(
            _summary_line(context) + "\n\nType a 4-digit year (e.g. 1998):"
        )
        return YEAR_CUSTOM
    context.user_data["year"] = int(value)
    await query.edit_message_text(
        _summary_line(context) + "\n\nHow many results?",
        reply_markup=count_keyboard(),
    )
    return COUNT


async def choose_year_typed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit() or not (1900 <= int(text) <= 2100):
        await update.message.reply_text("That doesn't look like a valid year. Try again (e.g. 2015):")
        return YEAR_CUSTOM
    context.user_data["year"] = int(text)
    await update.message.reply_text(
        _summary_line(context) + "\n\nHow many results?",
        reply_markup=count_keyboard(),
    )
    return COUNT


async def choose_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    limit = int(query.data.split(":", 1)[1])
    context.user_data["count"] = limit

    await query.edit_message_text(_summary_line(context) + "\n\nSearching...")

    category = context.user_data["category"]
    genre_label = context.user_data["genre"]
    year = context.user_data.get("year")

    try:
        results = await _fetch_recommendations(category, genre_label, year, limit)
    except Exception:
        logger.exception("Recommendation fetch failed")
        await query.edit_message_text(
            "Sorry, I couldn't reach the data source just now. Please try again shortly.",
            reply_markup=category_keyboard(),
        )
        return CATEGORY

    if not results:
        await query.edit_message_text(
            _summary_line(context) + "\n\nNo results matched those filters. Try different ones:",
            reply_markup=category_keyboard(),
        )
        return CATEGORY

    context.user_data["last_results"] = results
    text = _summary_line(context) + f"\n\nTop {len(results)} picks — tap one for details:"
    await query.edit_message_text(text, reply_markup=results_keyboard(results))
    return RESULTS


async def show_item_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    index = int(query.data.split(":", 1)[1])
    results = context.user_data.get("last_results", [])
    if index >= len(results):
        await query.answer("That item expired, please search again.", show_alert=True)
        return RESULTS
    item = results[index]

    try:
        details = await _fetch_details(item)
    except Exception:
        logger.exception("Detail fetch failed")
        details = None

    caption = _format_detail(item, details)
    poster = item.get("poster")

    if poster:
        try:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id, photo=poster,
                caption=caption, reply_markup=detail_keyboard(),
                parse_mode="Markdown",
            )
            return RESULTS
        except Exception:
            logger.warning("Could not send poster image, falling back to text")

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=caption,
        reply_markup=detail_keyboard(), parse_mode="Markdown",
    )
    return RESULTS


async def back_to_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Detail views are sent as separate messages; just clean this one up."""
    query = update.callback_query
    await query.answer()
    try:
        await query.delete_message()
    except Exception:
        pass
    return RESULTS


# ---------- generic "back" handling for earlier steps ----------

async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    target = query.data.split(":", 1)[1]

    if target == "start":
        return await restart_from_callback(update, context)

    if target == "category":
        context.user_data.pop("genre", None)
        context.user_data.pop("year", None)
        await query.edit_message_text(WELCOME, reply_markup=category_keyboard())
        return CATEGORY

    if target == "genre":
        category = context.user_data.get("category")
        await query.edit_message_text(
            f"Category: {category}\n\nNow pick a genre:",
            reply_markup=genre_keyboard(category),
        )
        return GENRE

    if target == "yearmode":
        await query.edit_message_text(
            _summary_line(context) + "\n\nWhich time range?",
            reply_markup=year_mode_keyboard(),
        )
        return YEAR_MODE

    if target == "results":
        results = context.user_data.get("last_results", [])
        text = _summary_line(context) + f"\n\nTop {len(results)} picks — tap one for details:"
        await query.edit_message_text(text, reply_markup=results_keyboard(results))
        return RESULTS

    # fallback
    return await restart_from_callback(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Okay, cancelled. Send /start whenever you want recommendations again.")
    return ConversationHandler.END


# ---------- helpers ----------

def _summary_line(context: ContextTypes.DEFAULT_TYPE) -> str:
    parts = [f"Category: {context.user_data.get('category')}"]
    if context.user_data.get("genre"):
        parts.append(f"Genre: {context.user_data['genre']}")
    if "year" in context.user_data:
        parts.append(f"Year: {context.user_data['year'] or 'All-time'}")
    return " | ".join(parts)


async def _fetch_recommendations(category: str, genre_label: str, year, limit: int) -> list:
    genre_value = None if genre_label == "Any" else genres_for(category).get(genre_label)

    if category == "Movies":
        return await tmdb_service.discover("movie", genre_value, year, limit)
    if category == "Web Series":
        return await tmdb_service.discover("tv", genre_value, year, limit)
    if category == "Novels":
        return await books_service.discover(genre_value, year, limit)
    if category in ("Light Novels", "Manga"):
        return await jikan_service.discover(category, genre_value, year, limit)
    return []


async def _fetch_details(item: dict) -> dict | None:
    if item["source"] == "tmdb":
        return await tmdb_service.get_details(item["kind"], item["id"])
    if item["source"] == "jikan":
        return await jikan_service.get_details(item["id"])
    if item["source"] == "google_books":
        return await books_service.get_details(item["id"])
    return None


def _format_detail(item: dict, details: dict | None) -> str:
    title = (details or {}).get("title") or item["title"]
    rating = item.get("rating", "N/A")
    year = item.get("year", "N/A")

    lines = [f"*{title}*", f"Rating: {rating}  |  Year: {year}"]

    if details:
        genres = details.get("genres") or []
        if genres:
            lines.append("Genres: " + ", ".join(genres[:5]))
        if details.get("authors"):
            lines.append("Author(s): " + ", ".join(details["authors"][:3]))
        if details.get("cast"):
            lines.append("Cast: " + ", ".join(details["cast"][:5]))
        if details.get("popularity") is not None:
            lines.append(f"Popularity score: {details['popularity']}")
        overview = details.get("overview") or item.get("overview", "")
    else:
        overview = item.get("overview", "No summary available.")

    lines.append("")
    lines.append(overview[:700])
    return "\n".join(lines)


def build_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("recommend", start)],
        states={
            CATEGORY: [CallbackQueryHandler(choose_category, pattern="^cat:")],
            GENRE: [
                CallbackQueryHandler(choose_genre, pattern="^genre:"),
                CallbackQueryHandler(go_back, pattern="^back:"),
            ],
            YEAR_MODE: [
                CallbackQueryHandler(choose_year_mode, pattern="^yearmode:"),
                CallbackQueryHandler(go_back, pattern="^back:"),
            ],
            YEAR: [
                CallbackQueryHandler(choose_year, pattern="^year:"),
                CallbackQueryHandler(go_back, pattern="^back:"),
            ],
            YEAR_CUSTOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_year_typed)],
            COUNT: [
                CallbackQueryHandler(choose_count, pattern="^count:"),
                CallbackQueryHandler(go_back, pattern="^back:"),
            ],
            RESULTS: [
                CallbackQueryHandler(show_item_detail, pattern="^item:"),
                CallbackQueryHandler(back_to_results, pattern="^back:results"),
                CallbackQueryHandler(go_back, pattern="^back:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
        name="recommendation_wizard",
        persistent=False,
    )
