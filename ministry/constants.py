import os
from datetime import timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TOKEN")

# Telegram ID of the bot owner. Leave empty to let anyone use /myid
# (handy for finding out your own ID during the initial setup).
_owner_id = os.getenv("OWNER_ID", "").strip()
OWNER_ID = int(_owner_id) if _owner_id else None

DATABASE_URL = os.getenv(
    "DATABASE_URL", "sqlite:////data/committee.db"
)

# The daily pair changes at midnight Moscow time.
PAIR_TIMEZONE = timezone(timedelta(hours=3))
