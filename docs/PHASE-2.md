# Phase 2: Content Pipeline

## Goal

Create the content pipeline to fetch vocabulary from JLPT sources and add to both database and Anki.

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

### Task 2: Create Seed Anki Script

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
from lib.jlpt_fetcher import JLPTFetcher


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
    
    # Enrich and add each word
    jisho = JishoClient()
    added = 0
    
    for i, word in enumerate(words):
        print(f"[{i+1}/{len(words)}] Processing: {word}")
        
        # Lookup details via Jisho
        details = jisho.lookup(word)
        
        if not details:
            print(f"  Skipping (no Jisho data)")
            continue
        
        # Format for Anki
        front = word
        back = f"{details['reading']}<br>{details['meaning']}<br><i>{details['part_of_speech']}</i>"
        tags = [f"vocab_{level}", "learn-jp"]
        
        if dry_run:
            print(f"  Would add: {front} -> {back}")
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

- [ ] Create JLPTFetcher class
- [ ] Create seed_anki.py script
- [ ] Create add_vocab.py script
- [ ] Test JLPT vocabulary fetching
- [ ] Test seeding to Anki (dry run)
- [ ] Test adding custom vocabulary
- [ ] Handle rate limiting
- [ ] Handle errors gracefully
