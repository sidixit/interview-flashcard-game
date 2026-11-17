"""Interview Flashcard Game - Streamlit web app.

Play the 97 cards from Sid's Anki deck as a game: Flip mode, Quiz mode,
and a daily Review queue that follows the Anki schedule (1 day, 3 days,
1 week, 2 weeks, 1 month). Progress (XP, level, streak, review dates)
is saved to progress.json next to this file.

Run it with:  streamlit run app.py
"""

from __future__ import annotations

import random
from datetime import date

import streamlit as st

from game import (
    LEVEL_STEP,
    Card,
    Progress,
    load_cards,
    make_quiz_question,
    shuffled_deck,
    xp_into_level,
)

ALL_CARDS = load_cards()
DECKS = [
    ("all", "All decks"),
    ("dsa", "DSA Patterns"),
    ("sys", "System Design - Primer"),
    ("genai", "Backend and GenAI"),
    ("stories", "My Stories"),
]
DECK_NAMES = dict(DECKS)


def get_progress() -> Progress:
    if "progress" not in st.session_state:
        st.session_state.progress = Progress.load()
    return st.session_state.progress


def save_progress() -> None:
    get_progress().save()


def filtered_cards(deck_key: str) -> list[Card]:
    if deck_key == "all":
        return ALL_CARDS
    return [c for c in ALL_CARDS if c.deck == deck_key]


def new_flip_queue(deck_key: str) -> None:
    st.session_state.flip_queue = shuffled_deck(filtered_cards(deck_key))
    st.session_state.flip_index = 0
    st.session_state.revealed = False


def new_quiz_question(deck_key: str) -> None:
    pool = filtered_cards(deck_key)
    card = random.choice(pool)
    st.session_state.quiz = make_quiz_question(card, pool)
    st.session_state.quiz_answered = None


def show_stats(progress: Progress, deck_key: str) -> None:
    today = date.today()
    due = len(progress.due_cards(filtered_cards(deck_key), today))
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Level", progress.level)
    col2.metric("XP", f"{progress.xp}  ({xp_into_level(progress.xp)}/{LEVEL_STEP} to next level)")
    col3.metric("Streak", f"{progress.streak}  (best {progress.best_streak})")
    col4.metric("Due today", due)
    st.progress(xp_into_level(progress.xp) / LEVEL_STEP)
    st.caption(f"Accuracy so far: {progress.accuracy}% over {progress.answered} answers.")


def flip_mode(deck_key: str) -> None:
    progress = get_progress()
    if "flip_queue" not in st.session_state:
        new_flip_queue(deck_key)
    queue = st.session_state.flip_queue
    idx = st.session_state.flip_index
    if idx >= len(queue):
        st.success("Deck complete! Shuffle and go again, or switch to Quiz mode.")
        if st.button("Shuffle deck"):
            new_flip_queue(deck_key)
            st.rerun()
        return
    card = queue[idx]
    st.subheader(f"Card {idx + 1} of {len(queue)} - {card.deck_name}")
    st.markdown(f"**{card.front}**")
    if not st.session_state.revealed:
        if st.button("Reveal answer"):
            st.session_state.revealed = True
            st.rerun()
    else:
        st.divider()
        st.markdown(card.back)
        st.write("How well did you know it?")
        col1, col2, col3, col4 = st.columns(4)
        rating = None
        if col1.button("Again"):
            rating = "again"
        if col2.button("Hard"):
            rating = "hard"
        if col3.button("Good"):
            rating = "good"
        if col4.button("Easy"):
            rating = "easy"
        if rating:
            state = progress.card_state(card.id)
            xp = state.record_review(rating, date.today())
            progress.set_card_state(card.id, state)
            progress.add_xp(xp)
            progress.record_answer(rating in ("good", "easy"))
            progress.last_played = date.today().isoformat()
            save_progress()
            st.session_state.flip_index += 1
            st.session_state.revealed = False
            if xp:
                st.toast(f"+{xp} XP")
            st.rerun()


