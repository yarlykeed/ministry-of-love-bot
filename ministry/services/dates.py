"""Matchmaking: pair of the day, random dates and matches."""

import random
from collections import Counter, defaultdict
from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import TypeVar

from sqlalchemy.orm import Session

from ministry import texts
from ministry.content import (
    CHARACTER_ROLL_LIMIT,
    DATE_SCENARIOS,
    FALLBACK_DATE_GIFT,
    GIFT_PHRASES,
    MIN_FRESH_SCENARIOS,
    SCENARIO_ROLL_LIMIT,
    SELF_DATE_CHANCE,
    STAY_HOME_CHANCE,
    DateScenario,
)
from ministry.models import Character, DailyPair, normalize_name
from ministry.services.characters import list_characters
from ministry.services.errors import NotEnoughCharacters, NotFound
from ministry.services.gifts import get_gift_pool

_rng = random.Random()

T = TypeVar("T")


@dataclass(frozen=True)
class DateResult:
    text: str
    photos: tuple[str, ...]


@dataclass
class RollHistory:
    """How many times each scenario / character came up in the current round.

    Scenarios are keyed by themselves (frozen dataclasses are hashable),
    characters by their ID. Kept in memory only: a restart starts new rounds.
    """

    scenarios: Counter[DateScenario] = field(default_factory=Counter)
    characters: Counter[int] = field(default_factory=Counter)


# One history per chat.
_histories: defaultdict[int, RollHistory] = defaultdict(RollHistory)


def _pick(
    rng: random.Random,
    items: Sequence[T],
    k: int,
    counts: Counter,
    key: Callable[[T], Hashable],
    limit: int,
    min_fresh: int = 0,
) -> list[T]:
    """Picks k distinct items, skipping those already rolled `limit` times.

    When fewer than max(k, min_fresh) items are left, the round is over:
    the counts are cleared and every item is back in play.
    """
    fresh = [item for item in items if counts[key(item)] < limit]

    if len(fresh) < max(k, min_fresh):
        counts.clear()
        fresh = list(items)

    picked = rng.sample(fresh, k)
    counts.update(key(item) for item in picked)
    return picked


def _photos(*characters: Character) -> tuple[str, ...]:
    """Unique photo file IDs of the given characters, in order."""
    return tuple(dict.fromkeys(c.photo_id for c in characters if c.photo_id))


def compose_random_date(
    characters: Sequence[Character],
    gifts: Sequence[str],
    rng: random.Random = _rng,
    history: RollHistory | None = None,
) -> DateResult:
    if len(characters) < 2:
        raise NotEnoughCharacters

    if history is None:
        history = RollHistory()

    def pick_characters(k: int) -> list[Character]:
        return _pick(
            rng, characters, k, history.characters,
            key=lambda c: c.id, limit=CHARACTER_ROLL_LIMIT,
        )

    roll = rng.random()

    if roll < SELF_DATE_CHANCE:
        [character] = pick_characters(1)
        return DateResult(
            texts.SELF_DATE.format(name=character.name), _photos(character)
        )

    if roll < SELF_DATE_CHANCE + STAY_HOME_CHANCE:
        [character] = pick_characters(1)
        return DateResult(
            texts.STAY_HOME_DATE.format(name=character.name),
            _photos(character),
        )

    [scenario] = _pick(
        rng,
        [s for s in DATE_SCENARIOS if s.min_characters <= len(characters)],
        1,
        history.scenarios,
        key=lambda s: s,
        limit=SCENARIO_ROLL_LIMIT,
        min_fresh=MIN_FRESH_SCENARIOS,
    )
    first, second, *extras = pick_characters(scenario.min_characters)

    story = scenario.template.format(
        first=first.name,
        second=second.name,
        gift=rng.choice(gifts) if gifts else FALLBACK_DATE_GIFT,
        **dict(zip(("third", "fourth"), (c.name for c in extras))),
    )

    return DateResult(
        texts.RANDOM_DATE.format(story=story),
        _photos(first, second, *extras),
    )


def random_date(
    session: Session, chat_id: int, rng: random.Random = _rng
) -> DateResult:
    characters = list_characters(session, chat_id)
    gifts = get_gift_pool(session, chat_id) or []
    return compose_random_date(characters, gifts, rng, _histories[chat_id])


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
