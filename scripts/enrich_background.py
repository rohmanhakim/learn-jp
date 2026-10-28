#!/usr/bin/env python3
"""Background Jisho enrichment for all remaining vocabulary rows.

Processes N4 → N3 → N2 → N1 sequentially, filling `reading` and
`part_of_speech` for rows still missing them. Designed to run unattended
in a separate terminal with live progress output.

Resumable: kill it at any time, re-run it, it picks up exactly where it
left off (only rows still missing data are touched). Commits every 50
rows so nothing is lost on interruption.

Usage:
    python3 scripts/enrich_background.py
    # or, with a log:
    python3 scripts/enrich_background.py 2>&1 | tee /tmp/enrich_all.log
"""

from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force line-buffered stdout so progress shows live when piped to tee/log
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

from lib.jisho_client import JishoClient

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "progress" / "progress.db"
LEVELS = ["n4", "n3", "n2", "n1"]
COMMIT_BATCH = 50


def enrich_level(level: str, db: sqlite3.Connection, jisho: JishoClient) -> int:
    """Enrich all rows missing reading or part_of_speech for one level."""
    where = (
        "WHERE (reading IS NULL OR reading = '' "
        "OR part_of_speech IS NULL OR part_of_speech = '') AND level = ?"
    )
    rows = db.execute(
        f"SELECT item_id, content FROM vocabulary {where}", (level,)
    ).fetchall()
    total = len(rows)
    print(f"== {level.upper()}: {total} rows need enrichment")

    if total == 0:
        return 0

    start = time.monotonic()
    enriched = 0
    skipped = 0

    for idx, row in enumerate(rows, start=1):
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

        if enriched % COMMIT_BATCH == 0:
            db.commit()
            elapsed = time.monotonic() - start
            rate = enriched / elapsed if elapsed > 0 else 0
            remaining = total - enriched
            eta = remaining / rate if rate > 0 else 0
            print(
                f"  [{enriched}/{total}] enriched={enriched} skipped={skipped} "
                f"rate={rate:.1f}/s eta={eta:.0f}s",
                flush=True,
            )

    db.commit()
    jisho.flush()

    elapsed = time.monotonic() - start
    rate = enriched / elapsed if elapsed > 0 else 0
    print(
        f"== {level.upper()} complete: enriched={enriched} skipped={skipped} "
        f"rate={rate:.1f}/s time={elapsed:.0f}s"
    )
    return enriched


def main() -> int:
    jisho = JishoClient()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row

    grand_start = time.monotonic()
    total_enriched = 0

    for level in LEVELS:
        total_enriched += enrich_level(level, db, jisho)

    db.close()

    total_time = time.monotonic() - grand_start
    print(
        f"\nAll levels done: enriched={total_enriched} "
        f"total_time={total_time:.0f}s"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())