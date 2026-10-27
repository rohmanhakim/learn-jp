#!/usr/bin/env python3
"""Push vocabulary from the progress DB to Anki via AnkiConnect.

Creates notes in Japanese::{LEVEL}::Vocab decks and back-links
anki_note_id onto the vocabulary row. Idempotent — skips rows that
already have anki_note_id.

Uses allowDuplicate=true so every vocabulary item gets its own note in
the learn-jp deck, even if the same word exists in another deck (e.g.
the legacy "My Japanese Vocabulary"). That deck is never touched.
"""

import argparse
import json
import sqlite3
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "progress" / "progress.db"

ANKI_URL = "http://localhost:8765"


def anki(action, **params):
    payload = json.dumps(
        {"action": action, "version": 6, "params": params}
    ).encode()
    req = urllib.request.Request(
        ANKI_URL, data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def deck_exists(deck_name: str) -> bool:
    response = anki("deckNames")
    return deck_name in (response.get("result") or [])


def make_note(deck_name: str, front: str, back: str, level: str) -> dict:
    """Build an AnkiConnect note object (properly wrapped)."""
    return {
        "deckName": deck_name,
        "modelName": "Basic",
        "fields": {"Front": front, "Back": back},
        "tags": [f"JLPT-{level.upper()}", "learn-jp"],
        "allowDuplicate": True,
    }


def push_level(level: str, db: sqlite3.Connection,
               dry_run: bool = False) -> int:
    deck_name = f"Japanese::{level.upper()}::Vocab"

    rows = db.execute(
        """
        SELECT item_id, content, reading, meaning, part_of_speech
        FROM vocabulary
        WHERE source = 'jlpt' AND level = ? AND anki_note_id IS NULL
        ORDER BY content
        """,
        (level,),
    ).fetchall()

    print(f"== {level.upper()}: {len(rows)} rows without anki_note_id")

    if dry_run:
        print(f"    [dry run] would push={len(rows)} notes")
        return len(rows)

    pushed = 0
    skipped = 0

    # Create deck if needed
    if not deck_exists(deck_name):
        anki("createDeck", deck=deck_name)

    # Batch add in chunks; fall back to individual addNote on batch failure
    BATCH = 100
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        notes = []
        for row in chunk:
            reading = row["reading"] or ""
            meaning = row["meaning"] or ""
            pos = row["part_of_speech"] or ""

            back_parts = []
            if reading:
                back_parts.append(f"[{reading}]")
            if pos:
                back_parts.append(f"<i>{pos}</i>")
            back_parts.append(meaning)
            back = "<br>".join(back_parts)

            notes.append(make_note(deck_name, row["content"], back, level))

        response = anki("addNotes", notes=notes)
        if not response.get("error"):
            note_ids = response.get("result") or []
            for row, note_id in zip(chunk, note_ids):
                db.execute(
                    "UPDATE vocabulary SET anki_note_id = ?, "
                    "updated_at = datetime('now') WHERE item_id = ?",
                    (note_id, row["item_id"]),
                )
            db.commit()
            pushed += len(note_ids)
            print(f"  [batch] {i//BATCH + 1}: added {len(note_ids)} notes")
            continue

        # Batch failed — fall back to one-by-one
        for row in chunk:
            reading = row["reading"] or ""
            meaning = row["meaning"] or ""
            pos = row["part_of_speech"] or ""

            back_parts = []
            if reading:
                back_parts.append(f"[{reading}]")
            if pos:
                back_parts.append(f"<i>{pos}</i>")
            back_parts.append(meaning)
            back = "<br>".join(back_parts)

            note = make_note(deck_name, row["content"], back, level)
            result = anki("addNote", note=note)
            if result.get("error"):
                skipped += 1
                print(f"  [fail] {row['content']}: {result.get('error')}")
                continue
            note_id = result.get("result")
            db.execute(
                "UPDATE vocabulary SET anki_note_id = ?, "
                "updated_at = datetime('now') WHERE item_id = ?",
                (note_id, row["item_id"]),
            )
            db.commit()
            pushed += 1

    print(f"    pushed={pushed} skipped={skipped}")
    return pushed


def main():
    parser = argparse.ArgumentParser(
        description="Push vocabulary from progress DB to Anki"
    )
    parser.add_argument(
        "--level", choices=["n5", "n4", "n3", "n2", "n1", "all"], default="n5",
        help="JLPT level to push (default: n5)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be done without writing",
    )
    args = parser.parse_args()

    levels = ["n5", "n4", "n3", "n2", "n1"] if args.level == "all" else [args.level]

    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row

    total = 0
    for level in levels:
        total += push_level(level, db, dry_run=args.dry_run)

    db.close()
    print(f"\nTotal notes pushed: {total}")


if __name__ == "__main__":
    main()