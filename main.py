import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

import database
import scheduler
from config import BOT_TOKEN, USE_WEBHOOK, PORT, WEBHOOK_BASE_URL, WEBHOOK_SECRET
from handlers.conversation import build_conversation_handler
from handlers import subscription

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)  # quiet PTB's HTTP logs
logger = logging.getLogger(__name__)


def main():
    if not BOT_TOKEN:
        raise SystemExit(
            "BOT_TOKEN is not set. Copy .env.example to .env, add your token "
            "from @BotFather, and try again."
        )

    database.init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # Recommendation wizard (covers /start and /recommend)
    app.add_handler(build_conversation_handler())

    # Standalone commands
    app.add_handler(CommandHandler("help", subscription.help_command))
    app.add_handler(CommandHandler("subscribe", subscription.subscribe_command))
    app.add_handler(CommandHandler("unsubscribe", subscription.unsubscribe_command))
    app.add_handler(CallbackQueryHandler(subscription.subscribe_callback, pattern="^subscribe$"))
    app.add_handler(CallbackQueryHandler(subscription.unsubscribe_callback, pattern="^unsubscribe$"))

    # Daily digest job
    scheduler.schedule_daily_job(app.job_queue)

    if USE_WEBHOOK:
        if not WEBHOOK_BASE_URL:
            raise SystemExit(
                "USE_WEBHOOK is true but no public URL is available. On "
                "Render this comes automatically from RENDER_EXTERNAL_URL; "
                "on other hosts, set WEBHOOK_URL manually (e.g. "
                "https://yourapp.example.com)."
            )
        # The bot token doubles as a hard-to-guess path segment, so random
        # bots scanning the internet can't hit this endpoint by accident.
        webhook_path = BOT_TOKEN
        webhook_url = f"{WEBHOOK_BASE_URL.rstrip('/')}/{webhook_path}"
        logger.info("Bot starting in webhook mode at %s (port %s)", webhook_url, PORT)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=webhook_path,
            webhook_url=webhook_url,
            secret_token=WEBHOOK_SECRET or None,
            allowed_updates=["message", "callback_query"],
        )
    else:
        logger.info("Bot starting in polling mode...")
        app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
