from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ministry.content import STANDARD_GIFTS
from ministry.models import (
    MAX_GIFT_NAME_LENGTH,
    Chat,
    Gift,
    GiftsMode,
    normalize_name,
)
from ministry.services.errors import (
    AlreadyExists,
    CustomGiftsDisabled,
    NameTooLong,
    NotFound,
)


def get_gift_pool(session: Session, chat_id: int) -> list[str] | None:
    """Gifts of the chat's current set, or None if no set was chosen yet."""
    chat = session.get(Chat, chat_id)

    if chat is None or chat.gifts_mode == GiftsMode.UNSET:
        return None

    if chat.gifts_mode == GiftsMode.STANDARD:
        return list(STANDARD_GIFTS)

    return list(session.scalars(
        select(Gift.name)
        .where(Gift.chat_id == chat_id)
        .order_by(Gift.name_key)
    ))


def _require_custom_mode(session: Session, chat_id: int) -> None:
    chat = session.get(Chat, chat_id)

    if chat is None or chat.gifts_mode != GiftsMode.CUSTOM:
        raise CustomGiftsDisabled


def add_gift(session: Session, chat_id: int, name: str) -> None:
    _require_custom_mode(session, chat_id)

    if len(name) > MAX_GIFT_NAME_LENGTH:
        raise NameTooLong(MAX_GIFT_NAME_LENGTH)

    existing = session.scalar(
        select(Gift.id).where(
            Gift.chat_id == chat_id,
            Gift.name_key == normalize_name(name),
        )
    )

    if existing is not None:
        raise AlreadyExists

    session.add(Gift(chat_id=chat_id, name=name))


def delete_gift(session: Session, chat_id: int, name: str) -> None:
    _require_custom_mode(session, chat_id)

    result = session.execute(
        delete(Gift).where(
            Gift.chat_id == chat_id,
            Gift.name_key == normalize_name(name),
        )
    )

    if not result.rowcount:
        raise NotFound
