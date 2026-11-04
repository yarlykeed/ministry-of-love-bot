
import sqlite3
import random

from datetime import datetime, timezone, timedelta

from telegram import (
    Update,
    BotCommand,
    BotCommandScopeChat,
    InputMediaPhoto
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)


import os

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    from config import TOKEN

OWNER_ID = 1655804253


STANDARD_GIFTS = [
    "Букет из 101 красной розы",
    "Коробка конфет",
    "Хозяйственное мыло",
    "Лопасть вертолета",
    "Роза в целлофане",
    "Пипидастр",
    "Ящик ананасов",
    "Крем для ног",
    "Бомбочка для ванной",
    "Полевой букетик",
    "Ветка",
    "Семечки",
    "Кофе из кофейного автомата за 50р",
    "Чьё-то ребро",
    "Игровой ноутбук Lenovo",
    "Алмазная мозаика",
    "Телеграм Премиум",
    "Головка сыра",
    "Чешки",
    "Клубника в шоколаде",
    "Колбасный букет",
    "Арбуз"
]


GIFT_PHRASES = [
    "🎁 {first} решил(а) преподнести {second} подарок: {gift}.",
    "💝 На свидание {first} приготовил(а) для {second}: {gift}.",
    "💍 Комитет сообщает, что в приданое для {second} включены: {gift}. Стороны вправе отказаться от союза, но не от приданого."
]


def connect_db():
    return sqlite3.connect("committee.db")


