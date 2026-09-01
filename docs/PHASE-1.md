# Phase 1: Foundation

## Goal

Set up the basic infrastructure for the learn-jp system.

## Tasks

### Task 1: Create Repository Structure

```bash
mkdir -p learn-jp
cd learn-jp

# Create directory structure
mkdir -p progress/queries
mkdir -p scripts
mkdir -p lib
mkdir -p data/jlpt
mkdir -p data/kanji
mkdir -p docs
```

---

### Task 2: Create Database Schema

**File:** `progress/schema.sql`

```sql
-- learn-jp database schema

-- Vocabulary table
CREATE TABLE IF NOT EXISTS vocabulary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT UNIQUE NOT NULL,
    content TEXT NOT NULL,
    reading TEXT,
    meaning TEXT,
    level TEXT NOT NULL,
    part_of_speech TEXT,
    source TEXT,
    anki_note_id INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_vocab_level ON vocabulary(level);
CREATE INDEX IF NOT EXISTS idx_vocab_item_id ON vocabulary(item_id);

-- Kanji table
CREATE TABLE IF NOT EXISTS kanji (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT UNIQUE NOT NULL,
    character TEXT NOT NULL,
    on_reading TEXT,
    kun_reading TEXT,
    meanings TEXT,
    level TEXT NOT NULL,
    stroke_count INTEGER,
    anki_note_id INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Grammar table
CREATE TABLE IF NOT EXISTS grammar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT UNIQUE NOT NULL,
    pattern TEXT NOT NULL,
    structure TEXT,
    meaning TEXT NOT NULL,
    level TEXT NOT NULL,
    examples TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    type TEXT NOT NULL,
    items_studied INTEGER,
    correct INTEGER,
    accuracy REAL,
    time_spent_seconds INTEGER,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(date);
CREATE INDEX IF NOT EXISTS idx_sessions_type ON sessions(type);

-- Item reviews table
CREATE TABLE IF NOT EXISTS item_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    item_type TEXT NOT NULL,
    severity INTEGER NOT NULL,
    response_time_ms INTEGER,
    error_type TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_item_reviews_item ON item_reviews(item_id);
CREATE INDEX IF NOT EXISTS idx_item_reviews_session ON item_reviews(session_id);

-- Mastery table
CREATE TABLE IF NOT EXISTS mastery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT UNIQUE NOT NULL,
    item_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    streak INTEGER DEFAULT 0,
    last_review_date TEXT,
    next_review_date TEXT,
    total_reviews INTEGER DEFAULT 0,
    correct_reviews INTEGER DEFAULT 0,
    mastery_date TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Stories table
CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    theme TEXT,
    content TEXT NOT NULL,
    vocab_used TEXT,
    vocab_count INTEGER,
    difficulty TEXT,
    length INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Reading sessions table
CREATE TABLE IF NOT EXISTS reading_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER,
    date TEXT NOT NULL,
    time_spent_seconds INTEGER,
    comprehension_score REAL,
    questions_answered INTEGER,
    questions_correct INTEGER,
    new_words_learned TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (story_id) REFERENCES stories(id)
);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT DEFAULT (datetime('now'))
);
```

---

### Task 3: Create Database Initialization Script

**File:** `scripts/init_db.py`

```python
#!/usr/bin/env python3
"""Initialize the learn-jp database."""

import sqlite3
from pathlib import Path

SCHEMA_FILE = Path(__file__).parent.parent / "progress" / "schema.sql"
DB_FILE = Path(__file__).parent.parent / "progress" / "progress.db"


def init_db():
    """Initialize database with schema."""
    # Ensure progress directory exists
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Read schema
    with open(SCHEMA_FILE, 'r') as f:
        schema = f.read()
    
    # Create database
    conn = sqlite3.connect(str(DB_FILE))
    conn.executescript(schema)
    
    # Log schema version
    conn.execute(
        "INSERT OR IGNORE INTO schema_version (version) VALUES (1)"
    )
    conn.commit()
    conn.close()
    
    print(f"Database initialized at {DB_FILE}")


if __name__ == "__main__":
    init_db()
```

---

### Task 4: Create AnkiConnect Wrapper

**File:** `lib/anki_connector.py`

