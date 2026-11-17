"""Tests for game.py. Run with: python -m unittest discover -s tests -v"""

import random
import unittest
from datetime import date
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game import (
    CardState,
    Progress,
    level_for_xp,
    load_cards,
    make_quiz_question,
)


class TestCards(unittest.TestCase):
    def test_loads_97_cards(self):
        cards = load_cards()
        self.assertEqual(len(cards), 97)

    def test_deck_counts(self):
        cards = load_cards()
        counts = {}
        for card in cards:
            counts[card.deck] = counts.get(card.deck, 0) + 1
        self.assertEqual(counts, {"dsa": 36, "sys": 33, "genai": 20, "stories": 8})

    def test_every_card_has_title_front_back(self):
        for card in load_cards():
            self.assertTrue(card.title)
            self.assertTrue(card.front)
            self.assertTrue(card.back)

    def test_ids_unique(self):
        ids = [c.id for c in load_cards()]
        self.assertEqual(len(ids), len(set(ids)))


class TestLevels(unittest.TestCase):
    def test_level_thresholds(self):
        self.assertEqual(level_for_xp(0), 1)
        self.assertEqual(level_for_xp(99), 1)
        self.assertEqual(level_for_xp(100), 2)
        self.assertEqual(level_for_xp(250), 3)


class TestReview(unittest.TestCase):
    def test_unreviewed_card_is_due(self):
        self.assertTrue(CardState().is_due(date(2026, 11, 17)))

    def test_good_advances_interval(self):
        state = CardState()
        xp = state.record_review("good", date(2026, 11, 17))
        self.assertEqual(xp, 10)
        self.assertEqual(state.due, "2026-11-20")  # 3 days later
        self.assertFalse(state.is_due(date(2026, 11, 17)))
        self.assertTrue(state.is_due(date(2026, 11, 20)))

    def test_again_restarts_at_one_day(self):
        state = CardState(interval_index=3, due="2026-12-01", reviews=5)
        xp = state.record_review("again", date(2026, 11, 17))
        self.assertEqual(xp, 0)
        self.assertEqual(state.due, "2026-11-18")
        self.assertEqual(state.interval_index, 0)

    def test_easy_jumps_two_steps(self):
        state = CardState()
        xp = state.record_review("easy", date(2026, 11, 17))
        self.assertEqual(xp, 15)
        self.assertEqual(state.due, "2026-11-24")  # 7 days later

    def test_bad_rating_rejected(self):
        with self.assertRaises(ValueError):
            CardState().record_review("perfect", date(2026, 11, 17))


class TestQuiz(unittest.TestCase):
    def test_question_has_four_options_with_correct_title(self):
        cards = load_cards()
        rng = random.Random(42)
        question = make_quiz_question(cards[0], cards, rng)
        self.assertEqual(len(question.options), 4)
        self.assertEqual(len(set(question.options)), 4)
        self.assertEqual(question.correct_title, cards[0].title)
        self.assertIn(cards[0].title, question.options)

    def test_quiz_deterministic_with_seed(self):
        cards = load_cards()
        q1 = make_quiz_question(cards[5], cards, random.Random(7))
        q2 = make_quiz_question(cards[5], cards, random.Random(7))
        self.assertEqual(q1.options, q2.options)


class TestProgress(unittest.TestCase):
    def test_streak_and_accuracy(self):
        progress = Progress()
        progress.record_answer(True)
        progress.record_answer(True)
        progress.record_answer(False)
        self.assertEqual(progress.streak, 0)
        self.assertEqual(progress.best_streak, 2)
        self.assertEqual(progress.accuracy, 66.7)

    def test_save_and_load_roundtrip(self, tmp_path=None):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "progress.json"
            progress = Progress(xp=150, streak=3)
            progress.set_card_state(1, CardState(interval_index=2, due="2026-11-24", reviews=2))
            progress.save(path)
            loaded = Progress.load(path)
            self.assertEqual(loaded.xp, 150)
            self.assertEqual(loaded.level, 2)
            self.assertEqual(loaded.card_state(1).due, "2026-11-24")


if __name__ == "__main__":
    unittest.main()