def init_database():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            gifts_mode TEXT DEFAULT 'unset',
            gifts_configured INTEGER DEFAULT 0
        )
    """)

    cursor.execute("PRAGMA table_info(chats)")
    columns = [column[1] for column in cursor.fetchall()]

    if "gifts_configured" not in columns:
        cursor.execute("""
            ALTER TABLE chats
            ADD COLUMN gifts_configured INTEGER DEFAULT 0
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            name TEXT
        )
    """)

    cursor.execute("PRAGMA table_info(characters)")
    character_columns = [
        column[1] for column in cursor.fetchall()
    ]

    if "photo_id" not in character_columns:
        cursor.execute("""
            ALTER TABLE characters
            ADD COLUMN photo_id TEXT
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            name TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS phrases (
            id INTEGER PRIMARY KEY,
            phrase TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_pairs (
            chat_id INTEGER PRIMARY KEY,
            pair_date TEXT,
            character_1 TEXT,
            character_2 TEXT
        )
    """)

    cursor.execute("PRAGMA table_info(daily_pairs)")
    pair_columns = [
        column[1] for column in cursor.fetchall()
    ]

    if "gift" not in pair_columns:
        cursor.execute("""
            ALTER TABLE daily_pairs
            ADD COLUMN gift TEXT
        """)

    if "gift_phrase" not in pair_columns:
        cursor.execute("""
            ALTER TABLE daily_pairs
            ADD COLUMN gift_phrase TEXT
        """)

    conn.commit()
    conn.close()


async def setup_commands(app):
    commands = [
        # ℹ️ Помощь
        BotCommand("start", "Запустить комитет"),
        BotCommand("help", "Список команд"),
        BotCommand("info", "Информация о Министерстве"),

        # 💞 Союзы
        BotCommand("pair", "Назначить пару дня"),
        BotCommand("random", "Случайное свидание"),
        BotCommand("match", "Подобрать пару персонажу"),

        # 👥 Персонажи
        BotCommand("add", "Добавить персонажа"),
        BotCommand("addphoto", "Добавить или заменить фото"),
        BotCommand("delete", "Удалить персонажа"),
        BotCommand("characters", "Список персонажей"),

        # 🎁 Подарки
        BotCommand("gifts", "Посмотреть набор подарков"),
        BotCommand("standard", "Выбрать стандартные подарки"),
        BotCommand("custom", "Выбрать свой набор подарков"),
        BotCommand("addgift", "Добавить подарок"),
        BotCommand("deletegift", "Удалить подарок")
    ]

    await app.bot.set_my_commands(commands)

    if OWNER_ID != 0:
        owner_commands = commands + [
            BotCommand("myid", "Мой Telegram ID")
        ]

        await app.bot.set_my_commands(
            owner_commands,
            scope=BotCommandScopeChat(
                chat_id=OWNER_ID,
            )
        )

        
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR IGNORE INTO chats (chat_id) VALUES (?)",
        (chat_id,)
    )

    cursor.execute(
        "SELECT gifts_configured FROM chats WHERE chat_id = ?",
        (chat_id,)
    )

    result = cursor.fetchone()
    conn.commit()
    conn.close()

    if result and result[0] == 0:
        await update.message.reply_text(
            "Добро пожаловать в Министерство любви! 💌\n\n"
            "Для начала выберите набор подарков:\n\n"
            "Стандартный набор — /standard\n"
            "Свой набор — /custom"
        )
    else:
        await update.message.reply_text(
            "💌 Комитет снова на связи!\n\n"
            "Добавляйте персонажей, выбирайте пары и "
            "доверяйте чужую личную жизнь в наши руки.\n\n"
            "Список команд: /help\n"
            "Информация: /info"
        )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "📜 Команды Министерства любви:\n\n"

        "💞 СОЮЗЫ\n"
        "/pair — назначить пару дня. Пара и подарок сохраняются до следующего дня.\n"
        "/random — устроить случайное свидание.\n"
        "/match Имя — подобрать случайного партнёра персонажу.\n\n"

        "👥 ПЕРСОНАЖИ\n"
        "/add Имя — добавить персонажа.\n"
        "/addphoto Имя — добавить или изменить фотографию персонажа.\n"
        "/delete Имя — удалить персонажа.\n"
        "/characters — посмотреть список персонажей.\n\n"

        "🎁 ПОДАРКИ\n"
        "/gifts — посмотреть доступные подарки.\n"
        "/standard — выбрать стандартный набор подарков.\n"
        "/custom — выбрать собственный набор подарков.\n"
        "/addgift Название — добавить подарок в собственный набор.\n"
        "/deletegift Название — удалить подарок из собственного набора.\n\n"

        "ℹ️ ПОМОЩЬ\n"
        "/start — запустить бота.\n"
        "/help — показать список команд.\n"
        "/info — информация о Министерстве любви."
    )

async def info_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "💌 Приветствую! Мы — Министерство Любви и ваш "
        "личный помощник в амурных делах.\n\n"
        "Поможем подобрать пару вашим персонажам, "
        "сводить их на свидание и подарить оригинальные подарки!\n\n"

        "✨ ЧТО МЫ УМЕЕМ:\n\n"

        "💞 Создавать пару дня (Pair) — раз в сутки мы "
        "случайным образом выбираем пару дня из добавленных "
        "персонажей и дарим подарки. Пара и подарки обновляются "
        "каждый день в 00:00 по московскому времени.\n\n"

        "💌 Водить на свидания (Random) — команда позволяет "
        "сводить двух случайных персонажей на свидание.\n\n"

        "❤️ Выбрать пару персонажу (Match) — команда позволяет "
        "подобрать случайную пару конкретному персонажу.\n\n"

        "🎁 Дарить подарки (Gifts) — персонажи дарят друг другу "
        "стандартные или кастомные подарки в Pair и изредка в Random.\n\n"

        "Это основные возможности Министерства. С остальными "
        "командами вы можете ознакомиться через /help.\n\n"

        "И помните: за личную жизнь персонажей Комитет "
        "ответственности не несёт! 💌"
    )

async def my_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user_id = update.effective_user.id


    if OWNER_ID != 1655804253 and user_id != OWNER_ID:
        await update.message.reply_text(
            "Эта команда доступна только владельцу Комитета."
        )
        return

    await update.message.reply_text(
        f"Твой Telegram ID: {user_id}\n\n"
        "Сохрани его. Он понадобится для настройки прав владельца."
    )



async def add_character(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat_id = update.effective_chat.id

    if not context.args:
        await update.message.reply_text(
            "Напиши имя персонажа после команды.\n"
            "Например: /add Иван"
        )
        return

    name = " ".join(context.args).strip()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR IGNORE INTO chats (chat_id) VALUES (?)",
        (chat_id,)
    )

    cursor.execute("""
        SELECT id FROM characters
        WHERE chat_id = ? AND LOWER(name) = LOWER(?)
    """, (chat_id, name))

    if cursor.fetchone():
        conn.close()
        await update.message.reply_text(
            "Такой персонаж уже есть в списке!"
        )
        return

    cursor.execute("""
        INSERT INTO characters (chat_id, name)
        VALUES (?, ?)
    """, (chat_id, name))

    character_id = cursor.lastrowid

    conn.commit()
    conn.close()

    pending = context.user_data.setdefault(
        "pending_characters", {}
    )

    sent_message = await update.message.reply_text(
        f"✨ Персонаж «{name}» добавлен в список!\n\n"
        "Теперь отправь его фотографию ответом на это сообщение.\n"
        "Если фотография не нужна, просто проигнорируй это сообщение."
    )

    pending[chat_id] = {
        "character_id": character_id,
        "message_id": sent_message.message_id
    }


async def add_character_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat_id = update.effective_chat.id
    name = " ".join(context.args).strip()

    if not name:
        await update.message.reply_text(
            "Укажи имя персонажа. Например: /addphoto Кристофер"
        )
        return

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM characters
        WHERE chat_id = ? AND LOWER(name) = LOWER(?)
    """, (chat_id, name))

    character = cursor.fetchone()
    conn.close()

    if not character:
        await update.message.reply_text(
            "Такого персонажа нет в списке этого чата."
        )
        return

    sent_message = await update.message.reply_text(
        f"📸 Отправь фотографию для персонажа «{name}» "
        "ответом на это сообщение."
    )

    pending_photos = context.user_data.setdefault(
        "pending_photos", {}
    )

    pending_photos[chat_id] = {
        "character_id": character[0],
        "message_id": sent_message.message_id
    }