def quiz_mode(deck_key: str) -> None:
    progress = get_progress()
    if "quiz" not in st.session_state:
        new_quiz_question(deck_key)
    question = st.session_state.quiz
    answered = st.session_state.quiz_answered
    st.subheader(f"Quiz - {question.card.deck_name}")
    st.write("Which concept does this describe?")
    st.markdown(question.clue)
    for i, option in enumerate(question.options):
        label = option
        if answered is not None:
            if i == question.correct_index:
                label = f"{option}  - correct"
            elif i == answered:
                label = f"{option}  - your pick"
        if st.button(label, key=f"quiz-opt-{i}", disabled=answered is not None):
            st.session_state.quiz_answered = i
            correct = i == question.correct_index
            progress.record_answer(correct)
            progress.add_xp(20 if correct else 2)
            progress.last_played = date.today().isoformat()
            save_progress()
            st.rerun()
    if answered is not None:
        if answered == question.correct_index:
            st.success("Correct! +20 XP")
        else:
            st.error(f"Not quite. The answer was: {question.correct_title} (+2 XP)")
        if st.button("Next question"):
            new_quiz_question(deck_key)
            st.rerun()


def review_mode(deck_key: str) -> None:
    progress = get_progress()
    today = date.today()
    due = progress.due_cards(filtered_cards(deck_key), today)
    if not due:
        st.success("All caught up! No cards are due today.")
        st.write("Come back tomorrow, or play Flip or Quiz mode in the meantime.")
        return
    st.write(f"{len(due)} card(s) due today. Same as Flip mode, but only the due ones.")
    if "review_queue" not in st.session_state or st.session_state.get("review_deck") != deck_key:
        st.session_state.review_queue = due
        st.session_state.review_index = 0
        st.session_state.review_revealed = False
        st.session_state.review_deck = deck_key
    queue = st.session_state.review_queue
    idx = st.session_state.review_index
    if idx >= len(queue):
        st.success("Review complete! All due cards done for today.")
        if st.button("Start over"):
            st.session_state.pop("review_queue", None)
            st.rerun()
        return
    card = queue[idx]
    st.subheader(f"Review {idx + 1} of {len(queue)} - {card.deck_name}")
    st.markdown(f"**{card.front}**")
    if not st.session_state.review_revealed:
        if st.button("Reveal answer"):
            st.session_state.review_revealed = True
            st.rerun()
    else:
        st.divider()
        st.markdown(card.back)
        st.write("How well did you know it?")
        col1, col2, col3, col4 = st.columns(4)
        rating = None
        if col1.button("Again"):
            rating = "again"
        if col2.button("Hard"):
            rating = "hard"
        if col3.button("Good"):
            rating = "good"
        if col4.button("Easy"):
            rating = "easy"
        if rating:
            state = progress.card_state(card.id)
            xp = state.record_review(rating, today)
            progress.set_card_state(card.id, state)
            progress.add_xp(xp)
            progress.record_answer(rating in ("good", "easy"))
            progress.last_played = today.isoformat()
            save_progress()
            st.session_state.review_index += 1
            st.session_state.review_revealed = False
            if xp:
                st.toast(f"+{xp} XP")
            st.rerun()


def main() -> None:
    st.set_page_config(page_title="Interview Flashcard Game", page_icon="🃏")
    st.title("Interview Flashcard Game")
    st.caption("97 cards from the Anki deck: DSA, System Design Primer, Backend and GenAI, My Stories.")
    progress = get_progress()
    deck_key = st.sidebar.selectbox("Deck", [k for k, _ in DECKS], format_func=lambda k: DECK_NAMES[k])
    mode = st.sidebar.radio("Mode", ["Review Due", "Flip", "Quiz"])
    if st.sidebar.button("Shuffle / new question"):
        st.session_state.pop("flip_queue", None)
        st.session_state.pop("review_queue", None)
        new_quiz_question(deck_key)
        st.rerun()
    show_stats(progress, deck_key)
    st.divider()
    if mode == "Flip":
        flip_mode(deck_key)
    elif mode == "Quiz":
        quiz_mode(deck_key)
    else:
        review_mode(deck_key)
    st.divider()
    st.caption("Levels: 100 XP per level. Flip: Again 0, Hard 5, Good 10, Easy 15 XP. Quiz: correct 20 XP, wrong 2 XP.")


if __name__ == "__main__":
    main()
