# Ministry of Love bot

A Telegram bot for group chats that plays matchmaker. Members add
characters (people from the chat, fictional heroes, anyone), and the bot
picks a "pair of the day", makes up random dates and finds a match for a
given character. Pairs come with a gift taken from a gift set the chat
picks. The bot replies in Russian.

## Running

### 1. Create the bot and fill in `.env`

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy its token.
2. Copy `.env.example` to `.env` and set `TOKEN` to that token.
3. Leave `OWNER_ID` empty for now and start the bot (next step).
4. Send `/myid` to the bot and put the number it replies with into
   `OWNER_ID`, then restart. After that, `/myid` answers only you, and it
   shows up in your command menu only.

| Variable       | Required | Default                       | Meaning                          |
|----------------|----------|-------------------------------|----------------------------------|
| `TOKEN`        | yes      | —                             | Bot token from @BotFather        |
| `OWNER_ID`     | no       | empty (anyone can use /myid)  | Your Telegram user ID            |
| `DATABASE_URL` | no       | `sqlite:///data/committee.db` | Any SQLAlchemy URL               |

### 2a. Run with Docker (recommended)

```sh
docker compose up -d --build
docker compose logs -f bot
```

The SQLite database lives in the `bot-data` volume (`/app/data` in the
container), so it survives rebuilds. The container restarts on its own
unless you stop it.

### 2b. Run locally

Requires Python 3.12+ (the code uses `enum.StrEnum`).

```sh
python -m venv .venv
.venv\Scripts\activate        # Windows; on Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

The database is created at `data/committee.db` next to `bot.py`.

Run only one copy of the bot per token. Telegram allows a single
long-polling client, so a local copy and a Docker copy running at the
same time will fight over updates.

## Using it in a chat

Add the bot to a group, then:

1. `/start` — the first time, the bot asks you to choose a gift set.
2. `/standard` for the built-in gifts, or `/custom` to build your own
   with `/addgift <name>` and `/deletegift <name>`.
3. `/add <name>` to add characters. After adding one, the bot asks for a
   photo: reply to that message with a picture to attach it. Use
   `/addphoto <name>` to add or replace a photo later.
4. Play: `/pair`, `/random`, `/match <name>`.

### Commands

| Command              | What it does                                         |
|----------------------|------------------------------------------------------|
| `/start`             | Greeting; asks for a gift set if none is chosen      |
| `/help`, `/info`     | Command list, about the bot                          |
| `/pair`              | Pair of the day                                      |
| `/random`            | A random date story                                  |
| `/match <name>`      | Random partner for the given character               |
| `/add <name>`        | Add a character (then reply with a photo)            |
| `/addphoto <name>`   | Ask for a new photo for a character                  |
| `/delete <name>`     | Delete a character                                   |
| `/characters`        | List characters                                      |
| `/gifts`             | Show the current gift set                            |
| `/standard`          | Use the built-in gift set                            |
| `/custom`            | Use the chat's own gift set                          |
| `/addgift <name>`    | Add a gift (custom set only)                         |
| `/deletegift <name>` | Delete a gift (custom set only)                      |
| `/myid`              | Your Telegram ID (owner only once `OWNER_ID` is set) |

## How it works

### Everything is per chat

Every group has its own characters, gift set and pair of the day. The
chat ID is the key for all stored data.

Names of characters and gifts are compared case-insensitively, with
extra whitespace collapsed (`normalize_name` in
[ministry/models.py](ministry/models.py)), so `/delete иван  петров`
finds "Иван Петров". Names must be unique within a chat. Limits: 64
characters for a character name, 100 for a gift.

### Gift sets

A chat starts with no gift set (`unset`). `/standard` switches it to the
built-in list in [ministry/content.py](ministry/content.py); `/custom`
switches it to the chat's own gifts stored in the database. Switching
back to standard keeps the custom gifts, so you can return to them.
Gifts can only be added or deleted while the chat is in custom mode.

### Pair of the day (`/pair`)

The first `/pair` of a day picks two random characters and a gift
phrase and saves them (one `daily_pairs` row per chat, overwritten each
day). Later calls that day return the same pair. The day changes at
midnight Moscow time (UTC+3, `PAIR_TIMEZONE` in
[ministry/constants.py](ministry/constants.py)). If one of the two
characters is deleted, the pair is deleted with it, and the next `/pair`
picks a new one.

If no gift set is chosen, or the custom set is empty, the pair gets a
"no gift" line instead of a gift.

### Random date (`/random`)

Needs at least two characters. Each call rolls:

- 10% — a character goes on a date with themselves;
- 10% — a character stays home;
- 80% — a story from `DATE_SCENARIOS`. Some scenarios need 3 or 4
  characters and are only picked when the chat has that many. If there
  are no gifts, a fallback gift ("полевой букетик") is used.

Nothing is saved; every call is a new roll. The odds and stories are in
[ministry/content.py](ministry/content.py).

### Match (`/match <name>`)

Pairs the named character with a random other character. Nothing is
saved.

### Photos

When a character has a photo, results include it: two photos are sent as
an album with the text as the caption, one photo as a captioned picture.
The bot stores only Telegram's `file_id`, not the image.

A photo is accepted only when it is a reply to the bot's latest
"send a photo" message for that user in that chat. These pending
requests are kept in memory, so they are lost when the bot restarts;
run `/addphoto <name>` again in that case.

## Code layout

```
bot.py                  entry point: logging, DB init, handlers, polling
ministry/
  constants.py          settings read from .env
  db.py                 SQLAlchemy engine and sessions; creates tables on start
  models.py             tables: chats, characters, gifts, daily_pairs
  texts.py              all bot messages and command descriptions
  content.py            standard gifts, gift phrases, date scenarios, odds
  handlers/             Telegram layer: parse the command, call a service, reply
  services/             logic and database access, no Telegram code
```

Handlers stay thin: they read the command argument, open a session, call
a service and turn its exceptions (`NotFound`, `AlreadyExists`,
`NameTooLong`, ...) from [ministry/services/errors.py](ministry/services/errors.py)
into replies.

Tables are created with `create_all` on startup. There are no
migrations: if you change a model, update the existing database by hand
or delete it.

To change what the bot says, edit [ministry/texts.py](ministry/texts.py).
To add gifts or date stories, edit [ministry/content.py](ministry/content.py).
