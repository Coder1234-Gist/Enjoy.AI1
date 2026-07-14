import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

import database
import scheduler
from config import BOT_TOKEN
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

    logger.info("Bot starting...")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