async def save_character_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat_id = update.effective_chat.id
    message = update.message

    pending_new = context.user_data.get(
        "pending_characters", {}
    )
    pending_existing = context.user_data.get(
        "pending_photos", {}
    )

    pending = None
    photo_mode = None

    if chat_id in pending_new:
        pending = pending_new[chat_id]
        photo_mode = "new"

    elif chat_id in pending_existing:
        pending = pending_existing[chat_id]
        photo_mode = "existing"

    if not pending:
        return

    if (
        not message.reply_to_message
        or message.reply_to_message.message_id != pending["message_id"]
    ):
        await message.reply_text(
            "⚠️ Отправь фотографию ответом на сообщение бота "
            "с просьбой прислать фото."
        )
        return

    character_id = pending["character_id"]
    photo_id = message.photo[-1].file_id

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE characters
        SET photo_id = ?
        WHERE id = ? AND chat_id = ?
    """, (photo_id, character_id, chat_id))

    conn.commit()
    conn.close()

    if photo_mode == "new":
        del pending_new[chat_id]
    else:
        del pending_existing[chat_id]

    await message.reply_text(
        "📸 Фотография персонажа сохранена!"
    )

async def delete_character(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat_id = update.effective_chat.id

    if not context.args:
        await update.message.reply_text(
            "Напиши имя персонажа после команды.\n"
            "Например: /delete Иван"
        )
        return

    name = " ".join(context.args).strip()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM characters
        WHERE chat_id = ? AND LOWER(name) = LOWER(?)
    """, (chat_id, name))

    deleted = cursor.rowcount

    if deleted:
        cursor.execute("""
            DELETE FROM daily_pairs
            WHERE chat_id = ?
            AND (
                LOWER(character_1) = LOWER(?)
                OR LOWER(character_2) = LOWER(?)
            )
        """, (chat_id, name, name))

    conn.commit()
    conn.close()

    if deleted:
        await update.message.reply_text(
            f"Персонаж «{name}» удалён из списка."
        )
    else:
        await update.message.reply_text(
            "Такого персонажа в списке нет."
        )


