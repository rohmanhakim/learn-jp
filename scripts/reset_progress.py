#!/usr/bin/env python3
"""Reset learn-jp progress state back to initial (pre-session) conditions.

Clears all session/progress tracking rows while preserving seeded content
(vocabulary, kanji, grammar) and schema.  Intended for use between E2E test
runs so each run starts from a clean, deterministic baseline.

Usage:
    python scripts/reset_progress.py              # interactive confirmation
    python scripts/reset_progress.py --yes        # skip confirmation (CI)
    python scripts/reset_progress.py --dry-run --yes   # preview only, no writes
    python scripts/reset_progress.py --unlink-anki   # also NULL anki_note_id so
                                                       # re-seeding to Anki works cleanly
    python scripts/reset_progress.py --include-stories   # also clear generated stories
    python scripts/reset_progress.py --db progress/progress.db   # custom path
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "progress"
DB_FILE = SCHEMA_DIR / "progress.db"

# Child-first deletion order so foreign keys (session_id -> sessions,
# item_id -> vocabulary/grammar) are respected.  vocabulary/kanji/grammar
# themselves are deliberately NOT in this list — they are seeded content.
PROGRESS_TABLES = [
    "item_reviews",
    "session_violations",
    "reading_sessions",
    "writing_sessions",
    "grammar_sessions",
    "grammar_progress",
    "sessions",
    "mastery",
    "user_config",
]

# AUTOINCREMENT counters to reset so newly inserted rows start at id=1.
SEQUENCE_TABLES = [
    "sessions",
    "item_reviews",
    "mastery",
    "session_violations",
    "reading_sessions",
    "writing_sessions",
    "grammar_sessions",
    "stories",
]


def row_counts(conn: sqlite3.Connection, tables: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in tables:
        try:
            counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except sqlite3.OperationalError:
            counts[table] = -1  # table does not exist yet
    return counts


def preview_counts(
    db_path: Path,
    unlink_anki: bool,
    include_stories: bool,
) -> dict[str, int]:
    """Return current row counts without modifying anything."""
    tables = list(PROGRESS_TABLES)
    if include_stories:
        tables.append("stories")

    conn = sqlite3.connect(str(db_path))
    try:
        counts = row_counts(conn, tables)
        if unlink_anki:
            counts["vocabulary.anki_note_id (non-null)"] = conn.execute(
                "SELECT COUNT(*) FROM vocabulary WHERE anki_note_id IS NOT NULL"
            ).fetchone()[0]
            counts["kanji.anki_note_id (non-null)"] = conn.execute(
                "SELECT COUNT(*) FROM kanji WHERE anki_note_id IS NOT NULL"
            ).fetchone()[0]
        return counts
    finally:
        conn.close()


def do_reset(
    db_path: Path,
    unlink_anki: bool,
    include_stories: bool,
) -> dict[str, int]:
    """Delete progress rows and reset AUTOINCREMENT counters. Return deleted counts."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    tables = list(PROGRESS_TABLES)
    seq_tables = list(SEQUENCE_TABLES)
    if include_stories:
        tables.append("stories")
        seq_tables.append("stories")

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON")
        cur.execute("BEGIN")

        before = row_counts(conn, tables)
        if unlink_anki:
            before["vocabulary.anki_note_id"] = conn.execute(
                "SELECT COUNT(*) FROM vocabulary WHERE anki_note_id IS NOT NULL"
            ).fetchone()[0]
            before["kanji.anki_note_id"] = conn.execute(
                "SELECT COUNT(*) FROM kanji WHERE anki_note_id IS NOT NULL"
            ).fetchone()[0]

        for table in tables:
            cur.execute(f"DELETE FROM {table}")

        if unlink_anki:
            cur.execute("UPDATE vocabulary SET anki_note_id = NULL")
            cur.execute("UPDATE kanji SET anki_note_id = NULL")

        # Reset AUTOINCREMENT counters so next inserts start at id=1.
        for table in seq_tables:
            cur.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))

        conn.commit()

        after = row_counts(conn, tables)
        return {t: before.get(t, 0) - after.get(t, 0) for t in tables}
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="reset_progress",
        description="Reset learn-jp progress state to initial (pre-session) conditions.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt (safe for CI/scripts).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show row counts that would be deleted without making changes.",
    )
    parser.add_argument(
        "--unlink-anki",
        action="store_true",
        help="Also NULL out vocabulary.anki_note_id and kanji.anki_note_id, "
        "reverting Anki links so re-seeding to Anki works cleanly.",
    )
    parser.add_argument(
        "--include-stories",
        action="store_true",
        help="Also clear generated stories rows.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DB_FILE,
        help=f"Path to progress database (default: {DB_FILE})",
    )
    args = parser.parse_args(argv)

    if not args.db.exists():
        print(f"Database not found: {args.db}")
        print("Run python scripts/init_db.py first.")
        return 1

    counts = preview_counts(args.db, args.unlink_anki, args.include_stories)

    print("\nProgress rows that would be deleted:")
    for table, n in sorted(counts.items()):
        print(f"  {table:<34} {n}")

    if args.dry_run:
        print("\nDry run complete — no changes made.")
        return 0

    if not args.yes:
        confirm = input("\nProceed with reset? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return 1

    deleted = do_reset(args.db, args.unlink_anki, args.include_stories)

    print("\nReset complete. Rows deleted:")
    for table, n in sorted(deleted.items()):
        print(f"  {table:<34} {n}")
    print("Progress state is back to initial (pre-session) conditions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())