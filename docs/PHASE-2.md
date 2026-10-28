# Phase 2: Content Pipeline

## Goal

Create the content pipeline to fetch vocabulary from JLPT sources and add to both database and Anki.

## Data Sources

| Source | Data | API/Method |
|--------|------|------------|
| Tanos.co.uk | JLPT word lists (N5-N1) | Web scraping |
| Jisho.org | Word readings, meanings, JLPT level, usage notes | REST API |
| KANJIDIC | Kanji readings (on/kun), meanings, grade, stroke count | XML/Text file |

## Card Structure

### Front Field
```
暖かい
```

### Back Field (HTML)
```html
<div class="reading-box">
    <div class="furigana">あたたかい</div>
</div>
<div class="meaning-section">
    <div class="part-of-speech">I-adjective (keiyoushi)</div>
    <div class="definition">warm; mild; (pleasantly) hot</div>
    <div class="notes">ℹ️ 暖かい usu. refers to air temperature</div>
</div>
<div class="other-forms">Other forms: 暖かい【あったかい】、温かい【あたたかい】</div>
<div class="kanji-breakdown">
    <div class="kanji-character">暖</div>
    <div class="kanji-meaning">warmth</div>
    <div class="kanji-readings">On: ダン、ノン | Kun: あたた.か、あたた.かい</div>
    <div class="kanji-meta">JLPT N1 · Grade 6 · 13 strokes</div>
</div>
```

### Tags
```
Common-word JLPT-N5 learn-jp
```

## Tasks

### Task 1: Create JLPT Vocabulary Fetcher

**File:** `lib/jlpt_fetcher.py`

```python
"""Fetch JLPT vocabulary from Tanos.co.uk."""

import requests
import json
import time
from pathlib import Path
from typing import List


class JLPTFetcher:
    """Fetch JLPT vocabulary lists."""
    
    # Tanos.co.uk URLs for JLPT vocabulary
    URLS = {
        "n5": "https://www.tanos.co.uk/jlpt/jlpt5/vocab/",
        "n4": "https://www.tanos.co.uk/jlpt/jlpt4/vocab/",
        "n3": "https://www.tanos.co.uk/jlpt/jlpt3/vocab/",
        "n2": "https://www.tanos.co.uk/jlpt/jlpt2/vocab/",
        "n1": "https://www.tanos.co.uk/jlpt/jlpt1/vocab/",
    }
    
    DATA_DIR = Path(__file__).parent.parent / "data" / "jlpt"
    
    def __init__(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    def fetch_level(self, level: str) -> List[str]:
        """Fetch vocabulary for a specific JLPT level."""
        if level not in self.URLS:
            raise ValueError(f"Invalid level: {level}. Must be n5-n1.")
        
        url = self.URLS[level]
        response = requests.get(url)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch {level} vocabulary")
        
        # Parse HTML (simplified - actual implementation may need BeautifulSoup)
        # This is a placeholder - actual parsing depends on Tanos HTML structure
        words = self._parse_vocabulary_page(response.text)
        
        # Save to file
        output_file = self.DATA_DIR / f"{level}_vocab.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(words, f, ensure_ascii=False, indent=2)
        
        return words
    
    def _parse_vocabulary_page(self, html: str) -> List[str]:
        """Parse vocabulary from HTML page."""
        # TODO: Implement actual HTML parsing
        # This depends on the actual HTML structure of Tanos
        # May need BeautifulSoup for robust parsing
        return []
    
    def fetch_all(self) -> dict:
        """Fetch all JLPT levels."""
        results = {}
        for level in ["n5", "n4", "n3", "n2", "n1"]:
            try:
                words = self.fetch_level(level)
                results[level] = len(words)
                print(f"Fetched {level}: {len(words)} words")
                time.sleep(2)  # Rate limiting
            except Exception as e:
                print(f"Error fetching {level}: {e}")
                results[level] = 0
        
        return results
    
    def load_cached(self, level: str) -> List[str]:
        """Load cached vocabulary for a level."""
        cache_file = self.DATA_DIR / f"{level}_vocab.json"
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)
        return []
```

---

### Task 2: Create KANJIDIC Client

**File:** `lib/kanjidic_client.py`

