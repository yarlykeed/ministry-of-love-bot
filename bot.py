import logging

from telegram.ext import Application, ContextTypes

from ministry import texts
from ministry.constants import TELEGRAM_TOKEN
from ministry.db import init_db
from ministry.handlers import register_handlers, setup_bot_commands

logger = logging.getLogger(__name__)


async def on_startup(app: Application) -> None:
    await setup_bot_commands(app.bot)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Error while handling an update", exc_info=context.error)


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.INFO,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if not TELEGRAM_TOKEN:
        raise SystemExit("TOKEN is not set. Put it in .env (see .env.example).")

    init_db()

    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(on_startup)
        .build()
    )
    register_handlers(app)
    app.add_error_handler(on_error)

    logger.info(texts.BOT_STARTED)
    app.run_polling()


if __name__ == "__main__":
    main()