async def show_characters(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat_id = update.effective_chat.id

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name FROM characters
        WHERE chat_id = ?
        ORDER BY name COLLATE NOCASE
    """, (chat_id,))

    characters = cursor.fetchall()
    conn.close()

    if not characters:
        await update.message.reply_text(
            "Список персонажей пока пуст.\n"
            "Добавить персонажа можно командой /add"
        )
        return

    text = "📜 Список персонажей:\n\n"

    for number, character in enumerate(characters, start=1):
        text += f"{number}. {character[0]}\n"

    await update.message.reply_text(text)


async def choose_standard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat_id = update.effective_chat.id

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO chats (chat_id)
        VALUES (?)
    """, (chat_id,))

    cursor.execute("""
        UPDATE chats
        SET gifts_mode = 'standard',
            gifts_configured = 1
        WHERE chat_id = ?
    """, (chat_id,))

    conn.commit()
    conn.close()

    await update.message.reply_text(
        "🎁 Выбран стандартный набор подарков!\n"
        "Посмотреть его можно командой /gifts"
    )


async def choose_custom(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat_id = update.effective_chat.id

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO chats (chat_id)
        VALUES (?)
    """, (chat_id,))

    cursor.execute("""
        UPDATE chats
        SET gifts_mode = 'custom',
            gifts_configured = 1
        WHERE chat_id = ?
    """, (chat_id,))

    conn.commit()
    conn.close()

    await update.message.reply_text(
        "🎁 Выбран собственный набор подарков!\n\n"
        "Добавить подарок: /addgift Название\n"
        "Удалить подарок: /deletegift Название\n"
        "Посмотреть список: /gifts"
    )


async def show_gifts(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat_id = update.effective_chat.id

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT gifts_mode FROM chats
        WHERE chat_id = ?
    """, (chat_id,))

    result = cursor.fetchone()

    if not result:
        conn.close()
        await update.message.reply_text(
            "Сначала запусти бота командой /start"
        )
        return

    gifts_mode = result[0]

    if gifts_mode == "standard":
        gifts = STANDARD_GIFTS

    elif gifts_mode == "custom":
        cursor.execute("""
            SELECT name FROM gifts
            WHERE chat_id = ?
            ORDER BY name COLLATE NOCASE
        """, (chat_id,))

        gifts = [row[0] for row in cursor.fetchall()]

    else:
        conn.close()
        await update.message.reply_text(
            "Сначала выбери набор подарков: "
            "/standard или /custom"
        )
        return

    conn.close()

    if not gifts:
        await update.message.reply_text(
            "Список подарков пока пуст."
        )
        return

    text = "🎁 Список подарков:\n\n"

    for number, gift in enumerate(gifts, start=1):
        text += f"{number}. {gift}\n"

    await update.message.reply_text(text)


async def add_gift(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat_id = update.effective_chat.id

    if not context.args:
        await update.message.reply_text(
            "Напиши название подарка после команды.\n"
            "Например: /addgift Торт"
        )
        return

    name = " ".join(context.args).strip()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT gifts_mode FROM chats
        WHERE chat_id = ?
    """, (chat_id,))

    result = cursor.fetchone()

    if not result or result[0] != "custom":
        conn.close()
        await update.message.reply_text(
            "Добавлять подарки можно только в собственный набор.\n"
            "Для этого сначала выбери /custom"
        )
        return

    cursor.execute("""
        SELECT id FROM gifts
        WHERE chat_id = ? AND LOWER(name) = LOWER(?)
    """, (chat_id, name))

    if cursor.fetchone():
        conn.close()
        await update.message.reply_text(
            "Такой подарок уже есть в списке!"
        )
        return

    cursor.execute("""
        INSERT INTO gifts (chat_id, name)
        VALUES (?, ?)
    """, (chat_id, name))

    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"🎁 Подарок «{name}» добавлен!"
    )


async def delete_gift(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat_id = update.effective_chat.id

    if not context.args:
        await update.message.reply_text(
            "Напиши название подарка после команды.\n"
            "Например: /deletegift Торт"
        )
        return

    name = " ".join(context.args).strip()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT gifts_mode FROM chats
        WHERE chat_id = ?
    """, (chat_id,))

    result = cursor.fetchone()

    if not result or result[0] != "custom":
        conn.close()
        await update.message.reply_text(
            "Удалять подарки можно только из собственного набора."
        )
        return

    cursor.execute("""
        DELETE FROM gifts
        WHERE chat_id = ? AND LOWER(name) = LOWER(?)
    """, (chat_id, name))

    deleted = cursor.rowcount

    conn.commit()
    conn.close()

    if deleted:
        await update.message.reply_text(
            f"Подарок «{name}» удалён."
        )
    else:
        await update.message.reply_text(
            "Такого подарка в списке нет."
        )


