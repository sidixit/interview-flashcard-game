"""Core game logic for the Interview Flashcard Game.

Pure Python, no third-party dependencies. Both the Streamlit web app
(app.py) and the terminal game (play.py) run on this module.

Cards come from Sid's Anki deck (97 cards: DSA Patterns, System Design
Primer, Backend and GenAI, My Stories). Reviews follow the same
spaced-repetition schedule as the Anki deck: 1 day, 3 days, 1 week,
2 weeks, 1 month.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
CARDS_FILE = HERE / "cards.json"
PROGRESS_FILE = HERE / "progress.json"

# Review intervals in days, matching the Anki deck's schedule.
INTERVALS_DAYS = [1, 3, 7, 14, 30]

# XP awarded per action.
XP_FLIP_GOOD = 10
XP_FLIP_EASY = 15
XP_FLIP_HARD = 5
XP_QUIZ_CORRECT = 20
XP_QUIZ_WRONG = 2

# Level thresholds: level N needs LEVEL_STEP * (N - 1) total XP.
LEVEL_STEP = 100


@dataclass
class Card:
    """One flashcard from the deck."""

    id: int
    deck: str
    deck_name: str
    title: str
    front: str
    back: str
    tags: list = field(default_factory=list)

    @property
    def question(self) -> str:
        """The prompt shown to the player."""
        return self.front

    @property
    def answer(self) -> str:
        """The answer revealed after the prompt."""
        return self.back


def load_cards(path: Path = CARDS_FILE) -> list[Card]:
    """Load all cards from cards.json."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return [Card(**item) for item in raw]


def cards_by_deck(cards: list[Card]) -> dict[str, list[Card]]:
    """Group cards by deck key, preserving deck order."""
    grouped: dict[str, list[Card]] = {}
    for card in cards:
        grouped.setdefault(card.deck, []).append(card)
    return grouped


def level_for_xp(xp: int) -> int:
    """Level from total XP. Level 1 starts at 0 XP, each level is 100 XP."""
    return xp // LEVEL_STEP + 1


def xp_into_level(xp: int) -> int:
    """XP earned toward the current level."""
    return xp % LEVEL_STEP


@dataclass
class CardState:
    """Spaced-repetition state for one card."""

    interval_index: int = 0
    due: str = ""  # ISO date; "" means never reviewed, always due
    reviews: int = 0

    def is_due(self, today: date) -> bool:
        if not self.due:
            return True
        return date.fromisoformat(self.due) <= today

    def record_review(self, rating: str, today: date) -> int:
        """Apply a rating and return the XP earned.

        rating is one of "again", "hard", "good", "easy".
        "again" restarts the card at the 1-day interval.
        """
        self.reviews += 1
        if rating == "again":
            self.interval_index = 0
            xp = 0
        elif rating == "hard":
            self.interval_index = max(0, self.interval_index - 1)
            xp = XP_FLIP_HARD
        elif rating == "good":
            self.interval_index = min(len(INTERVALS_DAYS) - 1, self.interval_index + 1)
            xp = XP_FLIP_GOOD
        elif rating == "easy":
            self.interval_index = min(len(INTERVALS_DAYS) - 1, self.interval_index + 2)
            xp = XP_FLIP_EASY
        else:
            raise ValueError(f"unknown rating: {rating!r}")
        self.due = (today + timedelta(days=INTERVALS_DAYS[self.interval_index])).isoformat()
        return xp


@dataclass
class Progress:
    """Player progress, saved to progress.json."""

    xp: int = 0
    streak: int = 0  # consecutive correct quiz answers / good+ flip ratings
    best_streak: int = 0
    answered: int = 0
    correct: int = 0
    last_played: str = ""  # ISO date
    cards: dict = field(default_factory=dict)  # card id (str) -> CardState dict

    @property
    def level(self) -> int:
        return level_for_xp(self.xp)

    @property
    def accuracy(self) -> float:
        if not self.answered:
            return 0.0
        return round(100 * self.correct / self.answered, 1)

    def card_state(self, card_id: int) -> CardState:
        raw = self.cards.get(str(card_id))
        if raw is None:
            return CardState()
        return CardState(**raw)

    def set_card_state(self, card_id: int, state: CardState) -> None:
        self.cards[str(card_id)] = {
            "interval_index": state.interval_index,
            "due": state.due,
            "reviews": state.reviews,
        }

    def add_xp(self, amount: int) -> None:
        self.xp += amount

    def record_answer(self, was_correct: bool) -> None:
        self.answered += 1
        if was_correct:
            self.correct += 1
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
        else:
            self.streak = 0

    def due_cards(self, cards: list[Card], today: date) -> list[Card]:
        """Cards due for review today, shuffled."""
        due = [c for c in cards if self.card_state(c.id).is_due(today)]
        random.shuffle(due)
        return due

    def save(self, path: Path = PROGRESS_FILE) -> None:
        data = {
            "xp": self.xp,
            "streak": self.streak,
            "best_streak": self.best_streak,
            "answered": self.answered,
            "correct": self.correct,
            "last_played": self.last_played,
            "cards": self.cards,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: Path = PROGRESS_FILE) -> "Progress":
        if not path.exists():
            return cls()
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            xp=data.get("xp", 0),
            streak=data.get("streak", 0),
            best_streak=data.get("best_streak", 0),
            answered=data.get("answered", 0),
            correct=data.get("correct", 0),
            last_played=data.get("last_played", ""),
            cards=data.get("cards", {}),
        )


@dataclass
class QuizQuestion:
    """One multiple-choice question built from a card."""

    card: Card
    clue: str  # the card's answer text, shown as the clue
    options: list[str]  # card titles, one is correct
    correct_index: int

    @property
    def correct_title(self) -> str:
        return self.options[self.correct_index]


def make_quiz_question(
    card: Card, pool: list[Card], rng: random.Random | None = None
) -> QuizQuestion:
    """Build a quiz question: show the card's answer, pick its title.

    Distractors are titles of other cards from the same deck when
    possible, falling back to any other deck.
    """
    rng = rng or random.Random()
    same_deck = [c for c in pool if c.deck == card.deck and c.id != card.id]
    others = [c for c in pool if c.id != card.id]
    candidates = same_deck if len(same_deck) >= 3 else others
    distractors = rng.sample([c.title for c in candidates], k=min(3, len(candidates)))
    options = distractors + [card.title]
    rng.shuffle(options)
    return QuizQuestion(
        card=card,
        clue=card.back,
        options=options,
        correct_index=options.index(card.title),
    )


def shuffled_deck(cards: list[Card], rng: random.Random | None = None) -> list[Card]:
    """A shuffled copy of the card list, for Flip mode."""
    rng = rng or random.Random()
    deck = list(cards)
    rng.shuffle(deck)
    return deck
