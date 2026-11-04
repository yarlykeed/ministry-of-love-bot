from telegram import Bot, BotCommand, BotCommandScopeChat
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from ministry import texts
from ministry.config import OWNER_ID
from ministry.handlers import characters, dates, general, gifts

COMMAND_HANDLERS = {
    "start": general.start,
    "help": general.help_command,
    "info": general.info,
    "myid": general.my_id,
    "pair": dates.pair,
    "random": dates.random_date,
    "match": dates.match,
    "add": characters.add_character,
    "addphoto": characters.request_photo,
    "delete": characters.delete_character,
    "characters": characters.show_characters,
    "gifts": gifts.show_gifts,
    "standard": gifts.choose_standard,
    "custom": gifts.choose_custom,
    "addgift": gifts.add_gift,
    "deletegift": gifts.delete_gift,
}


def register_handlers(app: Application) -> None:
    for command, callback in COMMAND_HANDLERS.items():
        app.add_handler(CommandHandler(command, callback))

    app.add_handler(
        MessageHandler(filters.PHOTO & filters.REPLY, characters.save_photo)
    )


def _bot_commands(descriptions: dict[str, str]) -> list[BotCommand]:
    return [BotCommand(name, text) for name, text in descriptions.items()]


async def setup_bot_commands(bot: Bot) -> None:
    """Fills the Telegram command menu; the owner also sees owner-only ones."""
    commands = _bot_commands(texts.COMMAND_DESCRIPTIONS)
    await bot.set_my_commands(commands)

    if OWNER_ID is not None:
        await bot.set_my_commands(
            commands + _bot_commands(texts.OWNER_COMMAND_DESCRIPTIONS),
            scope=BotCommandScopeChat(chat_id=OWNER_ID),
        )
