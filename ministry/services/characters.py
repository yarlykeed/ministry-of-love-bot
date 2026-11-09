from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ministry.models import MAX_CHARACTER_NAME_LENGTH, Character, normalize_name
from ministry.services.chats import get_or_create_chat
from ministry.services.errors import AlreadyExists, NameTooLong, NotFound


def list_characters(session: Session, chat_id: int) -> list[Character]:
    return list(session.scalars(
        select(Character)
        .where(Character.chat_id == chat_id)
        .order_by(Character.name_key)
    ))


def find_character(
    session: Session, chat_id: int, name: str
) -> Character | None:
    return session.scalar(
        select(Character).where(
            Character.chat_id == chat_id,
            Character.name_key == normalize_name(name),
        )
    )


def add_character(session: Session, chat_id: int, name: str) -> Character:
    if len(name) > MAX_CHARACTER_NAME_LENGTH:
        raise NameTooLong(MAX_CHARACTER_NAME_LENGTH)

    get_or_create_chat(session, chat_id)

    if find_character(session, chat_id, name):
        raise AlreadyExists

    character = Character(chat_id=chat_id, name=name)
    session.add(character)
    session.flush()
    return character


def delete_character(session: Session, chat_id: int, name: str) -> None:
    """Deletes the character; its daily pair goes with it (FK cascade)."""
    result = session.execute(
        delete(Character).where(
            Character.chat_id == chat_id,
            Character.name_key == normalize_name(name),
        )
    )

    if not result.rowcount:
        raise NotFound


def set_photo(
    session: Session, chat_id: int, character_id: int, photo_id: str
) -> None:
    character = session.get(Character, character_id)

    if character is None or character.chat_id != chat_id:
        raise NotFound

    character.photo_id = photo_id
