from datetime import date
from enum import StrEnum

from sqlalchemy import BigInteger, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    validates,
)

MAX_CHARACTER_NAME_LENGTH = 64
MAX_GIFT_NAME_LENGTH = 100


def normalize_name(name: str) -> str:
    """Key for case-insensitive comparison (works for Cyrillic too)."""
    return " ".join(name.split()).casefold()


class GiftsMode(StrEnum):
    UNSET = "unset"
    STANDARD = "standard"
    CUSTOM = "custom"


class Base(DeclarativeBase):
    pass


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False
    )
    gifts_mode: Mapped[GiftsMode] = mapped_column(
        Enum(GiftsMode, native_enum=False, length=16),
        default=GiftsMode.UNSET,
    )


class Character(Base):
    __tablename__ = "characters"
    __table_args__ = (UniqueConstraint("chat_id", "name_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(MAX_CHARACTER_NAME_LENGTH))
    name_key: Mapped[str] = mapped_column(String(MAX_CHARACTER_NAME_LENGTH))
    photo_id: Mapped[str | None] = mapped_column(String)

    @validates("name")
    def _sync_name_key(self, _key: str, value: str) -> str:
        self.name_key = normalize_name(value)
        return value


class Gift(Base):
    __tablename__ = "gifts"
    __table_args__ = (UniqueConstraint("chat_id", "name_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(MAX_GIFT_NAME_LENGTH))
    name_key: Mapped[str] = mapped_column(String(MAX_GIFT_NAME_LENGTH))

    @validates("name")
    def _sync_name_key(self, _key: str, value: str) -> str:
        self.name_key = normalize_name(value)
        return value


class DailyPair(Base):
    """The pair of the day; one row per chat, overwritten every day."""

    __tablename__ = "daily_pairs"

    chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chats.id", ondelete="CASCADE"),
        primary_key=True,
        autoincrement=False,
    )
    day: Mapped[date]
    # Deleting either character deletes the pair, so a new one gets rolled.
    first_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE")
    )
    second_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE")
    )
    gift_phrase: Mapped[str]

    first: Mapped[Character] = relationship(foreign_keys=[first_id])
    second: Mapped[Character] = relationship(foreign_keys=[second_id])
