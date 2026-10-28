"""Tests for the ProgressTracker kernel (learn_jp/progress.py)."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from learn_jp.progress import (
    ProgressTracker,
    SessionResult,
    ItemReview,
    compute_vocab_status,
    detect_vocab_regression,
)


def _seed_vocab(tracker, count, level="n5", base_id="v"):
    items = [
        {
            "item_id": f"{base_id}{i:03d}",
            "content": f"word{i:03d}",
            "reading": f"よみ{i:03d}",
            "meaning": f"meaning {i}",
            "level": level,
        }
        for i in range(count)
    ]
    tracker.add_items(items)
    return [i["item_id"] for i in items]


def _mark_mastered(tracker, item_ids, level="n5"):
    today = datetime.now().date().isoformat()
    with tracker._connect() as conn:
        for item_id in item_ids:
            conn.execute(
                """INSERT INTO mastery
                   (item_id, item_type, status, streak, last_review_date,
                    total_reviews, correct_reviews)
                   VALUES (?, 'vocabulary', 'mastered', 5, ?, 5, 5)""",
                (item_id, today),
            )
        conn.commit()


def test_add_items_idempotent(temp_db_path, tracker):
    ids = _seed_vocab(tracker, 3)
    inserted = tracker.add_items(
        [
            {"item_id": ids[0], "content": "dup", "meaning": "m", "level": "n5"},
            {"item_id": "new999", "content": "new", "meaning": "m", "level": "n5"},
        ]
    )
    assert inserted == ["new999"]
    with tracker._connect() as conn:
        n = conn.execute("SELECT COUNT(*) FROM vocabulary").fetchone()[0]
    assert n == 4


def test_compute_vocab_status_mastered():
    today = datetime.now().date().isoformat()
    last_week = (datetime.now().date() - timedelta(days=7)).isoformat()
    assert (
        compute_vocab_status(
            streak=5, total_reviews=5, correct_reviews=5,
            last_review_date=last_week, today=today,
        )
        == "mastered"
    )
    assert (
        compute_vocab_status(
            streak=4, total_reviews=5, correct_reviews=5,
            last_review_date=last_week, today=today,
        )
        == "review"
    )
    assert (
        compute_vocab_status(
            streak=5, total_reviews=2, correct_reviews=2,
            last_review_date=last_week, today=today,
        )
        == "learning"
    )


def test_detect_vocab_regression():
    assert detect_vocab_regression("mastered", severity=3, recent_failures=0) is True
    assert detect_vocab_regression("mastered", severity=1, recent_failures=3) is True
    assert detect_vocab_regression("mastered", severity=1, recent_failures=1) is False
    assert detect_vocab_regression("learning", severity=3, recent_failures=5) is False



def test_record_session_updates_streak(temp_db_path, tracker):
    item_id = _seed_vocab(tracker, 1)[0]
    for _ in range(3):
        tracker.record_session(
            SessionResult(
                date="2026-01-01",
                type="anki",
                reviews=[
                    ItemReview(
                        item_id=item_id, item_type="vocabulary", severity=1
                    )
                ],
                items_studied=1,
                correct=1,
            )
        )
    with tracker._connect() as conn:
        row = conn.execute(
            "SELECT streak, total_reviews, status FROM mastery WHERE item_id = ?",
            (item_id,),
        ).fetchone()
    assert row["streak"] == 3
    assert row["total_reviews"] == 3


def test_record_session_failure_resets_streak(temp_db_path, tracker):
    item_id = _seed_vocab(tracker, 1)[0]
    tracker.record_session(
        SessionResult(
            date="2026-01-01",
            type="anki",
            reviews=[
                ItemReview(
                    item_id=item_id, item_type="vocabulary", severity=1
                )
            ],
            items_studied=1,
            correct=1,
        )
    )
    tracker.record_session(
        SessionResult(
            date="2026-01-01",
            type="anki",
            reviews=[
                ItemReview(
                    item_id=item_id, item_type="vocabulary", severity=3
                )
            ],
            items_studied=1,
            correct=0,
        )
    )
    with tracker._connect() as conn:
        streak = conn.execute(
            "SELECT streak FROM mastery WHERE item_id = ?", (item_id,)
        ).fetchone()["streak"]
    assert streak == 0


def test_level_progression_persists_promotion(temp_db_path, tracker):
    ids = _seed_vocab(tracker, 10, level="n5")
    _mark_mastered(tracker, ids, level="n5")

    events = []
    with tracker._connect() as conn:
        tracker._check_level_progression(conn, events)
        conn.commit()

    assert tracker.get_config("current_level") == "n4"
    assert any(e.type == "level_up" for e in events)
    assert any("n5 → n4" in e.detail for e in events)


def test_level_progression_no_promotion_when_incomplete(temp_db_path, tracker):
    _seed_vocab(tracker, 10, level="n5")
    # Master only 5 of 10 (50% < 80% default threshold).
    _mark_mastered(tracker, [f"v{i:03d}" for i in range(5)], level="n5")

    events = []
    with tracker._connect() as conn:
        tracker._check_level_progression(conn, events)
        conn.commit()

    assert tracker.get_config("current_level", "n5") == "n5"
    assert not any(e.type == "level_up" for e in events)


def test_level_progression_promotes_without_grammar(temp_db_path, tracker):
    """Brand-new level with no grammar items should still progress on vocab."""
    _seed_vocab(tracker, 3, level="n5")
    _mark_mastered(tracker, [f"v{i:03d}" for i in range(3)], level="n5")

    events = []
    with tracker._connect() as conn:
        tracker._check_level_progression(conn, events)
        conn.commit()

    assert tracker.get_config("current_level") == "n4"
    assert any(e.type == "level_up" for e in events)


def test_get_status_shape(temp_db_path, tracker):
    _seed_vocab(tracker, 5, level="n5")
    status = tracker.get_status()
    assert status.level == "n5"
    assert status.vocab_total == 5
    assert status.vocab_mastered == 0
    assert status.vocab_percent == 0.0
    assert status.grammar_total == 0
    assert status.grammar_percent == 0.0
    assert isinstance(status.streak, int)
