"""
Commands that work independently of the recommendation wizard.
"""
from telegram import Update
from telegram.ext import ContextTypes

import database
from keyboards import subscribe_keyboard

HELP_TEXT = (
    "*What I can do*\n"
    "/start - Get recommendations (Movies, Web Series, Novels, Light Novels, Manga)\n"
    "/subscribe - Get a daily digest of new releases, trending titles & news\n"
    "/unsubscribe - Turn the daily digest off\n"
    "/cancel - Stop whatever you're doing and reset\n"
    "/help - Show this message"
)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subscribed = database.is_subscribed(update.effective_user.id)
    await update.message.reply_text(
        HELP_TEXT, parse_mode="Markdown", reply_markup=subscribe_keyboard(subscribed)
    )


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    database.upsert_user(user.id, user.username, user.first_name)
    database.set_subscription(user.id, True)
    await update.message.reply_text(
        "You're subscribed! You'll get a daily digest of new releases, trending "
        "titles, and industry news."
    )


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    database.set_subscription(user.id, False)
    await update.message.reply_text("You've been unsubscribed from the daily digest.")


async def subscribe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    database.set_subscription(update.effective_user.id, True)
    await query.edit_message_text("You're subscribed to the daily digest!")


async def unsubscribe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    database.set_subscription(update.effective_user.id, False)
    await query.edit_message_text("You've been unsubscribed from the daily digest.")
