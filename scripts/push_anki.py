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
KANJIDIC_DATA = ROOT / "data" / "kanji" / "kanjidic2.xml.gz"

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


def load_kanji_lookup(db: sqlite3.Connection) -> dict[str, dict]:
    """Load seeded kanji rows into a dict keyed by character.

    Returns {character: {"on_readings": [...], "kun_readings": [...],
    "meanings": [...], "level": str, "strokes": int}}.
    """
    lookup: dict[str, dict] = {}
    rows = db.execute(
        "SELECT character, on_reading, kun_reading, meanings, level, "
        "stroke_count FROM kanji"
    ).fetchall()
    for row in rows:
        lookup[row["character"]] = {
            "on_readings": (row["on_reading"] or "").split(",") if row["on_reading"] else [],
            "kun_readings": (row["kun_reading"] or "").split(",") if row["kun_reading"] else [],
            "meanings": (row["meanings"] or "").split(";") if row["meanings"] else [],
            "level": row["level"],
            "strokes": row["stroke_count"],
        }
    return lookup


def kanji_breakdown_html(chars: str, lookup: dict[str, dict]) -> str:
    """Render the kanji-breakdown div for a word's kanji characters."""
    items: list[str] = []
    for ch in chars:
        if not ("\u4e00" <= ch <= "\u9fff"):
            continue
        info = lookup.get(ch)
        if not info:
            continue
        readings = f"On: {', '.join(info['on_readings'])}"
        if info["kun_readings"]:
            readings += f" | Kun: {', '.join(info['kun_readings'])}"
        items.append(
            f"""<div class="kanji-item">
        <div class="kanji-character">{ch}</div>
        <div class="kanji-meaning">{', '.join(info['meanings'])}</div>
        <div class="kanji-readings">{readings}</div>
        <div class="kanji-meta">JLPT {info['level'].upper()} · {info['strokes'] or '?'} strokes</div>
    </div>"""
        )
    if not items:
        return ""
    inner = "\n".join(items)
    return (
        f"""<div class="kanji-breakdown">
{inner}
</div>"""
    )


def make_back(row: sqlite3.Row, lookup: dict[str, dict],
              include_kanji: bool) -> str:
    """Build the Anki card back-field HTML for a vocabulary row.

    Format per docs/PHASE-2.md: reading box, meaning section, optional
    kanji breakdown block.
    """
    reading = row["reading"] or ""
    meaning = row["meaning"] or ""
    pos = row["part_of_speech"] or ""

    parts: list[str] = []
    if reading:
        parts.append(f"""<div class="reading-box">
    <div class="furigana">{reading}</div>
</div>""")
    parts.append("<div class=\"meaning-section\">")
    if pos:
        parts.append(f"<div class=\"part-of-speech\">{pos}</div>")
    parts.append(f"<div class=\"definition\">{meaning}</div>")
    parts.append("</div>")

    if include_kanji:
        breakdown = kanji_breakdown_html(row["content"], lookup)
        if breakdown:
            parts.append(breakdown)

    return "<br>".join(parts)


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
               dry_run: bool = False,
               kanji_lookup: dict[str, dict] | None = None,
               include_kanji: bool = False) -> int:
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
            back = make_back(row, kanji_lookup or {}, include_kanji)
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
            back = make_back(row, kanji_lookup or {}, include_kanji)
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
    parser.add_argument(
        "--no-kanji", action="store_true",
        help="Skip kanji breakdown (push plain cards, no KANJIDIC data needed)",
    )
    args = parser.parse_args()

    levels = ["n5", "n4", "n3", "n2", "n1"] if args.level == "all" else [args.level]
    include_kanji = not args.no_kanji

    # Load kanji lookup once (shared across levels).  Missing KANJIDIC data
    # degrades gracefully to plain cards when --no-kanji is not set.
    kanji_lookup = None
    if include_kanji:
        if not KANJIDIC_DATA.exists():
            print(
                f"[warn] KANJIDIC data not found at {KANJIDIC_DATA}; "
                "pushing without kanji breakdown. "
                "Run scripts/fetch_kanjidic.py to enable it.",
                file=sys.stderr,
            )
            include_kanji = False
        else:
            db_tmp = sqlite3.connect(str(DB_PATH))
            db_tmp.row_factory = sqlite3.Row
            kanji_lookup = load_kanji_lookup(db_tmp)
            db_tmp.close()
            print(f"[kanji] loaded {len(kanji_lookup)} kanji for card breakdown")

    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row

    total = 0
    for level in levels:
        total += push_level(
            level, db, dry_run=args.dry_run,
            kanji_lookup=kanji_lookup, include_kanji=include_kanji,
        )

    db.close()
    print(f"\nTotal notes pushed: {total}")


if __name__ == "__main__":
    main()