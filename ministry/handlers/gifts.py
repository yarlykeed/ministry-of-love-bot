from telegram import Update
from telegram.ext import ContextTypes

from ministry import texts
from ministry.db import SessionLocal
from ministry.handlers.common import command_argument, numbered_list
from ministry.models import GiftsMode
from ministry.services import gifts
from ministry.services.chats import set_gifts_mode
from ministry.services.errors import (
    AlreadyExists,
    CustomGiftsDisabled,
    NameTooLong,
    NotFound,
)


async def choose_standard(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    with SessionLocal.begin() as session:
        set_gifts_mode(session, update.effective_chat.id, GiftsMode.STANDARD)

    await update.message.reply_text(texts.STANDARD_GIFTS_CHOSEN)


async def choose_custom(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    with SessionLocal.begin() as session:
        set_gifts_mode(session, update.effective_chat.id, GiftsMode.CUSTOM)

    await update.message.reply_text(texts.CUSTOM_GIFTS_CHOSEN)


async def show_gifts(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    with SessionLocal() as session:
        pool = gifts.get_gift_pool(session, update.effective_chat.id)

    if pool is None:
        await update.message.reply_text(texts.GIFTS_MODE_NOT_CHOSEN)
    elif not pool:
        await update.message.reply_text(texts.NO_GIFTS)
    else:
        await update.message.reply_text(
            numbered_list(texts.GIFTS_HEADER, pool)
        )


async def add_gift(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = command_argument(context)

    if not name:
        await update.message.reply_text(texts.ADD_GIFT_USAGE)
        return

    try:
        with SessionLocal.begin() as session:
            gifts.add_gift(session, update.effective_chat.id, name)
    except CustomGiftsDisabled:
        await update.message.reply_text(texts.ADD_GIFT_NOT_CUSTOM)
        return
    except NameTooLong as error:
        await update.message.reply_text(
            texts.GIFT_NAME_TOO_LONG.format(limit=error.limit)
        )
        return
    except AlreadyExists:
        await update.message.reply_text(texts.GIFT_ALREADY_EXISTS)
        return

    await update.message.reply_text(texts.GIFT_ADDED.format(name=name))


async def delete_gift(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    name = command_argument(context)

    if not name:
        await update.message.reply_text(texts.DELETE_GIFT_USAGE)
        return

    try:
        with SessionLocal.begin() as session:
            gifts.delete_gift(session, update.effective_chat.id, name)
    except CustomGiftsDisabled:
        await update.message.reply_text(texts.DELETE_GIFT_NOT_CUSTOM)
        return
    except NotFound:
        await update.message.reply_text(texts.GIFT_NOT_FOUND)
        return

    await update.message.reply_text(texts.GIFT_DELETED.format(name=name))
