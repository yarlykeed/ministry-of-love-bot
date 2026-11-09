"""Matchmaking: pair of the day, random dates and matches."""

import random
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from ministry import texts
from ministry.content import (
    DATE_SCENARIOS,
    FALLBACK_DATE_GIFT,
    GIFT_PHRASES,
    SELF_DATE_CHANCE,
    STAY_HOME_CHANCE,
)
from ministry.models import Character, DailyPair, normalize_name
from ministry.services.characters import list_characters
from ministry.services.errors import NotEnoughCharacters, NotFound
from ministry.services.gifts import get_gift_pool

_rng = random.Random()


@dataclass(frozen=True)
class DateResult:
    text: str
    photos: tuple[str, ...]


def _photos(*characters: Character) -> tuple[str, ...]:
    """Unique photo file IDs of the given characters, in order."""
    return tuple(dict.fromkeys(c.photo_id for c in characters if c.photo_id))


def compose_random_date(
    characters: Sequence[Character],
    gifts: Sequence[str],
    rng: random.Random = _rng,
) -> DateResult:
    if len(characters) < 2:
        raise NotEnoughCharacters

    roll = rng.random()

    if roll < SELF_DATE_CHANCE:
        character = rng.choice(characters)
        return DateResult(
            texts.SELF_DATE.format(name=character.name), _photos(character)
        )

    if roll < SELF_DATE_CHANCE + STAY_HOME_CHANCE:
        character = rng.choice(characters)
        return DateResult(
            texts.STAY_HOME_DATE.format(name=character.name),
            _photos(character),
        )

    scenario = rng.choice([
        scenario for scenario in DATE_SCENARIOS
        if scenario.min_characters <= len(characters)
    ])
    first, second, *extras = rng.sample(
        list(characters), scenario.min_characters
    )

    story = scenario.template.format(
        first=first.name,
        second=second.name,
        gift=rng.choice(gifts) if gifts else FALLBACK_DATE_GIFT,
        **dict(zip(("third", "fourth"), (c.name for c in extras))),
    )

    return DateResult(
        texts.RANDOM_DATE.format(story=story), _photos(first, second)
    )


def random_date(
    session: Session, chat_id: int, rng: random.Random = _rng
) -> DateResult:
    characters = list_characters(session, chat_id)
    gifts = get_gift_pool(session, chat_id) or []
    return compose_random_date(characters, gifts, rng)


def match_character(
    session: Session,
    chat_id: int,
    name: str,
    rng: random.Random = _rng,
) -> DateResult:
    characters = list_characters(session, chat_id)
    key = normalize_name(name)

    selected = next((c for c in characters if c.name_key == key), None)

    if selected is None:
        raise NotFound

    partners = [c for c in characters if c is not selected]

    if not partners:
        raise NotEnoughCharacters

    partner = rng.choice(partners)

    return DateResult(
        texts.MATCH_RESULT.format(first=selected.name, second=partner.name),
        _photos(selected, partner),
    )


def daily_pair(
    session: Session,
    chat_id: int,
    today: date,
    rng: random.Random = _rng,
) -> DateResult:
    """Returns today's pair, rolling a new one if there is none yet."""
    pair = session.get(DailyPair, chat_id)

    if pair is None or pair.day != today:
        characters = list_characters(session, chat_id)

        if len(characters) < 2:
            raise NotEnoughCharacters

        first, second = rng.sample(characters, 2)
        gifts = get_gift_pool(session, chat_id)

        if gifts:
            gift_phrase = rng.choice(GIFT_PHRASES).format(
                first=first.name, second=second.name, gift=rng.choice(gifts)
            )
        else:
            gift_phrase = texts.PAIR_NO_GIFT

        if pair is None:
            pair = DailyPair(chat_id=chat_id)
            session.add(pair)

        pair.day = today
        pair.first = first
        pair.second = second
        pair.gift_phrase = gift_phrase
        session.flush()

    return DateResult(
        texts.PAIR_RESULT.format(
            first=pair.first.name,
            second=pair.second.name,
            gift_phrase=pair.gift_phrase,
        ),
        _photos(pair.first, pair.second),
    )
