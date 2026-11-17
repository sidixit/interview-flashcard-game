#!/usr/bin/env python3
"""Interview Flashcard Game - terminal version.

No third-party dependencies, just Python 3.10+.

    python play.py            # flip mode (default)
    python play.py quiz       # quiz mode
    python play.py review     # only cards due today
    python play.py --deck sys # only the System Design deck

Progress (XP, level, streak, review dates) is saved to progress.json
next to this file. Ratings: 1 Again, 2 Hard, 3 Good, 4 Easy.
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import date

from game import (
    Progress,
    load_cards,
    make_quiz_question,
    shuffled_deck,
)

DECKS = {
    "all": "All decks",
    "dsa": "DSA Patterns",
    "sys": "System Design - Primer",
    "genai": "Backend and GenAI",
    "stories": "My Stories",
}


def prompt(text: str) -> str:
    try:
        return input(text).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nGood game. Progress saved.")
        sys.exit(0)


def flip_game(cards, progress: Progress, today: date) -> None:
    queue = shuffled_deck(cards)
    print(f"\nFlip mode: {len(queue)} cards. Press Enter to reveal, then rate 1-4.")
    for i, card in enumerate(queue, start=1):
        print(f"\n--- Card {i}/{len(queue)} [{card.deck_name}] ---")
        print(card.front)
        prompt("Press Enter to reveal... ")
        print(card.back)
        while True:
            rating = prompt("Rate it: 1 Again, 2 Hard, 3 Good, 4 Easy (q to quit): ")
            mapping = {"1": "again", "2": "hard", "3": "good", "4": "easy"}
            if rating == "q":
                progress.save()
                print(f"Saved. Level {progress.level}, {progress.xp} XP, streak {progress.streak}.")
                return
            if rating in mapping:
                break
            print("Pick 1, 2, 3, 4, or q.")
        state = progress.card_state(card.id)
        xp = state.record_review(mapping[rating], today)
        progress.set_card_state(card.id, state)
        progress.add_xp(xp)
        progress.record_answer(mapping[rating] in ("good", "easy"))
        progress.last_played = today.isoformat()
        progress.save()
        print(f"+{xp} XP. Level {progress.level}, total {progress.xp} XP, streak {progress.streak}.")
    print(f"\nDeck complete! Level {progress.level}, {progress.xp} XP.")


def quiz_game(cards, progress: Progress, today: date) -> None:
    rng = random.Random()
    print("\nQuiz mode: read the description, pick the right concept. q to quit.")
    while True:
        card = rng.choice(cards)
        question = make_quiz_question(card, cards, rng)
        print(f"\n[{question.card.deck_name}]")
        print(question.clue)
        for i, option in enumerate(question.options, start=1):
            print(f"  {i}. {option}")
        answer = prompt("Your answer (1-4, q to quit): ")
        if answer == "q":
            progress.save()
            print(f"Saved. Level {progress.level}, {progress.xp} XP, streak {progress.streak}.")
            return
        if answer not in ("1", "2", "3", "4"):
            print("Pick 1-4.")
            continue
        picked = int(answer) - 1
        correct = picked == question.correct_index
        progress.record_answer(correct)
        progress.add_xp(20 if correct else 2)
        progress.last_played = today.isoformat()
        progress.save()
        if correct:
            print(f"Correct! +20 XP. Level {progress.level}, streak {progress.streak}.")
        else:
            print(f"Not quite. It was: {question.correct_title}. +2 XP. Streak reset.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Interview Flashcard Game (terminal)")
    parser.add_argument("mode", nargs="?", default="flip", choices=["flip", "quiz", "review"])
    parser.add_argument("--deck", default="all", choices=list(DECKS))
    args = parser.parse_args()
    all_cards = load_cards()
    cards = all_cards if args.deck == "all" else [c for c in all_cards if c.deck == args.deck]
    progress = Progress.load()
    today = date.today()
    print(f"Interview Flashcard Game - {DECKS[args.deck]}")
    print(f"Level {progress.level}, {progress.xp} XP, streak {progress.streak}, accuracy {progress.accuracy}%.")
    if args.mode == "quiz":
        quiz_game(cards, progress, today)
    elif args.mode == "review":
        due = progress.due_cards(cards, today)
        if not due:
            print("All caught up! No cards due today.")
            return
        print(f"{len(due)} card(s) due today.")
        flip_game(due, progress, today)
    else:
        flip_game(cards, progress, today)


if __name__ == "__main__":
    main()