async def send_pair_with_photos(
    update,
    first_name,
    second_name,
    character_data,
    message_text
):
    first_photo = character_data.get(first_name)
    second_photo = character_data.get(second_name)

    if first_photo and second_photo:
        await update.message.reply_media_group(
            media=[
                InputMediaPhoto(
                    media=first_photo,
                    caption=message_text
                ),
                InputMediaPhoto(
                    media=second_photo
                )
            ]
        )

    elif first_photo:
        await update.message.reply_photo(
            photo=first_photo,
            caption=message_text
        )

    elif second_photo:
        await update.message.reply_photo(
            photo=second_photo,
            caption=message_text
        )

    else:
        await update.message.reply_text(message_text)



async def random_pair(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat_id = update.effective_chat.id

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name, photo_id FROM characters
        WHERE chat_id = ?
    """, (chat_id,))

    characters = cursor.fetchall()

    gifts = get_chat_gifts(cursor, chat_id)

    conn.close()

    if len(characters) < 2:
        await update.message.reply_text(
            "Для случайного свидания нужны хотя бы два персонажа."
        )
        return

    event_roll = random.random()

    if event_roll < 0.1:

        character = random.choice(characters)
        name = character[0]

        character_data = {
            name: character[1]
        }

        message_text = (
            "💞 Случайное свидание:\n\n"
            f"{name} решил(а) провести время с самым "
            "близким и понимающим человеком — с самим собой!"
        )

        await send_pair_with_photos(
            update,
            name,
            name,
            character_data,
            message_text
        )
        return

    elif event_roll < 0.2:

        character = random.choice(characters)
        name = character[0]

        message_text = (
            "🛁 Случайное свидание:\n\n"
            f"{name} сегодня совершенно не в настроении "
            "для встреч. Никаких свиданий и лишней суеты! "
            "Он(а) решил(а) остаться дома, набрать горячую "
            "ванну и провести вечер в тишине и спокойствии."
        )

        if character[1]:
            await update.message.reply_photo(
                photo=character[1],
                caption=message_text
            )
        else:
            await update.message.reply_text(message_text)

        return

    first, second = random.sample(characters, 2)

    first_name = first[0]
    second_name = second[0]

    character_data = {
        first_name: first[1],
        second_name: second[1]
    }

    scenarios = [
        (2, 1),
        (2, 2),
        (2, 3),
        (4, 4),
        (2, 5),
        (2, 6),
        (2, 7),
        (2, 8),
        (3, 9),
        (3, 10),
        (2, 11),
        (2, 12),
        (2, 13),
        (3, 14),
        (2, 15),
        (2, 16),
        (3, 17),
        (2, 18),
        (2, 19),
        (3, 20),
        (2, 21),
        (3, 22),
        (3, 23),
        (2, 24),
        (2, 25)
    ]

    available_scenarios = [
        number for minimum, number in scenarios
        if len(characters) >= minimum
    ]

    scenario = random.choice(available_scenarios)

    remaining = [
        character for character in characters
        if character not in (first, second)
    ]

    if scenario == 1:
        story = (
            f"{first_name} пригласил(а) {second_name} "
            "на прогулку по осеннему парку. Они долго гуляли, "
            "собирали красивые листья и совершенно забыли о времени."
        )

    elif scenario == 2:
        story = (
            f"{first_name} пригласил(а) {second_name} "
            "на променад в парке. Однако он(а) не посмотрел(а) "
            "прогноз погоды, и их лавочку унесло волной."
        )

    elif scenario == 3:
        if gifts:
            gift = random.choice(gifts)
        else:
            gift = "полевой букетик"

        story = (
            f"{first_name} подарил(а) {second_name} "
            f"{gift}. Они отправились за город, "
            "где провели весь день, разговаривая обо всём на свете."
        )

    elif scenario == 4:
        third, fourth = random.sample(remaining, 2)
        third_name = third[0]
        fourth_name = fourth[0]

        story = (
            f"{first_name} пригласил(а) {second_name} "
            "поиграть в монополию с друзьями. Через 2 часа "
            f"они с {third_name} и {fourth_name} устроили "
            "драку за последнюю свободную улицу."
        )

    elif scenario == 5:
        story = (
            f"{first_name} пригласил(а) {second_name} "
            "провести время на рыбалке. Выпито пива — 5 литров, "
            "поймано рыбы — 0 шт."
        )

    elif scenario == 6:
        story = (
            f"{first_name} пригласил(а) {second_name} "
            "в комнату кривых зеркал. "
            f"{second_name} начал(а) смеяться над {first_name} "
            "до того, как они вошли в комнату. "
            "В следующий раз первый персонаж подумает над выбором дважды."
        )

    elif scenario == 7:
        story = (
            f"{first_name} пригласил(а) {second_name} "
            "пойти вместе по грибы. Собрали всё — крапиву, "
            "чертополох, клещей и поганки. Оба согласились "
            "как-нибудь повторить."
        )

    elif scenario == 8:
        story = (
            f"{first_name} и {second_name} решили приготовить "
            "вместе ужин. Всё вышло так слащаво и мило, что аж тошно."
        )

    elif scenario == 9:
        story = (
            f"{first_name} пригласил(а) {second_name} потанцевать. "
            f"{second_name} знает, что {first_name} не умеет танцевать, "
            "просто хочет проводить больше времени вместе."
        )

    elif scenario == 10:
        third = random.choice(remaining)
        third_name = third[0]

        story = (
            f"{first_name} написал(а) {second_name}, "
            "что очень хочет увидеться. "
            f"{second_name} получил(а) сообщение, "
            f"находясь на свидании с {third_name}."
        )

    elif scenario == 11:
        story = (
            f"{first_name} пригласил(а) {second_name} "
            "в ресторан и предложил(а) разделить счёт пополам. "
            "Кажется, второго свидания не будет."
        )

    elif scenario == 12:
        story = (
            f"{first_name} и {second_name} отправились "
            "на романтическую прогулку. Вечер закончился "
            "неожиданно, но оба решили, что это было незабываемо."
        )

    elif scenario == 13:
        story = (
            f"{first_name} приготовил(а) для {second_name} "
            "романтический ужин при свечах. Потому что в подвале "
            f"{first_name} других источников света не было."
        )

    elif scenario == 14:
        third = random.choice(remaining)
        third_name = third[0]

        story = (
            f"Во время свидания к {first_name} и {second_name} "
            f"подошёл {third_name} и сообщил, что они прекрасно "
            "смотрятся вместе. После этого он попросил у них "
            "денег на билет домой."
        )

    elif scenario == 15:
        story = (
            f"{first_name} предложил(а) {second_name} пойти туда, "
            "куда глаза глядят. Через два часа они уже танцевали "
            "и произносили тост на чужой свадьбе."
        )

    elif scenario == 16:
        story = (
            f"{first_name} и {second_name} случайно встретились "
            "после долгой разлуки, и между ними пробежала искра. "
            "Они решили начать всё сначала, но уже через пять минут "
            "вспомнили, почему расстались."
        )

    elif scenario == 17:
        third = random.choice(remaining)
        third_name = third[0]

        story = (
            f"{first_name} пригласил(а) {second_name} на свидание, "
            f"но по дороге они встретили {third_name}. "
            "В итоге все трое отправились ужинать, а "
            f"{first_name} весь вечер пытался понять, "
            "кто с кем вообще встречается."
        )

    elif scenario == 18:
        story = (
            f"{first_name} настолько сильно хотел(а) увидеть "
            f"{second_name}, что за неделю совершенно случайно "
            "встретил(а) его в магазине, парке, аптеке и у себя дома. "
            f"{second_name} начал(а) подозревать, что совпадения не случайны."
        )

    elif scenario == 19:
        story = (
            f"{first_name} сказал(а) {second_name}, что ему(ей) "
            "нужно переустановить винду, и надел(а) самое "
            "привлекательное, что было в шкафу. "
            f"{second_name} намёк не понял(а) и крыл(а) ПК "
            "трёхэтажным матом, потому что винда не хотела активироваться."
        )

    elif scenario == 20:
        third = random.choice(remaining)
        third_name = third[0]

        story = (
            f"{first_name}, {second_name} и {third_name} "
            "решили устроить киновечер. Один хотел мелодраму, "
            "другой — хоррор, третий — боевик. "
            "Вследствие дебатов они решили посмотреть айсберг "
            "и тайные теории по FNaF."
        )

    elif scenario == 21:
        if gifts:
            gift = random.choice(gifts)
        else:
            gift = "полевой букетик"

        story = (
            f"{first_name} пожаловался(ась) {second_name}, "
            "что давно не баловал(а) себя покупками. "
            f"{second_name} вытащил(а) из кармана {gift} "
            "и спросил(а), сойдёт ли это. "
            f"{first_name} очень обрадовался(ась) такому жесту заботы."
        )

    elif scenario == 22:
        third = random.choice(remaining)
        third_name = third[0]

        story = (
            f"{first_name} пригласил(а) {second_name} на ночное "
            "рандеву, чтобы показать кое-что интересное. "
            f"К утру они вернулись очень довольными, но этой ночью "
            f"{third_name} пропал(а) без следа по неизвестным обстоятельствам."
        )

    elif scenario == 23:
        third = random.choice(remaining)
        third_name = third[0]

        story = (
            f"{first_name} пригласил(а) {second_name} романтично "
            "посидеть в подъезде и выпить пару бутылок жигулей. "
            f"Было романтично, пока голубков не выгнал(а) "
            f"{third_name}, живущий(ая) в квартире сверху."
        )

    elif scenario == 24:
        story = (
            f"{first_name} в очередной раз шлепнул(а) {second_name} "
            "по попе и не понимал(а), почему это вызывает такую "
            "негативную реакцию. В следующий раз "
            f"{second_name} точно скажет, что все это время ему(ей) прилетало в поясницу."
        )

    elif scenario == 25:
        story = (
            f"{first_name} пригласил(а) {second_name} на свидание "
            "в дорогой ресторан, но свободных столиков не оказалось, "
            "и пришлось идти во Вкусно — и точка. "
            f"{second_name} облегченно выдохнул(а)."
        )

    message_text = (
        "💞 Случайное свидание:\n\n"
        f"{story}"
    )

    await send_pair_with_photos(
        update,
        first_name,
        second_name,
        character_data,
        message_text
    )

async def match_character(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat_id = update.effective_chat.id

    if not context.args:
        await update.message.reply_text(
            "Укажи имя персонажа.\n"
            "Например: /match Иван"
        )
        return

    requested_name = " ".join(context.args).strip()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name, photo_id FROM characters
        WHERE chat_id = ?
    """, (chat_id,))

    characters = cursor.fetchall()
    conn.close()

    selected = None

    for character in characters:
        if character[0].lower() == requested_name.lower():
            selected = character
            break

    if selected is None:
        await update.message.reply_text(
            f"Персонаж «{requested_name}» не найден.\n"
            "Проверь имя командой /characters."
        )
        return

    partners = [
        character for character in characters
        if character[0].lower() != selected[0].lower()
    ]

    if not partners:
        await update.message.reply_text(
            "Для подбора пары нужен хотя бы один другой персонаж."
        )
        return

    partner = random.choice(partners)

    first_name = selected[0]
    second_name = partner[0]

    character_data = {
        first_name: selected[1],
        second_name: partner[1]
    }

    message_text = (
        "💞 Комитет подобрал пару:\n\n"
        f"{first_name} ❤️ {second_name}"
    )

    await send_pair_with_photos(
        update,
        first_name,
        second_name,
        character_data,
        message_text
    )


