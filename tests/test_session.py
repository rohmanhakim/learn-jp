"""Tests for SessionManager orchestration (learn_jp/session.py)."""
from __future__ import annotations

import time

import pytest

from learn_jp.session import SessionManager
from learn_jp.errors import PreFlightResult
from learn_jp.progress import ItemReview, SessionResult


class StubAnki:
    def __init__(self, reviews=None, notes=None, available=True):
        # reviews: {card_id: [{"cid":..., "ease":..., "type":..., "time":...}]}
        self._reviews = reviews or {}
        # notes: {note_id: {"noteId":..., "cards": [...]}}
        self._notes = notes or {}
        self.available = available
        self.calls = []

    def is_available(self):
        return self.available

    def version(self):
        return 1 if self.available else None

    def notes_info(self, note_ids):
        self.calls.append(("notes_info", note_ids))
        return [self._notes.get(nid, {}) for nid in note_ids]

    def get_reviews_of_cards(self, card_ids):
        self.calls.append(("get_reviews_of_cards", card_ids))
        return {str(cid): self._reviews.get(int(cid), []) for cid in card_ids}

    def cards_info(self, card_ids):
        self.calls.append(("cards_info", card_ids))
        return []


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
        reviews={100: [{"cid": 100, "type": 2, "ease": 3, "id": int(time.time() * 1000), "time": 1200}]},
        notes={42: {"noteId": 42, "cards": [100]}},
    )
    eh = StubErrorHandler()
    mgr = SessionManager(db_path=temp_db_path, anki=anki, error_handler=eh)

    res = mgr.end_session()

    assert res.aborted is False
    assert res.no_reviews is False
    assert res.unmapped == 0
    assert res.summary.items_studied == 1
    assert res.summary.correct == 1  # ease 3 (good) -> severity 1 -> correct


def test_end_session_deleted_anki_note(temp_db_path, tracker):
    """Linked vocabulary item whose Anki note was deleted (notes_info returns
    no cards) should not crash; we report no reviews."""
    with tracker._connect() as conn:
        conn.execute(
            """INSERT INTO vocabulary
               (item_id, content, reading, meaning, level, anki_note_id)
               VALUES ('item1', 'x', 'よみ', 'm', 'n5', 1)""",
        )
        conn.commit()
    anki = StubAnki(
        reviews={},
        notes={1: {}},  # note 1 deleted from Anki — no cards returned
    )
    eh = StubErrorHandler()
    mgr = SessionManager(db_path=temp_db_path, anki=anki, error_handler=eh)

    res = mgr.end_session()

    assert res.aborted is False
    assert res.no_reviews is True
    assert res.summary is None


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
        reviews={100: [{"cid": 100, "type": 2, "ease": 3, "id": int(time.time() * 1000), "time": 100}]},
        notes={1: {"noteId": 1, "cards": [100]}},
    )
    eh = StubErrorHandler()
    mgr = SessionManager(db_path=temp_db_path, anki=anki, error_handler=eh)

    res = mgr.end_session()

    assert res.aborted is False
    assert res.summary is not None
    assert tracker.get_config("current_level") == "n4"
