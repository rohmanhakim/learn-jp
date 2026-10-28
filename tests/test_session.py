"""Tests for SessionManager orchestration (learn_jp/session.py)."""
from __future__ import annotations

import pytest

from learn_jp.session import SessionManager
from learn_jp.errors import PreFlightResult
from learn_jp.progress import ItemReview, SessionResult


class StubAnki:
    def __init__(self, reviews=None, cards=None, available=True):
        self._reviews = reviews or {}
        self._cards = cards or []
        self.available = available
        self.calls = []

    def is_available(self):
        return self.available

    def version(self):
        return 1 if self.available else None

    def get_reviews(self, days=1):
        self.calls.append(("get_reviews", days))
        return self._reviews

    def cards_info(self, card_ids):
        self.calls.append(("cards_info", card_ids))
        return self._cards


class StubErrorHandler:
    def __init__(self, result=None):
        self.result = result or PreFlightResult(success=True)
        self.called = False

    def pre_flight_check(self):
        self.called = True
        return self.result


def test_start_session_aborts_when_pre_flight_fails(temp_db_path, tracker):
    del tracker  # unused; we construct our own manager below
    from learn_jp.progress import ProgressTracker

    tracker = ProgressTracker(temp_db_path)
    anki = StubAnki(available=False)
    eh = StubErrorHandler(PreFlightResult(success=False, errors=["Anki down"]))
    mgr = SessionManager(db_path=temp_db_path, anki=anki, error_handler=eh)

    res = mgr.start_session()

    assert res.aborted is True
    assert res.errors == ["Anki down"]
    assert eh.called is True


def test_start_session_returns_status(temp_db_path, tracker):
    anki = StubAnki()
    eh = StubErrorHandler()
    mgr = SessionManager(db_path=temp_db_path, anki=anki, error_handler=eh)

    res = mgr.start_session()

    assert res.aborted is False
    assert res.status.level == "n5"
    assert eh.called is True


def test_end_session_no_reviews(temp_db_path, tracker):
    anki = StubAnki(reviews={})
    eh = StubErrorHandler()
    mgr = SessionManager(db_path=temp_db_path, anki=anki, error_handler=eh)

    res = mgr.end_session()

    assert res.aborted is False
    assert res.no_reviews is True
    assert res.summary is None


def test_end_session_maps_reviews_to_items(temp_db_path, tracker):
    # add_items() does not write anki_note_id, so insert the row directly to
    # build the card -> note -> item mapping that end_session relies on.
    with tracker._connect() as conn:
        conn.execute(
            """INSERT INTO vocabulary
               (item_id, content, reading, meaning, level, anki_note_id)
               VALUES (?, 'test', 'よみ', 'm', 'n5', ?)""",
            ("item1", 42),
        )
        conn.commit()
    anki = StubAnki(
        reviews={"2026-01-01": [{"cid": 100, "type": 2, "ease": 3, "time": 1200}]},
        cards=[{"cid": 100, "note": 42}],
    )
    eh = StubErrorHandler()
    mgr = SessionManager(db_path=temp_db_path, anki=anki, error_handler=eh)

    res = mgr.end_session()

    assert res.aborted is False
    assert res.no_reviews is False
    assert res.unmapped == 0
    assert res.summary.items_studied == 1
    assert res.summary.correct == 1  # ease 3 (good) -> severity 1 -> correct


def test_end_session_unmapped_review(temp_db_path, tracker):
    anki = StubAnki(
        reviews={"2026-01-01": [{"cid": 999, "type": 2, "ease": 3, "time": 100}]},
        cards=[{"cid": 999, "note": 777}],  # note 777 not in vocabulary
    )
    eh = StubErrorHandler()
    mgr = SessionManager(db_path=temp_db_path, anki=anki, error_handler=eh)

    res = mgr.end_session()

    assert res.aborted is False
    assert res.unmapped == 1
    assert res.summary.items_studied == 0


def test_end_session_promotes_on_threshold(temp_db_path, tracker):
    """A session that records reviews promotes the level when the threshold
    is met. Items are pre-mastered with a last_review_date 7 days ago so the
    today's review keeps them mastered (compute_vocab_status uses the prior
    date for its day-span check).
    """
    today = "2026-01-08"
    last_week = "2026-01-01"
    with tracker._connect() as conn:
        for i in range(1, 4):
            conn.execute(
                """INSERT INTO vocabulary
                   (item_id, content, reading, meaning, level, anki_note_id)
                   VALUES (?, ?, ?, ?, 'n5', ?)""",
                (f"item{i}", f"w{i}", "よみ", "m", i),
            )
            conn.execute(
                """INSERT INTO mastery
                   (item_id, item_type, status, streak, last_review_date,
                    total_reviews, correct_reviews)
                   VALUES (?, 'vocabulary', 'mastered', 5, ?, 5, 5)""",
                (f"item{i}", last_week),
            )
        conn.commit()

    # One mapped review drives record_session -> level-progression check.
    anki = StubAnki(
        reviews={"2026-01-08": [{"cid": 100, "type": 2, "ease": 3, "time": 100}]},
        cards=[{"cid": 100, "note": 1}],
    )
    eh = StubErrorHandler()
    mgr = SessionManager(db_path=temp_db_path, anki=anki, error_handler=eh)

    res = mgr.end_session()

    assert res.aborted is False
    assert res.summary is not None
    assert tracker.get_config("current_level") == "n4"
