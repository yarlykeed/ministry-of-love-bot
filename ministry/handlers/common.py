from collections.abc import Iterable

from telegram import InputMediaPhoto, Message
from telegram.ext import ContextTypes

from ministry.services.dates import DateResult


def command_argument(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Everything after the command, e.g. `/add Иван Петров` -> `Иван Петров`."""
    return " ".join(context.args or []).strip()


def numbered_list(header: str, items: Iterable[str]) -> str:
    lines = [f"{number}. {item}" for number, item in enumerate(items, start=1)]
    return header + "\n\n" + "\n".join(lines)


async def send_date(message: Message, result: DateResult) -> None:
    """Replies with the date text, attaching the characters' photos if any."""
    if len(result.photos) >= 2:
        first, second = result.photos[:2]
        await message.reply_media_group(media=[
            InputMediaPhoto(media=first, caption=result.text),
            InputMediaPhoto(media=second),
        ])
    elif result.photos:
        await message.reply_photo(photo=result.photos[0], caption=result.text)
    else:
        await message.reply_text(result.text)
