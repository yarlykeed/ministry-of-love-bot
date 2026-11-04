from sqlalchemy.orm import Session

from ministry.models import Chat, GiftsMode


def get_or_create_chat(session: Session, chat_id: int) -> Chat:
    chat = session.get(Chat, chat_id)

    if chat is None:
        chat = Chat(id=chat_id, gifts_mode=GiftsMode.UNSET)
        session.add(chat)
        session.flush()

    return chat


def set_gifts_mode(session: Session, chat_id: int, mode: GiftsMode) -> None:
    chat = get_or_create_chat(session, chat_id)
    chat.gifts_mode = mode