```python
"""AnkiConnect API wrapper."""

import requests
from typing import List, Optional


class AnkiConnector:
    """Wrapper for AnkiConnect API."""
    
    def __init__(self, base_url: str = "http://localhost:8765"):
        self.base_url = base_url
    
    def _request(self, action: str, **params) -> dict:
        """Make API request."""
        response = requests.post(
            self.base_url,
            json={"action": action, "version": 6, "params": params}
        )
        return response.json()
    
    def version(self) -> int:
        """Get AnkiConnect version."""
        result = self._request("version")
        return result.get("result")
    
    def create_deck(self, deck_name: str) -> dict:
        """Create a new deck."""
        return self._request("createDeck", deck=deck_name)
    
    def add_note(self, deck_name: str, front: str, back: str, 
                 model: str = "Basic", tags: List[str] = None) -> dict:
        """Add a single note to Anki."""
        note = {
            "deckName": deck_name,
            "modelName": model,
            "fields": {"Front": front, "Back": back}
        }
        if tags:
            note["tags"] = tags
        
        return self._request("addNote", note=note)
    
    def add_notes(self, deck_name: str, notes: List[dict], 
                  model: str = "Basic") -> dict:
        """Add multiple notes to Anki."""
        anki_notes = []
        for note in notes:
            anki_notes.append({
                "deckName": deck_name,
                "modelName": model,
                "fields": {
                    "Front": note["front"],
                    "Back": note["back"]
                },
                "tags": note.get("tags", [])
            })
        
        return self._request("addNotes", notes=anki_notes)
    
    def find_notes(self, query: str) -> List[int]:
        """Find notes matching query."""
        result = self._request("findNotes", query=query)
        return result.get("result", [])
    
    def notes_info(self, note_ids: List[int]) -> List[dict]:
        """Get info about notes."""
        result = self._request("notesInfo", notes=note_ids)
        return result.get("result", [])
    
    def deck_names(self) -> List[str]:
        """Get list of all deck names."""
        result = self._request("deckNames")
        return result.get("result", [])
    
    def deck_stats(self, deck_names: List[str]) -> dict:
        """Get deck statistics."""
        result = self._request("getDeckStats", decks=deck_names)
        return result.get("result", {})
    
    def get_reviews(self, days: int = 30) -> dict:
        """Get review history."""
        result = self._request("getReviews", days=days)
        return result.get("result", {})
    
    def is_available(self) -> bool:
        """Check if Anki is running and AnkiConnect is available."""
        try:
            version = self.version()
            return version is not None
        except requests.exceptions.ConnectionError:
            return False


# Singleton instance
connector = AnkiConnector()
```

---

### Task 5: Create Jisho Client

**File:** `lib/jisho_client.py`

```python
"""Jisho API client for word lookup."""

import requests
import time
import json
from pathlib import Path
from typing import List, Optional


class JishoClient:
    """Client for Jisho API."""
    
    BASE_URL = "https://jisho.org/api/v1/search/words"
    CACHE_FILE = Path(__file__).parent.parent / "data" / "cache" / "jisho_cache.json"
    
    def __init__(self):
        self.cache = self._load_cache()
    
    def _load_cache(self) -> dict:
        """Load API response cache."""
        if self.CACHE_FILE.exists():
            with open(self.CACHE_FILE, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_cache(self):
        """Save cache to file."""
        self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(self.CACHE_FILE, 'w') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    def lookup(self, word: str) -> Optional[dict]:
        """Look up a word on Jisho."""
        # Check cache
        if word in self.cache:
            return self.cache[word]
        
        # Rate limiting
        time.sleep(1)
        
        # API request
        response = requests.get(
            self.BASE_URL,
            params={"keyword": word}
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        results = data.get("data", [])
        
        if not results:
            return None
        
        # Parse first result
        first = results[0]
        japanese = first.get("japanese", [{}])[0]
        english = first.get("english_definitions", [])
        
        result = {
            "word": word,
            "reading": japanese.get("reading", ""),
            "meaning": ", ".join(english[:3]),  # Top 3 meanings
            "part_of_speech": first.get("parts_of_speech", [""])[0]
        }
        
        # Cache result
        self.cache[word] = result
        self._save_cache()
        
        return result
    
    def lookup_batch(self, words: List[str]) -> List[dict]:
        """Look up multiple words."""
        results = []
        for word in words:
            result = self.lookup(word)
            if result:
                results.append(result)
        return results
```

---

### Task 6: Create Utility Scripts

**File:** `scripts/hhmmss_to_seconds.py`

```python
#!/usr/bin/env python3
"""Convert hh:mm:ss format to seconds."""

import sys


def hhmmss_to_seconds(time_str: str) -> int:
    """Convert hh:mm:ss or mm:ss to seconds."""
    parts = time_str.strip().split(":")
    
    if len(parts) == 3:
        hours, minutes, seconds = map(int, parts)
        return hours * 3600 + minutes * 60 + seconds
    elif len(parts) == 2:
        minutes, seconds = map(int, parts)
        return minutes * 60 + seconds
    else:
        return int(parts[0])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python hhmmss_to_seconds.py <time>")
        print("Example: python hhmmss_to_seconds.py 01:30:00")
        sys.exit(1)
    
    time_str = sys.argv[1]
    seconds = hhmmss_to_seconds(time_str)
    print(f"{time_str} = {seconds} seconds")
```

---

### Task 7: Create .gitignore

**File:** `.gitignore`

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.venv/

# Database
progress/progress.db
progress/progress.db-wal
progress/progress.db-shm

# Cache
data/cache/

# API keys
*.api-key
.openrouter-api-key

# Anki
*.anki2
*.anki2-wal
*.anki2-shm

# Generated files
story.txt
*.output

# IDE
.vscode/
.idea/
```

---

## Testing

### Test Database Initialization
```bash
python scripts/init_db.py
ls -la progress/progress.db
```

### Test AnkiConnect
```bash
python -c "from lib.anki_connector import connector; print(connector.is_available())"
```

### Test Jisho Client
```bash
python -c "from lib.jisho_client import JishoClient; c = JishoClient(); print(c.lookup('食べる'))"
```

---

## Checklist

- [x] Create repository structure
- [x] Create database schema
- [x] Create init_db.py script
- [x] Create AnkiConnector class
- [x] Create JishoClient class
- [x] Create utility scripts
- [x] Create .gitignore
- [x] Initialize database
- [x] Test AnkiConnect connection
- [x] Test Jisho lookup
