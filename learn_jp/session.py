"""SessionManager — the orchestration layer for learn-jp.

The SessionManager conducts one study session from start to finish:

    CLI  →  SessionManager  →  ProgressTracker (kernel)  →  SQLite
                                  ↑
                           AnkiConnect (reviews)

It owns all I/O: printing, HTTP to AnkiConnect, and DB transactions.
The kernel (ProgressTracker) decides mastery; SessionManager feeds it
raw outcomes and returns structured results.  All printing is deferred
to the caller (the CLI) so this layer can be unit-tested without a
terminal.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.anki_connector import AnkiConnector  # noqa: E402

from .errors import ErrorHandler, PreFlightResult
from .progress import (
    DEFAULT_DB_PATH,
    ItemReview,
    ProgressTracker,
    SessionResult,
    SessionSummary,
    Status,
)


@dataclass
class StartResult:
    """Outcome of :meth:`start_session`."""

    aborted: bool = False
    errors: list[str] | None = None
    status: Status | None = None


@dataclass
class EndResult:
    """Outcome of :meth:`end_session`."""

    aborted: bool = False
    no_reviews: bool = False
    unmapped: int = 0
    errors: list[str] | None = None
    summary: SessionSummary | None = None


class SessionManager:
    """Conducts one study session, start to finish.

    Parameters
    ----------
    db_path:
        Path to the SQLite progress database.  Defaults to the repo's
        ``progress/progress.db``.
    anki:
        Optional ``AnkiConnector`` (mostly for testing with a stub).
    error_handler:
        Optional ``ErrorHandler`` (mostly for testing).
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        anki: AnkiConnector | None = None,
        error_handler: ErrorHandler | None = None,
    ):
        self.db_path = str(db_path or DEFAULT_DB_PATH)
        self.tracker = ProgressTracker(db_path)
        self.anki = anki or AnkiConnector()
        self.error_handler = error_handler or ErrorHandler(self.anki)

    # ------------------------------------------------------------------ #
    # start
    # ------------------------------------------------------------------ #
    def start_session(self) -> StartResult:
        """Pre-flight checks + show current status.  No DB writes."""
        checks: PreFlightResult = self.error_handler.pre_flight_check()
        if not checks.success:
            return StartResult(aborted=True, errors=list(checks.errors))

        status = self.tracker.get_status()
        return StartResult(aborted=False, status=status)

    # ------------------------------------------------------------------ #
    # end
    # ------------------------------------------------------------------ #
    def end_session(self) -> EndResult:
        """Pull today's reviews from Anki, record via kernel, return summary."""
        checks: PreFlightResult = self.error_handler.pre_flight_check()
        if not checks.success:
            return EndResult(aborted=True, errors=list(checks.errors))

        raw = self.anki.get_reviews(days=1)
        entries = self._flatten_reviews(raw)

        if not entries:
            return EndResult(no_reviews=True)

        note_to_item = self._build_note_item_map()

        # Resolve card ids -> note ids via AnkiConnect cardsInfo so we can
        # map each review back to a vocabulary item_id.
        cid_to_nid: dict[int, int] = {}
        card_ids = [int(e["cid"]) for e in entries if e.get("cid") is not None]
        if card_ids:
            for card in self.anki.cards_info(card_ids):
                cid = card.get("cid")
                nid = card.get("note")
                if cid is not None and nid is not None:
                    cid_to_nid[int(cid)] = int(nid)

        item_reviews: list[ItemReview] = []
        unmapped = 0
        for entry in entries:
            cid = entry.get("cid")
            note_id = cid_to_nid.get(int(cid)) if cid is not None else None
            if note_id is None:
                unmapped += 1
                continue

            item_id = note_to_item.get(str(note_id))
            if item_id is None:
                unmapped += 1
                continue

            severity = self._severity_from_entry(entry)
            item_reviews.append(
                ItemReview(
                    item_id=item_id,
                    item_type="vocabulary",
                    severity=severity,
                    response_time_ms=entry.get("time"),
                )
            )

        notes = (
            f"{unmapped} review(s) could not be mapped to vocabulary items"
            if unmapped
            else None
        )
        result = SessionResult(
            date=datetime.now().strftime("%Y-%m-%d"),
            type="anki",
            reviews=item_reviews,
            items_studied=len(item_reviews),
            correct=sum(1 for r in item_reviews if r.severity <= 1),
            notes=notes,
        )
        summary = self.tracker.record_session(result)
        return EndResult(summary=summary, unmapped=unmapped)

    # ------------------------------------------------------------------ #
    # status
    # ------------------------------------------------------------------ #
    def show_status(self) -> Status:
        """Current progress status (read-only)."""
        return self.tracker.get_status()

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _flatten_reviews(raw: dict) -> list[dict]:
        """Flatten getReviews() output (date -> [entries]) into a list."""
        entries: list[dict] = []
        for _date, day_entries in (raw or {}).items():
            if isinstance(day_entries, list):
                entries.extend(day_entries)
        return entries

    @staticmethod
    def _severity_from_entry(entry: dict) -> int:
        """Map an Anki revlog entry to severity 0-3.

        severity: 0 = easy, 1 = good, 2 = hard, 3 = again / failed.

        Anki revlog ease: 1 = again, 2 = hard, 3 = good, 4 = easy.
        Falls back to the revlog type when ``ease`` is unavailable.

        Anki revlog types: 0 = learn, 1 = relearn, 2 = review, 3 = cram.
        """
        ease = entry.get("ease")
        if ease is not None:
            return {1: 3, 2: 2, 3: 1, 4: 0}.get(int(ease), 1)
        rtype = entry.get("type")
        if rtype in (1, 3):
            return 3  # relearn / cram: previously failed
        if rtype == 0:
            return 2  # learning step: treat as hard
        return 1  # review: assume good

    def _build_note_item_map(self) -> dict[str, str]:
        """anki_note_id -> vocabulary item_id for all cards pushed to Anki."""
        with self.tracker._connect() as conn:
            rows = conn.execute(
                "SELECT item_id, anki_note_id FROM vocabulary "
                "WHERE anki_note_id IS NOT NULL"
            ).fetchall()
        return {str(r["anki_note_id"]): r["item_id"] for r in rows}
