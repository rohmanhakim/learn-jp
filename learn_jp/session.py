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
        """Pull today's reviews from Anki, record via kernel, return summary.

        Flow::

            notes_info(our linked notes)  -> card IDs
            get_reviews_of_cards(card_ids)  -> {card_id: [reviews]}
            filter to last N days
            card -> note -> item_id (via our DB back-links)
            record_session(...) -> mastery + level progression

        The upstream ``getReviews`` AnkiConnect action is unsupported, so we
        use ``notesInfo`` + ``getReviewsOfCards`` (both supported) instead.
        """
        checks: PreFlightResult = self.error_handler.pre_flight_check()
        if not checks.success:
            return EndResult(aborted=True, errors=list(checks.errors))

        note_to_item = self._build_note_item_map()
        if not note_to_item:
            return EndResult(no_reviews=True, unmapped=0)

        note_ids = [int(nid) for nid in note_to_item.keys()]

        # Resolve note IDs -> card IDs via notesInfo; build card->note map.
        card_to_note: dict[int, int] = {}
        card_ids: list[int] = []
        for info in self.anki.notes_info(note_ids):
            nid = info.get("noteId")
            if nid is None:
                continue
            for c in info.get("cards", []):
                cid = int(c)
                card_to_note[cid] = int(nid)
                card_ids.append(cid)

        if not card_ids:
            return EndResult(no_reviews=True, unmapped=0)

        # Pull reviews for our cards (getReviewsOfCards is supported).
        reviews_by_card = self.anki.get_reviews_of_cards(card_ids) or {}

        # Flatten to entries, filtering to the last N days.
        # Note: each review entry's "time" field is seconds-from-midnight,
        # not a unix timestamp.  Use "id" (unix ms) for the day cutoff.
        cutoff_ms = int(
            (datetime.now().timestamp() - (1 * 86400)) * 1000
        )
        entries: list[dict] = []
        for card_id, reviews in reviews_by_card.items():
            for rev in (reviews or []):
                rev_time_ms = rev.get("id", 0)
                if rev_time_ms >= cutoff_ms:
                    entries.append(
                        {
                            "cid": int(card_id),
                            "ease": rev.get("ease"),
                            "type": rev.get("type"),
                            "time": rev.get("time"),
                        }
                    )

        if not entries:
            return EndResult(no_reviews=True)

        item_reviews: list[ItemReview] = []
        unmapped = 0
        for entry in entries:
            cid = entry.get("cid")
            note_id = card_to_note.get(int(cid)) if cid is not None else None
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
