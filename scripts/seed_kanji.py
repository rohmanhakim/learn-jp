#!/usr/bin/env python3
"""Seed the progress database's kanji table from seeded vocabulary.

Extracts unique CJK characters from seeded vocabulary rows, looks each up
via KANJIDICClient, and upserts into the kanji table. Kanji stays scoped to
what you are actually learning ("kanji implicit through vocab", per the
architecture). Idempotent — safe to re-run; refreshed lookups overwrite in
place.

Offline once data/kanji/kanjidic2.xml.gz is present (scripts/fetch_kanjidic.py).
"""

import argparse
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.kanjidic_client import KANJIDICClient

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "jlpt"
DB_PATH = ROOT / "progress" / "progress.db"

LEVELS = ["n5", "n4", "n3", "n2", "n1"]
LEVEL_ORDER = {level: idx for idx, level in enumerate(LEVELS)}


def extract_kanji(vocab_items: list[str]) -> list[str]:
    """Return sorted unique CJK characters from vocabulary content."""
    chars = set()
    for content in vocab_items:
        for ch in content:
            if "\u4e00" <= ch <= "\u9fff":
                chars.add(ch)
    return sorted(chars)


def seed_kanji(
    db: sqlite3.Connection,
    kanjidic: KANJIDICClient,
    level: str | None = None,
    dry_run: bool = False,
) -> int:
    """Upsert kanji rows for vocabulary-derived kanji. Returns rows upserted."""
    if level:
        vocabs = db.execute(
            "SELECT content FROM vocabulary WHERE level = ?", (level,)
        ).fetchall()
        # Vocab-derived level: earliest level containing the char across all levels
        char_levels: dict[str, str] = {}
        for lvl in LEVELS:
            rows = db.execute(
                "SELECT content FROM vocabulary WHERE level = ?", (lvl,)
            ).fetchall()
            for (content,) in rows:
                for ch in content:
                    if "\u4e00" <= ch <= "\u9fff" and ch not in char_levels:
                        char_levels[ch] = lvl
        chars = sorted(
            ch
            for ch, lv in char_levels.items()
            if LEVEL_ORDER[lv] == LEVEL_ORDER[level]
        )
    else:
        char_levels: dict[str, str] = {}
        for lvl in LEVELS:
            rows = db.execute(
                "SELECT content FROM vocabulary WHERE level = ?", (lvl,)
            ).fetchall()
            for (content,) in rows:
                for ch in content:
                    if "\u4e00" <= ch <= "\u9fff" and ch not in char_levels:
                        char_levels[ch] = lvl
        chars = sorted(char_levels)

    print(f"  {len(chars)} unique kanji")
    upserted = 0

    for ch in chars:
        info = kanjidic.lookup(ch)
        item_id = f"kanji:{ch}"

        if info:
            on_reading = ",".join(info["on_readings"]) or None
            kun_reading = ",".join(info["kun_readings"]) or None
            meanings = ";".join(info["meanings"]) or None
            strokes = info["strokes"]
            jlpt_level = char_levels.get(ch, level)
        else:
            on_reading = None
            kun_reading = None
            meanings = None
            strokes = None
            jlpt_level = char_levels.get(ch, level)

        if not dry_run:
            db.execute(
                """
                INSERT INTO kanji (item_id, character, on_reading, kun_reading,
                                   meanings, level, stroke_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET
                    character = excluded.character,
                    on_reading = excluded.on_reading,
                    kun_reading = excluded.kun_reading,
                    meanings = excluded.meanings,
                    level = excluded.level,
                    stroke_count = excluded.stroke_count
                """,
                (
                    item_id,
                    ch,
                    on_reading,
                    kun_reading,
                    meanings,
                    jlpt_level,
                    strokes,
                ),
            )

        upserted += 1

    if not dry_run:
        db.commit()

    print(f"    upserted={upserted}")
    return upserted


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed kanji table from seeded vocabulary"
    )
    parser.add_argument(
        "--level", choices=LEVELS, default=None,
        help="Only upsert kanji whose vocab-derived level matches",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be done without writing",
    )
    args = parser.parse_args()

    kanjidic = KANJIDICClient()
    if not kanjidic.loaded:
        print(
            f"KANJIDIC data not found at {kanjidic.data_file}. "
            "Run scripts/fetch_kanjidic.py first.",
            file=sys.stderr,
        )
        return 1

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row

    total = 0
    if args.level:
        print(f"== {args.level.upper()}")
        total += seed_kanji(db, kanjidic, level=args.level, dry_run=args.dry_run)
    else:
        print("== all levels")
        total += seed_kanji(db, kanjidic, level=None, dry_run=args.dry_run)

    db.close()
    print(f"\nTotal kanji upserted: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())