```python
"""KANJIDIC client for kanji lookup."""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional


class KANJIDICClient:
    """Client for KANJIDIC kanji dictionary."""
    
    def __init__(self, data_file: str = None):
        if data_file is None:
            # Default to data/kanji/kanjidic.xml
            data_file = Path(__file__).parent.parent / "data" / "kanji" / "kanjidic.xml"
        self.data_file = Path(data_file)
        self.cache = {}
        
    def load(self):
        """Load KANJIDIC data into memory."""
        # Parse XML and build lookup index
        # This is a simplified example - actual implementation
        # depends on KANJIDIC XML format
        pass
    
    def lookup(self, kanji: str) -> Optional[dict]:
        """Look up a kanji character."""
        # Return cached or parse from XML
        if kanji in self.cache:
            return self.cache[kanji]
        
        # Parse and cache
        result = self._parse_kanji(kanji)
        if result:
            self.cache[kanji] = result
        return result
    
    def _parse_kanji(self, kanji: str) -> Optional[dict]:
        """Parse kanji data from XML."""
        # Implementation depends on KANJIDIC XML structure
        # Returns: {
        #   "character": "暖",
        #   "on_readings": ["ダン", "ノン"],
        #   "kun_readings": ["あたた.か", "あたた.かい", ...],
        #   "meanings": ["warmth"],
        #   "jlpt": "N1",
        #   "grade": 6,
        #   "strokes": 13
        # }
        pass
```

### Task 3: Create Seed Anki Script

**File:** `scripts/seed_anki.py`

```python
#!/usr/bin/env python3
"""Seed vocabulary to Anki from JLPT lists."""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.anki_connector import connector
from lib.jisho_client import JishoClient
from lib.kanjidic_client import KANJIDICClient
from lib.jlpt_fetcher import JLPTFetcher


def format_back_field(jisho_data: dict, kanji_data: list) -> str:
    """Format the back field HTML with enriched data."""
    # Reading and meanings from Jisho
    html = f"""
<div class="reading-box">
    <div class="furigana">{jisho_data['reading']}</div>
</div>
<div class="meaning-section">
    <div class="part-of-speech">{jisho_data['part_of_speech']}</div>
    <div class="definition">{jisho_data['meaning']}</div>
</div>"""
    
    # Add usage notes if present
    if jisho_data.get('notes'):
        html += f"""
<div class="notes">ℹ️ {jisho_data['notes']}</div>"""
    
    # Add kanji breakdown
    if kanji_data:
        html += """
<div class="kanji-breakdown">"""
        for kanji in kanji_data:
            readings = f"On: {', '.join(kanji['on_readings'])}"
            if kanji['kun_readings']:
                readings += f" | Kun: {', '.join(kanji['kun_readings'])}"
            html += f"""
    <div class="kanji-item">
        <div class="kanji-character">{kanji['character']}</div>
        <div class="kanji-meaning">{', '.join(kanji['meanings'])}</div>
        <div class="kanji-readings">{readings}</div>
        <div class="kanji-meta">JLPT {kanji['jlpt']} · Grade {kanji['grade']} · {kanji['strokes']} strokes</div>
    </div>"""
        html += """
</div>"""
    
    return html


def seed_level(level: str, dry_run: bool = False):
    """Seed vocabulary for a specific level."""
    print(f"Seeding {level} vocabulary...")
    
    # Load vocabulary
    fetcher = JLPTFetcher()
    words = fetcher.load_cached(level)
    
    if not words:
        print(f"No cached vocabulary for {level}. Fetching...")
        words = fetcher.fetch_level(level)
    
    print(f"Found {len(words)} words")
    
    # Setup Anki deck
    deck_name = f"Japanese::{level.upper()}::Vocab"
    
    if not dry_run:
        connector.create_deck(deck_name)
        print(f"Created deck: {deck_name}")
    
    # Initialize clients
    jisho = JishoClient()
    kanjidic = KANJIDICClient()
    added = 0
    
    for i, word in enumerate(words):
        print(f"[{i+1}/{len(words)}] Processing: {word}")
        
        # Lookup details via Jisho
        jisho_data = jisho.lookup(word)
        
        if not jisho_data:
            print(f"  Skipping (no Jisho data)")
            continue
        
        # Lookup kanji breakdown via KANJIDIC
        kanji_list = []
        for char in word:
            # Only lookup actual kanji (not hiragana/katakana)
            if '\u4e00' <= char <= '\u9fff':  # CJK Unified Ideographs
                kanji_info = kanjidic.lookup(char)
                if kanji_info:
                    kanji_list.append(kanji_info)
        
        # Format for Anki
        front = word
        back = format_back_field(jisho_data, kanji_list)
        tags = [f"vocab_{level}", "learn-jp"]
        
        if dry_run:
            print(f"  Would add: {front} -> {back[:100]}...")
        else:
            result = connector.add_note(deck_name, front, back, tags=tags)
            if result.get("error"):
                print(f"  Error: {result['error']}")
            else:
                added += 1
        
        # Log to database (TODO: implement in Phase 4)
        # log_to_database(word, details, level)
    
    print(f"\nDone! Added {added}/{len(words)} words to {deck_name}")
    return added


def main():
    parser = argparse.ArgumentParser(description="Seed vocabulary to Anki")
    parser.add_argument("--level", choices=["n5", "n4", "n3", "n2", "n1"],
                        help="JLPT level to seed")
    parser.add_argument("--all", action="store_true",
                        help="Seed all levels")
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't actually add to Anki")
    
    args = parser.parse_args()
    
    if not args.level and not args.all:
        parser.error("Must specify --level or --all")
    
    if args.all:
        for level in ["n5", "n4", "n3", "n2", "n1"]:
            seed_level(level, args.dry_run)
    else:
        seed_level(args.level, args.dry_run)


if __name__ == "__main__":
    main()
```

