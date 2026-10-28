"""Progress tracking and mastery kernel for learn-jp.

The kernel is the single writer for all learning progress.  Every session
(anki, reading, grammar, writing, story) submits raw outcomes through
``record_session()``; the kernel alone decides mastery, regression, and
level progression inside one transaction.

No I/O: no printing, no requests, no Anki, no LLM.  Deterministic and
synchronous.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

DEFAULT_DB_PATH = (
    Path(__file__).resolve().parent.parent / "progress" / "progress.db"
)

MASTERY_RULES = {
    "vocabulary": {
        "min_streak": 5,
        "min_days": 7,
        "min_reviews_in_14_days": 3,
        "max_severity_for_correct": 1,
    },
    "grammar": {
        "min_sessions": 3,
        "min_accuracy": 0.80,
        "min_days": 7,
    },
    "reading": {
        "min_sessions": 3,
        "min_score": 0.70,
        "min_days": 7,
    },
}

SEVERITY_MAX_FOR_CORRECT = 1
LEVEL_ORDER = ["n5", "n4", "n3", "n2", "n1"]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ItemReview:
    """A single item outcome from a session.

    severity: 0 = easy, 1 = good, 2 = hard, 3 = again / failed.
    """

    item_id: str
    item_type: str  # "vocabulary" | "kanji" | "grammar"
    severity: int  # 0-3
    response_time_ms: int | None = None
    error_type: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class SessionResult:
    """Raw outcomes from any session type.  The kernel decides mastery."""

    date: str  # ISO "YYYY-MM-DD"
    type: str  # "anki" | "reading" | "grammar" | "writing" | "story"
    reviews: list[ItemReview] = field(default_factory=list)
    items_studied: int = 0
    correct: int = 0
    time_spent_seconds: int = 0
    notes: str | None = None

    # Reading-specific
    story_id: int | None = None
    questions_answered: int = 0
    questions_correct: int = 0

    # Writing-specific
    prompt_type: str | None = None
    prompt: str | None = None
    user_response: str | None = None
    score: float | None = None
    feedback: str | None = None


@dataclass(frozen=True)
class KernelEvent:
    """A change the kernel made during record_session()."""

    type: str  # "mastery_gained" | "regressed" | "level_up" | "at_risk"
    item_id: str | None = None
    item_type: str | None = None
    detail: str = ""


@dataclass(frozen=True)
class SessionSummary:
    session_id: int
    type: str
    items_studied: int
    correct: int
    accuracy: float
    events: list[KernelEvent]


@dataclass(frozen=True)
class Status:
    level: str
    vocab_mastered: int
    vocab_total: int
    vocab_percent: float
    grammar_mastered: int
    grammar_total: int
    grammar_percent: float
    violation_rate: float
    last_session: str | None
    streak: int


# ---------------------------------------------------------------------------
# Pure mastery rules (testable without a DB)
# ---------------------------------------------------------------------------


def compute_vocab_status(
    streak: int,
    total_reviews: int,
    correct_reviews: int,
    last_review_date: str | None,
    today: str,
) -> str:
    """Return ``"new" | "learning" | "review" | "mastered"`` for vocabulary.

    Mirrors PHASE-4 criteria: streak >= 5, time span >= 7 days,
    >= 3 reviews in last 14 days, severity <= 1 per session.
    """
    if total_reviews < MASTERY_RULES["vocabulary"]["min_reviews_in_14_days"]:
        return "learning"
    if streak < MASTERY_RULES["vocabulary"]["min_streak"]:
        return "review"
    if last_review_date:
        days = (
            datetime.strptime(today, "%Y-%m-%d").date()
            - datetime.strptime(last_review_date, "%Y-%m-%d").date()
        ).days
        if days >= MASTERY_RULES["vocabulary"]["min_days"]:
            return "mastered"
    return "review"


def detect_vocab_regression(
    current_status: str,
    severity: int,
    recent_failures: int,
) -> bool:
    """Return True if a mastered item should regress to 'review'."""
    if current_status != "mastered":
        return False
    if severity == 3:
        return True
    if recent_failures >= 2:
        return True
    return False


# ---------------------------------------------------------------------------
# ProgressTracker — the kernel facade
# ---------------------------------------------------------------------------


class ProgressTracker:
    """Single writer for all learning progress.

    All writes go through :meth:`record_session` or :meth:`add_items`.
    No session ever touches SQL directly.
    """

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = str(db_path or DEFAULT_DB_PATH)

    # -- connection --------------------------------------------------------

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 30000")
        try:
            yield conn
        finally:
            conn.close()

    # -- config ------------------------------------------------------------

    def get_config(self, key: str, default: str | None = None) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM user_config WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else default

    def set_config(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO user_config (key, value, updated_at)
                   VALUES (?, ?, datetime('now'))
                   ON CONFLICT(key) DO UPDATE
                   SET value = excluded.value, updated_at = datetime('now')""",
                (key, value),
            )
            conn.commit()

    # -- queries (read-only) ----------------------------------------------

    def get_status(self, level: str | None = None) -> Status:
        """Overall progress status for a level."""
        level = level or self.get_config("current_level", "n5")
        today = datetime.now().strftime("%Y-%m-%d")

        with self._connect() as conn:
            total = conn.execute(
                "SELECT COUNT(*) AS c FROM vocabulary WHERE level = ?",
                (level,),
            ).fetchone()["c"]

            by_status: dict[str, int] = {}
            for row in conn.execute(
                """SELECT m.status, COUNT(*) AS c
                   FROM mastery m
                   JOIN vocabulary v ON m.item_id = v.item_id
                   WHERE v.level = ?
                   GROUP BY m.status""",
                (level,),
            ):
                by_status[row["status"]] = row["c"]

            mastered = by_status.get("mastered", 0)
            in_review = by_status.get("review", 0)
            learning = by_status.get("learning", 0)
            not_started = total - sum(by_status.values())
            vocab_percent = (mastered / total * 100) if total > 0 else 0.0

            g_total = conn.execute(
                "SELECT COUNT(*) AS c FROM grammar_progress WHERE level = ?",
                (level,),
            ).fetchone()["c"]
            g_mastered = conn.execute(
                """SELECT COUNT(*) AS c FROM grammar_progress
                   WHERE level = ? AND status = 'mastered'""",
                (level,),
            ).fetchone()["c"]
            grammar_percent = (g_mastered / g_total * 100) if g_total > 0 else 0.0

            vr = conn.execute(
                """SELECT AVG(violation_rate) AS avg_rate
                   FROM session_violations
                   WHERE date >= date('now', '-7 days')"""
            ).fetchone()["avg_rate"]
            violation_rate = vr if vr is not None else 0.0

            last = conn.execute(
                """SELECT date FROM sessions
                   ORDER BY date DESC, id DESC LIMIT 1"""
            ).fetchone()
            last_session = last["date"] if last else None

            streak = self._compute_streak(conn)

        return Status(
            level=level,
            vocab_mastered=mastered,
            vocab_total=total,
            vocab_percent=round(vocab_percent, 1),
            grammar_mastered=g_mastered,
            grammar_total=g_total,
            grammar_percent=round(grammar_percent, 1),
            violation_rate=round(violation_rate, 1),
            last_session=last_session,
            streak=streak,
        )

    def _compute_streak(self, conn: sqlite3.Connection) -> int:
        """Consecutive days (ending today) with at least one session."""
        rows = conn.execute(
            """SELECT DISTINCT date FROM sessions ORDER BY date DESC"""
        ).fetchall()
        if not rows:
            return 0
        dates = [
            datetime.strptime(r["date"], "%Y-%m-%d").date() for r in rows
        ]
        today = datetime.now().date()
        streak = 0
        expected = today
        for d in dates:
            if d == expected:
                streak += 1
                expected -= timedelta(days=1)
            elif d < expected:
                break
        return streak

    def get_known_vocabulary(
        self, level: str | None = None, limit: int | None = None
    ) -> list[str]:
        """Words the user knows (mastered or in review), oldest review first."""
        level = level or self.get_config("current_level", "n5")
        with self._connect() as conn:
            query = """
                SELECT v.content
                FROM vocabulary v
                JOIN mastery m ON v.item_id = m.item_id
                WHERE m.status IN ('review', 'mastered') AND v.level = ?
            """
            params: list = [level]
            if limit:
                query += " ORDER BY m.last_review_date IS NULL, m.last_review_date ASC LIMIT ?"
                params.append(limit)
            else:
                query += " ORDER BY m.last_review_date IS NULL, m.last_review_date ASC"
            return [r["content"] for r in conn.execute(query, params)]

    def get_due_items(self, limit: int = 20) -> list[dict]:
        """Items needing review (not mastered), oldest review first."""
        level = self.get_config("current_level", "n5")
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT v.item_id, v.content, v.reading, v.meaning, v.level,
                          m.status, m.streak, m.last_review_date
                   FROM vocabulary v
                   LEFT JOIN mastery m ON v.item_id = m.item_id
                   WHERE v.level = ?
                     AND (m.status IS NULL OR m.status != 'mastered')
                   ORDER BY m.last_review_date IS NULL, m.last_review_date ASC
                   LIMIT ?""",
                (level, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_at_risk_items(self) -> list[dict]:
        """Mastered items not reviewed in 7+ days."""
        level = self.get_config("current_level", "n5")
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT v.item_id, v.content, v.reading, v.meaning, v.level,
                          m.status, m.streak, m.last_review_date
                   FROM vocabulary v
                   JOIN mastery m ON v.item_id = m.item_id
                   WHERE v.level = ?
                     AND m.status = 'mastered'
                     AND m.last_review_date < date('now', '-7 days')
                   ORDER BY m.last_review_date ASC""",
                (level,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_weak_areas(self, limit: int = 10) -> list[dict]:
        """Items with >30% failure rate."""
        level = self.get_config("current_level", "n5")
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT v.item_id, v.content, v.reading, v.meaning, v.level,
                          COUNT(ir.id) AS reviews,
                          SUM(CASE WHEN ir.severity >= 2 THEN 1 ELSE 0 END)
                          AS failures
                   FROM vocabulary v
                   JOIN item_reviews ir ON v.item_id = ir.item_id
                   WHERE v.level = ?
                   GROUP BY v.item_id
                   HAVING failures * 1.0 / reviews > 0.3
                   ORDER BY failures DESC
                   LIMIT ?""",
                (level, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_mastery_status(self, item_id: str) -> dict:
        """Mastery record for a single item."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM mastery WHERE item_id = ?", (item_id,)
            ).fetchone()
            if row:
                return dict(row)
            return {"item_id": item_id, "status": "new", "streak": 0}

    def get_last_session_time(
        self, session_type: str | None = None
    ) -> str | None:
        """ISO date of the most recent session (optionally by type)."""
        with self._connect() as conn:
            if session_type:
                row = conn.execute(
                    """SELECT date FROM sessions
                       WHERE type = ?
                       ORDER BY date DESC, id DESC LIMIT 1""",
                    (session_type,),
                ).fetchone()
            else:
                row = conn.execute(
                    """SELECT date FROM sessions
                       ORDER BY date DESC, id DESC LIMIT 1"""
                ).fetchone()
            return row["date"] if row else None

    # -- commands (write) --------------------------------------------------

    def record_session(self, result: SessionResult) -> SessionSummary:
        """Record a full session in one transaction.

        Inserts the session row and all item_reviews, updates mastery,
        checks regression and level progression.  Returns a summary with
        every kernel event.
        """
        events: list[KernelEvent] = []
        accuracy = (
            result.correct / result.items_studied * 100
            if result.items_studied > 0
            else 0.0
        )

        with self._connect() as conn:
            # 1. Insert session row
            cur = conn.execute(
                """INSERT INTO sessions
                   (date, type, items_studied, correct, accuracy,
                    time_spent_seconds, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    result.date,
                    result.type,
                    result.items_studied,
                    result.correct,
                    round(accuracy, 2),
                    result.time_spent_seconds,
                    result.notes,
                ),
            )
            session_id = cur.lastrowid

            # 2. Insert item reviews + update mastery per review
            for review in result.reviews:
                conn.execute(
                    """INSERT INTO item_reviews
                       (session_id, item_id, item_type, severity,
                        response_time_ms, error_type, notes)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        session_id,
                        review.item_id,
                        review.item_type,
                        review.severity,
                        review.response_time_ms,
                        review.error_type,
                        review.notes,
                    ),
                )
                self._update_mastery_for_review(conn, review, events)

            # 3. Type-specific logging
            if result.type == "reading" and result.story_id is not None:
                score = (
                    result.questions_correct / result.questions_answered
                    if result.questions_answered > 0
                    else 0.0
                )
                conn.execute(
                    """INSERT INTO reading_sessions
                       (story_id, date, time_spent_seconds,
                        comprehension_score, questions_answered,
                        questions_correct, notes)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        result.story_id,
                        result.date,
                        result.time_spent_seconds,
                        round(score, 3),
                        result.questions_answered,
                        result.questions_correct,
                        result.notes,
                    ),
                )

            if result.type == "writing":
                conn.execute(
                    """INSERT INTO writing_sessions
                       (date, prompt_type, prompt, user_response,
                        vocabulary_used, grammar_patterns, score,
                        feedback, time_spent)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        result.date,
                        result.prompt_type,
                        result.prompt,
                        result.user_response,
                        None,
                        None,
                        result.score,
                        result.feedback,
                        result.time_spent_seconds,
                    ),
                )

            # 4. Session violations (violation-based learning)
            if result.reviews:
                violation_count = sum(
                    1 for r in result.reviews if r.severity >= 2
                )
                violation_rate = violation_count / len(result.reviews)
                conn.execute(
                    """INSERT INTO session_violations
                       (session_id, violation_count, violation_rate, date)
                       VALUES (?, ?, ?, ?)""",
                    (session_id, violation_count, violation_rate, result.date),
                )

            # 5. Level progression (inside the write transaction)
            self._check_level_progression(conn, events)

            conn.commit()

        return SessionSummary(
            session_id=session_id,
            type=result.type,
            items_studied=result.items_studied,
            correct=result.correct,
            accuracy=round(accuracy, 1),
            events=events,
        )

    def _update_mastery_for_review(
        self,
        conn: sqlite3.Connection,
        review: ItemReview,
        events: list[KernelEvent],
    ) -> None:
        """Update the mastery row for a single review (inside a transaction)."""
        today = datetime.now().strftime("%Y-%m-%d")
        item_type = review.item_type
        is_correct = review.severity <= SEVERITY_MAX_FOR_CORRECT

        current = conn.execute(
            "SELECT * FROM mastery WHERE item_id = ?", (review.item_id,)
        ).fetchone()

        if current:
            new_streak = current["streak"] + 1 if is_correct else 0
            new_total = current["total_reviews"] + 1
            new_correct = current["correct_reviews"] + (1 if is_correct else 0)

            recent_failures = conn.execute(
                """SELECT COUNT(*) AS c FROM item_reviews
                   WHERE item_id = ? AND severity >= 2
                   ORDER BY created_at DESC LIMIT 3""",
                (review.item_id,),
            ).fetchone()["c"]

            new_status = current["status"]
            if detect_vocab_regression(
                current["status"], review.severity, recent_failures
            ):
                new_status = "review"
                events.append(
                    KernelEvent(
                        type="regressed",
                        item_id=review.item_id,
                        item_type=item_type,
                        detail=(
                            f"severity={review.severity}, "
                            f"recent_failures={recent_failures}"
                        ),
                    )
                )
            else:
                candidate = compute_vocab_status(
                    new_streak, new_total, new_correct,
                    current["last_review_date"], today,
                )
                if candidate == "mastered" and current["status"] != "mastered":
                    new_status = "mastered"
                    events.append(
                        KernelEvent(
                            type="mastery_gained",
                            item_id=review.item_id,
                            item_type=item_type,
                            detail=f"streak={new_streak}, total={new_total}",
                        )
                    )
                elif candidate != current["status"]:
                    new_status = candidate

            conn.execute(
                """UPDATE mastery
                   SET streak = ?, total_reviews = ?, correct_reviews = ?,
                       last_review_date = ?, status = ?,
                       updated_at = datetime('now')
                   WHERE item_id = ?""",
                (
                    new_streak,
                    new_total,
                    new_correct,
                    today,
                    new_status,
                    review.item_id,
                ),
            )
        else:
            # Brand-new item
            new_streak = 1 if is_correct else 0
            new_total = 1
            new_correct = 1 if is_correct else 0
            new_status = (
                "mastered"
                if (
                    is_correct
                    and new_streak >= MASTERY_RULES["vocabulary"]["min_streak"]
                )
                else "learning"
            )

            conn.execute(
                """INSERT INTO mastery
                   (item_id, item_type, status, streak, last_review_date,
                    total_reviews, correct_reviews)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    review.item_id,
                    item_type,
                    new_status,
                    new_streak,
                    today,
                    new_total,
                    new_correct,
                ),
            )
            if new_status == "mastered":
                events.append(
                    KernelEvent(
                        type="mastery_gained",
                        item_id=review.item_id,
                        item_type=item_type,
                        detail="first review, immediate mastery",
                    )
                )

    def _check_level_progression(
        self, conn: sqlite3.Connection, events: list[KernelEvent]
    ) -> None:
        """Persist a level promotion when the threshold is met.

        Runs inside ``record_session``'s write transaction so the level
        change is atomic with the session's mastery updates.  Grammar is
        only considered when at least one grammar item exists for the
        level; otherwise a brand-new level can still progress on vocab
        alone.
        """
        threshold = float(self.get_config("level_threshold", "0.8"))
        level = self.get_config("current_level", "n5")
        next_level = self._next_level(level)

        total = conn.execute(
            "SELECT COUNT(*) AS c FROM vocabulary WHERE level = ?", (level,)
        ).fetchone()["c"]
        mastered = conn.execute(
            """SELECT COUNT(*) AS c FROM mastery m
               JOIN vocabulary v ON m.item_id = v.item_id
               WHERE v.level = ? AND m.status = 'mastered'""",
            (level,),
        ).fetchone()["c"]
        vocab_percent = (mastered / total * 100) if total > 0 else 0.0

        g_total = conn.execute(
            "SELECT COUNT(*) AS c FROM grammar_progress WHERE level = ?",
            (level,),
        ).fetchone()["c"]
        g_mastered = conn.execute(
            """SELECT COUNT(*) AS c FROM grammar_progress
               WHERE level = ? AND status = 'mastered'""",
            (level,),
        ).fetchone()["c"]
        grammar_percent = (g_mastered / g_total * 100) if g_total > 0 else 0.0

        vocab_ok = vocab_percent >= threshold * 100
        grammar_ok = g_total == 0 or grammar_percent >= threshold * 100

        if vocab_ok and grammar_ok:
            conn.execute(
                """INSERT INTO user_config (key, value, updated_at)
                   VALUES ('current_level', ?, datetime('now'))
                   ON CONFLICT(key) DO UPDATE
                   SET value = excluded.value, updated_at = datetime('now')""",
                (next_level,),
            )
            events.append(
                KernelEvent(
                    type="level_up",
                    detail=f"promoted {level} → {next_level}",
                )
            )

    def _next_level(self, level: str) -> str:
        try:
            idx = LEVEL_ORDER.index(level)
            return LEVEL_ORDER[min(idx + 1, len(LEVEL_ORDER) - 1)]
        except ValueError:
            return "n5"

    def add_items(self, items: list[dict]) -> list[str]:
        """Bulk-insert vocabulary items (idempotent on item_id).

        Used by the importer and violation enrichment.  Returns the
        item_ids that were actually inserted.
        """
        inserted: list[str] = []
        with self._connect() as conn:
            for item in items:
                item_id = item["item_id"]
                existing = conn.execute(
                    "SELECT item_id FROM vocabulary WHERE item_id = ?",
                    (item_id,),
                ).fetchone()
                if existing:
                    continue
                conn.execute(
                    """INSERT INTO vocabulary
                       (item_id, content, reading, meaning, level,
                        part_of_speech, source)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item_id,
                        item["content"],
                        item.get("reading"),
                        item["meaning"],
                        item["level"],
                        item.get("part_of_speech"),
                        item.get("source", "manual"),
                    ),
                )
                inserted.append(item_id)
            conn.commit()
        return inserted