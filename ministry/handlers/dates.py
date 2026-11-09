from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from ministry import texts
from ministry.constants import PAIR_TIMEZONE
from ministry.db import SessionLocal
from ministry.handlers.common import command_argument, send_date
from ministry.services import dates
from ministry.services.errors import NotEnoughCharacters, NotFound


async def pair(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    today = datetime.now(PAIR_TIMEZONE).date()

    try:
        with SessionLocal.begin() as session:
            result = dates.daily_pair(session, update.effective_chat.id, today)
    except NotEnoughCharacters:
        await update.message.reply_text(texts.PAIR_NOT_ENOUGH)
        return

    await send_date(update.message, result)


async def random_date(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    try:
        with SessionLocal() as session:
            result = dates.random_date(session, update.effective_chat.id)
    except NotEnoughCharacters:
        await update.message.reply_text(texts.RANDOM_DATE_NOT_ENOUGH)
        return

    await send_date(update.message, result)


async def match(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = command_argument(context)

    if not name:
        await update.message.reply_text(texts.MATCH_USAGE)
        return

    try:
        with SessionLocal() as session:
            result = dates.match_character(
                session, update.effective_chat.id, name
            )
    except NotFound:
        await update.message.reply_text(
            texts.MATCH_CHARACTER_NOT_FOUND.format(name=name)
        )
        return
    except NotEnoughCharacters:
        await update.message.reply_text(texts.MATCH_NOT_ENOUGH)
        return

    await send_date(update.message, result)