---

### Task 3: Create Add Custom Vocabulary Script

**File:** `scripts/add_vocab.py`

```python
#!/usr/bin/env python3
"""Add custom vocabulary to Anki and database."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.anki_connector import connector
from lib.jisho_client import JishoClient


def add_words(words: list, level: str = "custom", dry_run: bool = False):
    """Add words to Anki and database."""
    jisho = JishoClient()
    deck_name = f"Japanese::{level.upper()}::Vocab"
    
    if not dry_run:
        connector.create_deck(deck_name)
    
    added = 0
    for word in words:
        print(f"Processing: {word}")
        
        details = jisho.lookup(word)
        if not details:
            print(f"  Skipping (no data)")
            continue
        
        front = word
        back = f"{details['reading']}<br>{details['meaning']}"
        tags = [f"vocab_{level}", "custom", "learn-jp"]
        
        if dry_run:
            print(f"  Would add: {front} -> {back}")
        else:
            result = connector.add_note(deck_name, front, back, tags=tags)
            if not result.get("error"):
                added += 1
        
        # TODO: Log to database
    
    print(f"\nAdded {added}/{len(words)} words")


def main():
    parser = argparse.ArgumentParser(description="Add custom vocabulary")
    parser.add_argument("--words", help="Comma-separated words")
    parser.add_argument("--file", help="File with one word per line")
    parser.add_argument("--level", default="custom", help="JLPT level")
    parser.add_argument("--dry-run", action="store_true")
    
    args = parser.parse_args()
    
    if args.words:
        words = [w.strip() for w in args.words.split(",")]
    elif args.file:
        with open(args.file, 'r') as f:
            words = [line.strip() for line in f if line.strip()]
    else:
        parser.error("Must specify --words or --file")
    
    add_words(words, args.level, args.dry_run)


if __name__ == "__main__":
    main()
```

---

## Testing

### Test JLPT Fetcher
```bash
python -c "from lib.jlpt_fetcher import JLPTFetcher; f = JLPTFetcher(); print(f.fetch_level('n5'))"
```

### Test Seed Script (Dry Run)
```bash
python scripts/seed_anki.py --level n5 --dry-run
```

### Test Add Custom Vocab
```bash
python scripts/add_vocab.py --words "勉強する,宿題,先生" --dry-run
```

---

## Checklist

### Content Pipeline
- [x] Create JLPTFetcher class
- [x] Test JLPT vocabulary fetching
- [x] Download KANJIDIC data file (`scripts/fetch_kanjidic.py`, `data/kanji/kanjidic2.xml.gz`)
- [x] Create KANJIDICClient class (`lib/kanjidic_client.py`)
- [ ] Update JishoClient to return richer data (multiple meanings, notes)
- ~[ ]~ Create seed_anki.py script with kanji enrichment — superseded: kanji seeding lives in `scripts/seed_kanji.py` (kanji table) and card enrichment in `scripts/push_anki.py` (kanji breakdown on pushed notes)
- [ ] Create add_vocab.py script
- [x] Test KANJIDIC kanji lookup (verified 暖, 山, unknown-kanji → None)
- [ ] Test seeding to Anki (dry run verified; live push awaits AnkiConnect)
- [ ] Test adding custom vocabulary
- [ ] Handle rate limiting (JishoClient 1 req/s sleep; KANJIDIC is offline XML)
- [ ] Handle errors gracefully (push_anki batch fallback + missing-KANJIDIC degradation)

### CLI Entry Point (NEW)
- [x] Create `learn_jp/cli.py` - main CLI module
- [x] Implement `learn-jp start` - pre-flight checks, show deck info
- [x] Implement `learn-jp end` - pull reviews, calculate mastery, show summary
- [x] Implement `learn-jp status` - show progress, mastery, next steps
- [ ] Implement `learn-jp story` - generate story + comprehension test (Phase 6)
- [x] Implement `learn-jp config` - view/set configuration
- [x] Add pyproject.toml entry point for CLI
- [ ] Test CLI commands end-to-end (unit tests pass; live AnkiConnect E2E pending)

