from dataclasses import dataclass

from telegram import Update
from telegram.ext import ContextTypes

from ministry import texts
from ministry.db import SessionLocal
from ministry.handlers.common import command_argument, numbered_list
from ministry.services import characters
from ministry.services.errors import AlreadyExists, NameTooLong, NotFound

# user_data key: {chat_id: PhotoRequest}. One pending request per user
# per chat; a new /add or /addphoto replaces the previous one.
PHOTO_REQUESTS = "photo_requests"


@dataclass(frozen=True)
class PhotoRequest:
    character_id: int
    message_id: int


def _remember_photo_request(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    character_id: int,
    message_id: int,
) -> None:
    requests = context.user_data.setdefault(PHOTO_REQUESTS, {})
    requests[chat_id] = PhotoRequest(character_id, message_id)


async def add_character(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    name = command_argument(context)

    if not name:
        await update.message.reply_text(texts.ADD_CHARACTER_USAGE)
        return

    chat_id = update.effective_chat.id

    try:
        with SessionLocal.begin() as session:
            character = characters.add_character(session, chat_id, name)
            character_id = character.id
    except NameTooLong as error:
        await update.message.reply_text(
            texts.CHARACTER_NAME_TOO_LONG.format(limit=error.limit)
        )
        return
    except AlreadyExists:
        await update.message.reply_text(texts.CHARACTER_ALREADY_EXISTS)
        return

    sent = await update.message.reply_text(
        texts.CHARACTER_ADDED.format(name=name)
    )
    _remember_photo_request(context, chat_id, character_id, sent.message_id)


async def request_photo(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    name = command_argument(context)

    if not name:
        await update.message.reply_text(texts.ADD_PHOTO_USAGE)
        return

    chat_id = update.effective_chat.id

    with SessionLocal() as session:
        character = characters.find_character(session, chat_id, name)

    if character is None:
        await update.message.reply_text(texts.CHARACTER_NOT_IN_CHAT)
        return

    sent = await update.message.reply_text(
        texts.PHOTO_REQUEST.format(name=character.name)
    )
    _remember_photo_request(context, chat_id, character.id, sent.message_id)


async def save_photo(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles photos sent as a reply to the bot's photo request."""
    message = update.message
    chat_id = update.effective_chat.id
    requests = context.user_data.get(PHOTO_REQUESTS, {})
    request = requests.get(chat_id)

    if (
        request is None
        or message.reply_to_message.message_id != request.message_id
    ):
        return

    del requests[chat_id]

    try:
        with SessionLocal.begin() as session:
            characters.set_photo(
                session,
                chat_id,
                request.character_id,
                message.photo[-1].file_id,
            )
    except NotFound:
        await message.reply_text(texts.CHARACTER_NOT_IN_CHAT)
        return

    await message.reply_text(texts.PHOTO_SAVED)


async def delete_character(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    name = command_argument(context)

    if not name:
        await update.message.reply_text(texts.DELETE_CHARACTER_USAGE)
        return

    try:
        with SessionLocal.begin() as session:
            characters.delete_character(
                session, update.effective_chat.id, name
            )
    except NotFound:
        await update.message.reply_text(texts.CHARACTER_NOT_FOUND)
        return

    await update.message.reply_text(texts.CHARACTER_DELETED.format(name=name))


async def show_characters(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    with SessionLocal() as session:
        names = [
            character.name
            for character in characters.list_characters(
                session, update.effective_chat.id
            )
        ]

    if not names:
        await update.message.reply_text(texts.NO_CHARACTERS)
        return

    await update.message.reply_text(
        numbered_list(texts.CHARACTERS_HEADER, names)
    )
