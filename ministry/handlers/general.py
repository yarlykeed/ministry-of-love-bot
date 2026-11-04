from telegram import Update
from telegram.ext import ContextTypes

from ministry import texts
from ministry.config import OWNER_ID
from ministry.db import SessionLocal
from ministry.models import GiftsMode
from ministry.services.chats import get_or_create_chat


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with SessionLocal.begin() as session:
        chat = get_or_create_chat(session, update.effective_chat.id)
        is_configured = chat.gifts_mode != GiftsMode.UNSET

    await update.message.reply_text(
        texts.START_AGAIN if is_configured else texts.START_FIRST_TIME
    )


async def help_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await update.message.reply_text(texts.HELP)


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(texts.INFO)


async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if OWNER_ID is not None and user_id != OWNER_ID:
        await update.message.reply_text(texts.MY_ID_FORBIDDEN)
        return

    await update.message.reply_text(texts.MY_ID.format(user_id=user_id))