### Data-layer implementation notes (A1–A6, complete)

**Vocab seeding (A1):** `scripts/seed_db.py --level all --no-jisho` seeded N4–N1 (7,672 rows). Full vocabulary: 8,334 rows across N1–N5. Enrichment backfill is chunked via `--enrich-missing --limit N` (A2) — no sleep-polling; completion is a `SELECT COUNT(*) FROM vocabulary WHERE reading IS NULL` query.

**KANJIDIC (A3–A4):** `scripts/fetch_kanjidic.py` downloads `data/kanji/kanjidic2.xml.gz` (gitignored). `lib/kanjidic_client.py` parses it into an in-memory index; `lookup(kanji)` returns on/kun readings, meanings, JLPT, grade, strokes. Verified: `暖` → ダン/ノン, あたた.か/あたた.かい, warmth, jlpt 2, grade 6, 13 strokes.

**Kanji table (A5):** `scripts/seed_kanji.py` upserts 2,091 vocab-derived kanji into the `kanji` table (per-level: n5 418, n4 310, n3 578, n2 326, n1 459). Idempotent via `ON CONFLICT`.

**Anki cards (A6):** `scripts/push_anki.py` gained `--no-kanji`; with kanji data present, new notes get the documented back-field HTML (reading box, meaning section, kanji breakdown block with JLPT/grade/strokes). Missing KANJIDIC data degrades gracefully to plain cards. The 662 already-pushed N5 notes keep their original format.

---


## CLI Design

### Commands

```bash
# Start study session (pre-flight checks)
$ learn-jp start
  Checking Anki... ✓
  Current level: N5
  Deck: Japanese::N5::Vocab (800 cards)
  Ready! Open Anki and review.

# End study session (auto-pull reviews)
$ learn-jp end
  Session Summary
  ───────────────
  Reviews: 25
  Correct: 20 (80%)
  Weak words: 痛い, 働く, 掛ける
  
  Mastery Update
  ───────────────
  N5 Vocab: 180/200 mastered (90%)
  Ready for N4 in ~2 weeks

# Show progress
$ learn-jp status
  Current Level: N5
  Vocabulary: 180/200 mastered (90%)
  Grammar: 45/80 patterns (56%)
  Violation rate: 8%
  Last session: 2 hours ago
  Streak: 12 days

# Generate story + comprehension test
$ learn-jp story
  Generating story...
  Story: [displayed]
  
  Questions:
  1. Where did Taro go?
     A) Store  B) School  C) Home
  > A
  ✓ Correct!
  
  Score: 4/5 (80%)

# Grammar drill
$ learn-jp grammar
  Pattern: ～ます
  Q: What is the polite form of 食べる?
  > 食べます
  ✓ Correct!

# Writing practice
$ learn-jp write
  Prompt: Write what you ate yesterday using ～ました
  > 私は昨日、寿司を食べました。
  ✓ Great! Natural sentence.
```

### Implementation

**File:** `learn_jp/cli.py`

```python
import argparse
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        prog="learn-jp",
        description="Japanese learning system"
    )
    subparsers = parser.add_subparsers(dest="command")
    
    # learn-jp start
    subparsers.add_parser("start", help="Start study session")
    
    # learn-jp end
    subparsers.add_parser("end", help="End study session")
    
    # learn-jp status
    subparsers.add_parser("status", help="Show progress")
    
    # learn-jp story
    story_parser = subparsers.add_parser("story", help="Generate story")
    story_parser.add_argument("--theme", help="Story theme")
    story_parser.add_argument("--questions", type=int, default=5, help="Max questions")
    
    # learn-jp grammar
    grammar_parser = subparsers.add_parser("grammar", help="Grammar drill")
    grammar_parser.add_argument("--pattern", help="Specific pattern")
    
    # learn-jp write
    write_parser = subparsers.add_parser("write", help="Writing practice")
    write_parser.add_argument("--type", choices=["construction", "translation", "prompt"])
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Dispatch to command handler
    from learn_jp.session import SessionManager
    manager = SessionManager()
    
    if args.command == "start":
        return manager.start_session()
    elif args.command == "end":
        return manager.end_session()
    elif args.command == "status":
        return manager.show_status()
    elif args.command == "story":
        return manager.run_story(args.theme, args.questions)
    elif args.command == "grammar":
        return manager.run_grammar(args.pattern)
    elif args.command == "write":
        return manager.run_writing(args.type)

if __name__ == "__main__":
    sys.exit(main())
```

**pyproject.toml entry:**

```toml
[project.scripts]
learn-jp = "learn_jp.cli:main"
```
