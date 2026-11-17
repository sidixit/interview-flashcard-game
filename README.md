# Interview Flashcard Game

A quiz game built from Sid's Anki interview deck: 97 cards across 4 subdecks.

- **DSA Patterns** (36 cards) - NeetCode 150 / Blind 75 patterns, plus Number of Islands, Moving Ones, GEICO topo sort and impact analysis
- **System Design - Primer** (33 cards) - System Design Primer topics (CAP, sharding, caching, load balancing) plus the CTGT policy engine and R1 hospital billing designs
- **Backend and GenAI** (20 cards) - continuous batching, KV cache, RAG, guardrails, Kafka, outbox pattern
- **My Stories** (8 cards) - Business Education merge, partner self-serve tool, Instagram beta

Everything here is Python. The web app is Streamlit (pure Python), the terminal game is plain Python with no dependencies, and the game logic lives in `game.py`, shared by both.

## How to play

### Web app (recommended)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL it prints (usually http://localhost:8501).

Three modes:

- **Review Due** - only the cards due today, on the Anki schedule: 1 day, 3 days, 1 week, 2 weeks, 1 month. Rate each card Again / Hard / Good / Easy.
- **Flip** - the whole deck (or one subdeck), shuffled. Reveal the answer, rate yourself.
- **Quiz** - read a description, pick the right concept from 4 options.

Scoring: Flip gives Again 0, Hard 5, Good 10, Easy 15 XP. Quiz gives 20 XP for a correct answer, 2 XP for a wrong one. Every 100 XP is a level up. Streaks count consecutive correct answers.

Progress (XP, level, streak, review dates) saves to `progress.json` next to the app.

### Terminal game

No installs needed, just Python 3.10+:

```bash
python play.py            # flip mode, all decks
python play.py quiz       # quiz mode
python play.py review     # only cards due today
python play.py --deck sys # only the System Design deck
```

Rate cards with 1 Again, 2 Hard, 3 Good, 4 Easy. Press q to quit; progress is saved on every answer.

### Deploy the web app for free

Streamlit Community Cloud runs this repo directly: sign in at share.streamlit.io, point it at this repo, set the main file to `app.py`, and deploy. No other setup needed.

## Files

- `app.py` - Streamlit web app
- `play.py` - terminal game
- `game.py` - shared game logic: cards, quiz generation, spaced repetition, XP and levels, progress saving
- `cards.json` - the 97 cards (title, prompt, answer, deck, tags)
- `tests/test_game.py` - tests for the game logic

## Tests

```bash
python -m unittest discover -s tests -v
```

## Where the cards came from

The cards are the same content as the Anki deck `Sid-Technical-Interview.apkg` (97 cards), built from the System Design Primer (donnemartin/system-design-primer), the NeetCode 150 / Blind 75 list (zoekurtzer/Leetcode-Study), and Sid's own interview prep (CTGT policy engine, R1 hospital billing, GEICO drills, moving-ones). See `cards.json` for the full question bank.