def get_chat_gifts(cursor, chat_id):
    cursor.execute("""
        SELECT gifts_mode FROM chats
        WHERE chat_id = ?
    """, (chat_id,))

    result = cursor.fetchone()

    if not result:
        return []

    if result[0] == "standard":
        return STANDARD_GIFTS.copy()

    if result[0] == "custom":
        cursor.execute("""
            SELECT name FROM gifts
            WHERE chat_id = ?
        """, (chat_id,))

        return [row[0] for row in cursor.fetchall()]

    return []


async def pair(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat_id = update.effective_chat.id

    moscow_time = timezone(timedelta(hours=3))
    today = datetime.now(moscow_time).date().isoformat()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT character_1, character_2, gift, gift_phrase
        FROM daily_pairs
        WHERE chat_id = ? AND pair_date = ?
    """, (chat_id, today))

    saved_pair = cursor.fetchone()

    if saved_pair:
        first_name, second_name, saved_gift, saved_phrase = saved_pair

        cursor.execute("""
            SELECT name, photo_id FROM characters
            WHERE chat_id = ?
            AND name IN (?, ?)
        """, (chat_id, first_name, second_name))

        rows = cursor.fetchall()
        character_data = {
            row[0]: row[1] for row in rows
        }

        if (
            first_name not in character_data
            or second_name not in character_data
        ):
            saved_pair = None

    if not saved_pair:
        cursor.execute("""
            SELECT name, photo_id FROM characters
            WHERE chat_id = ?
        """, (chat_id,))

        characters = cursor.fetchall()

        if len(characters) < 2:
            conn.close()
            await update.message.reply_text(
                "Для пары дня нужны хотя бы два разных персонажа.\n"
                "Добавь их командой /add"
            )
            return

        first, second = random.sample(characters, 2)

        first_name = first[0]
        second_name = second[0]

        character_data = {
            first_name: first[1],
            second_name: second[1]
        }

        gifts = get_chat_gifts(cursor, chat_id)

        if gifts:
            gift = random.choice(gifts)
            gift_phrase = random.choice(GIFT_PHRASES).format(
                first=first_name,
                second=second_name,
                gift=gift
            )
        else:
            gift = ""
            gift_phrase = (
                "🎁 Подарок пока не назначен: "
                "проверь настройки набора подарков."
            )

        cursor.execute("""
            INSERT OR REPLACE INTO daily_pairs (
                chat_id,
                pair_date,
                character_1,
                character_2,
                gift,
                gift_phrase
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            chat_id,
            today,
            first_name,
            second_name,
            gift,
            gift_phrase
        ))

    else:
        gift = saved_gift or ""
        gift_phrase = saved_phrase

        if not gift_phrase:
            gifts = get_chat_gifts(cursor, chat_id)

            if gifts:
                gift = random.choice(gifts)
                gift_phrase = random.choice(GIFT_PHRASES).format(
                    first=first_name,
                    second=second_name,
                    gift=gift
                )
            else:
                gift = ""
                gift_phrase = (
                    "🎁 Подарок пока не назначен: "
                    "проверь настройки набора подарков."
                )

            cursor.execute("""
                UPDATE daily_pairs
                SET gift = ?, gift_phrase = ?
                WHERE chat_id = ? AND pair_date = ?
            """, (gift, gift_phrase, chat_id, today))

    conn.commit()
    conn.close()

    message_text = (
        "💌 Пара дня:\n\n"
        f"{first_name} ❤️ {second_name}\n\n"
        f"{gift_phrase}"
    )

    await send_pair_with_photos(
        update,
        first_name,
        second_name,
        character_data,
        message_text
    )


def main():
    init_database()

    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(setup_commands)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("info", info_command))
    app.add_handler(CommandHandler("myid", my_id))

    app.add_handler(CommandHandler("add", add_character))
    app.add_handler(CommandHandler("addphoto", add_character_photo))
    app.add_handler(CommandHandler("delete", delete_character))
    app.add_handler(CommandHandler("characters", show_characters))

    app.add_handler(CommandHandler("standard", choose_standard))
    app.add_handler(CommandHandler("custom", choose_custom))
    app.add_handler(CommandHandler("gifts", show_gifts))
    app.add_handler(CommandHandler("addgift", add_gift))
    app.add_handler(CommandHandler("deletegift", delete_gift))

    app.add_handler(CommandHandler("random", random_pair))
    app.add_handler(CommandHandler("match", match_character))
    app.add_handler(CommandHandler("pair", pair))

    app.add_handler(
        MessageHandler(filters.PHOTO, save_character_photo)
    )

    print("Комитет союзов запущен!")

    app.run_polling()


if __name__ == "__main__":
    main()
