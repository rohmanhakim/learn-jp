#!/usr/bin/env python3
"""Seed the progress database with JLPT vocabulary from data/jlpt/*.json.

Reads raw JLPT vocabulary files, optionally enriches via Jisho API
(reading, part_of_speech), normalizes text, and upserts into the
vocabulary table. Idempotent — safe to re-run.

The DB is the source of truth; Anki is a projection. This script only
writes to SQLite. Use scripts/push_anki.py to project into Anki.
"""

import argparse
import html
import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.jisho_client import JishoClient  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "jlpt"
DB_PATH = ROOT / "progress" / "progress.db"

LEVELS = ["n5", "n4", "n3", "n2", "n1"]


def normalize(text: str) -> str:
    """Strip whitespace and decode HTML entities."""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_jlpt_words(level: str) -> list[dict]:
    path = DATA_DIR / f"{level}_vocab.json"
    if not path.exists():
        print(f"  [skip] {path} not found", file=sys.stderr)
        return []
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    words = []
    seen = set()
    for entry in raw:
        content = normalize(entry.get("word", ""))
        meaning = normalize(entry.get("meaning", ""))
        if not content or content in seen:
            continue
        seen.add(content)
        words.append({"content": content, "meaning": meaning, "level": level})
    return words


def seed_level(level: str, jisho: JishoClient | None,
               db: sqlite3.Connection, dry_run: bool = False) -> int:
    words = load_jlpt_words(level)
    print(f"  {level.upper()}: {len(words)} unique words from file")

    inserted = 0
    skipped = 0
    enriched = 0

    for w in words:
        item_id = f"jlpt:{level}:{w['content']}"

        existing = db.execute(
            "SELECT item_id FROM vocabulary WHERE item_id = ?", (item_id,)
        ).fetchone()
        if existing:
            skipped += 1
            continue

        reading = None
        pos = None
        meaning = w["meaning"]

        if jisho and not dry_run:
            try:
                result = jisho.lookup(w["content"])
                if result:
                    reading = result.get("reading") or None
                    pos = result.get("part_of_speech") or None
                    jisho_meaning = normalize(result.get("meaning", ""))
                    if jisho_meaning:
                        meaning = jisho_meaning
                    enriched += 1
            except Exception as e:
                print(f"    [warn] Jisho failed for {w['content']}: {e}", file=sys.stderr)

        if not dry_run:
            db.execute(
                """
                INSERT INTO vocabulary
                (item_id, content, reading, meaning, level, part_of_speech, source)
                VALUES (?, ?, ?, ?, ?, ?, 'jlpt')
                """,
                (item_id, w["content"], reading, meaning, level, pos),
            )
        inserted += 1

        # Commit periodically so a crash doesn't lose everything
        if not dry_run and inserted % 50 == 0:
            db.commit()

    if not dry_run:
        db.commit()

    print(f"    inserted={inserted} skipped={skipped} enriched={enriched}")
    return inserted


def enrich_missing(
    level: str | None,
    jisho: JishoClient,
    db: sqlite3.Connection,
    limit: int | None = None,
    dry_run: bool = False,
) -> int:
    """Enrichment-only mode: fill reading/part_of_speech/meaning for existing
    rows via Jisho lookups. Idempotent and resumable — only rows still missing
    data are touched, so a run can be killed and re-run safely.
    """
    where = (
        "WHERE (reading IS NULL OR reading = '' "
        "OR part_of_speech IS NULL OR part_of_speech = '')"
    )
    params: list = []
    if level:
        where += " AND level = ?"
        params.append(level)
    if limit:
        where += " LIMIT ?"
        params.append(limit)

    rows = db.execute(
        f"SELECT item_id, content FROM vocabulary {where}", params
    ).fetchall()
    print(f"  {len(rows)} rows need enrichment" + (f" (limit={limit})" if limit else ""))

    enriched = 0
    skipped = 0
    for row in rows:
        content = row["content"]
        item_id = row["item_id"]
        try:
            result = jisho.lookup(content)
        except Exception as e:
            print(f"    [warn] Jisho failed for {content}: {e}", file=sys.stderr)
            skipped += 1
            continue

        if not result:
            skipped += 1
            continue

        reading = result.get("reading") or None
        pos = result.get("part_of_speech") or None
        meaning = result.get("meaning") or None

        if not dry_run:
            db.execute(
                """
                UPDATE vocabulary
                   SET reading = COALESCE(?, reading),
                       part_of_speech = COALESCE(?, part_of_speech),
                       meaning = COALESCE(?, meaning),
                       updated_at = datetime('now')
                 WHERE item_id = ?
                """,
                (reading, pos, meaning, item_id),
            )

        enriched += 1

        if not dry_run and enriched % 50 == 0:
            db.commit()
            print(f"    committed {enriched} rows so far")

    if not dry_run:
        db.commit()
        jisho.flush()

    print(f"    enriched={enriched} skipped={skipped}")
    return enriched


def main():
    parser = argparse.ArgumentParser(
        description="Seed JLPT vocabulary into progress DB"
    )
    parser.add_argument(
        "--level", choices=LEVELS + ["all"], default="n5",
        help="JLPT level to seed (default: n5)",
    )
    parser.add_argument(
        "--no-jisho", action="store_true",
        help="Skip Jisho enrichment (fast, no reading/POS)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be done without writing",
    )
    parser.add_argument(
        "--enrich-missing", action="store_true",
        help="Enrichment-only mode: fill reading/part_of_speech/meaning for "
             "existing rows via Jisho (no new inserts).",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Max rows to enrich in this run (pairs with --enrich-missing).",
    )
    args = parser.parse_args()

    levels = LEVELS if args.level == "all" else [args.level]

    if args.enrich_missing and args.no_jisho:
        print("--enrich-missing requires Jisho; drop --no-jisho.", file=sys.stderr)
        return 1

    jisho = None if args.no_jisho else JishoClient()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row

    if args.enrich_missing:
        total = 0
        for level in levels:
            print(f"== {level.upper()} enrichment")
            total += enrich_missing(
                level, jisho, db, limit=args.limit, dry_run=args.dry_run,
            )
        if not args.dry_run:
            jisho.flush()
        db.close()
        print(f"\nTotal rows enriched: {total}")
        return 0

    total = 0
    for level in levels:
        print(f"== {level.upper()}")
        total += seed_level(level, jisho, db, dry_run=args.dry_run)

    db.close()
    print(f"\nTotal rows inserted: {total}")


if __name__ == "__main__":
    main()