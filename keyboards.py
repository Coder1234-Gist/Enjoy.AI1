"""
All InlineKeyboardMarkup builders live here so the handlers stay readable.
callback_data conventions (kept short — Telegram caps it at 64 bytes):
    cat:<Category>
    genre:<GenreLabel>
    yearmode:specific / yearmode:all
    year:<YYYY>
    count:5 / count:10
    item:<index>          -> show details for results[index]
    back:<step>
    noop                  -> disabled/decorative button
"""
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from genres import CATEGORIES, genres_for


def chunk(buttons: list[InlineKeyboardButton], per_row: int = 2) -> list[list[InlineKeyboardButton]]:
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


def category_keyboard() -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(c, callback_data=f"cat:{c}") for c in CATEGORIES]
    return InlineKeyboardMarkup(chunk(buttons, 2))


def genre_keyboard(category: str) -> InlineKeyboardMarkup:
    labels = list(genres_for(category).keys())
    buttons = [InlineKeyboardButton(g, callback_data=f"genre:{g}") for g in labels]
    rows = chunk(buttons, 2)
    rows.append([InlineKeyboardButton("Any genre", callback_data="genre:Any")])
    rows.append([InlineKeyboardButton("<< Back", callback_data="back:category")])
    return InlineKeyboardMarkup(rows)


def year_mode_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("A specific year", callback_data="yearmode:specific")],
        [InlineKeyboardButton("All-time", callback_data="yearmode:all")],
        [InlineKeyboardButton("<< Back", callback_data="back:genre")],
    ]
    return InlineKeyboardMarkup(rows)


def year_keyboard() -> InlineKeyboardMarkup:
    current_year = datetime.now().year
    years = [str(y) for y in range(current_year, current_year - 15, -1)]
    buttons = [InlineKeyboardButton(y, callback_data=f"year:{y}") for y in years]
    rows = chunk(buttons, 4)
    rows.append([InlineKeyboardButton("Type a different year", callback_data="year:custom")])
    rows.append([InlineKeyboardButton("<< Back", callback_data="back:yearmode")])
    return InlineKeyboardMarkup(rows)


def count_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("Top 5", callback_data="count:5"),
         InlineKeyboardButton("Top 10", callback_data="count:10")],
        [InlineKeyboardButton("<< Back", callback_data="back:yearmode")],
    ]
    return InlineKeyboardMarkup(rows)


def results_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for i, item in enumerate(items):
        label = f"{i + 1}. {item['title']} ({item['year']})"
        if len(label) > 60:
            label = label[:57] + "..."
        rows.append([InlineKeyboardButton(label, callback_data=f"item:{i}")])
    rows.append([
        InlineKeyboardButton("Change filters", callback_data="back:category"),
        InlineKeyboardButton("Start over", callback_data="back:start"),
    ])
    return InlineKeyboardMarkup(rows)


def detail_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton("<< Back to results", callback_data="back:results")]]
    return InlineKeyboardMarkup(rows)


def subscribe_keyboard(subscribed: bool) -> InlineKeyboardMarkup:
    if subscribed:
        rows = [[InlineKeyboardButton("Unsubscribe from daily digest", callback_data="unsubscribe")]]
    else:
        rows = [[InlineKeyboardButton("Subscribe to daily digest", callback_data="subscribe")]]
    return InlineKeyboardMarkup(rows)
