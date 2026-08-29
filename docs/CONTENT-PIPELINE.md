# Content Pipeline

## Overview

The content pipeline fetches vocabulary and kanji from external sources, processes them, and adds them to both the agent database and Anki.

## Sources

### 1. JLPT Vocabulary Lists (Tanos.co.uk)

**URL:** https://www.tanos.co.uk/jlpt/jlpt5/vocab/

**Data Structure:**
- N5: ~800 words (beginner)
- N4: ~700 words (elementary)
- N3: ~600 words (intermediate)
- N2: ~1,000 words (upper intermediate)
- N1: ~1,000 words (advanced)

### 2. Jisho API

**URL:** https://jisho.org/api/v1/search/words

**Provides:**
- Readings (hiragana/katakana)
- English meanings
- Parts of speech
- Example sentences
- Audio pronunciation

### 3. Kanken Dojo (Kanji)

**URL:** https://kanken.dojo.jp/

**Data Structure:**
- JLPT N5: ~100 kanji
- JLPT N4: ~150 kanji
- JLPT N3: ~200 kanji
- JLPT N2: ~350 kanji
- JLPT N1: ~600 kanji

---

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    CONTENT PIPELINE                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. FETCH (from sources)                                    │
│     ├─ JLPT lists → raw word list                           │
│     └─ Kanken Dojo → raw kanji list                         │
│                                                             │
│  2. ENRICH (via Jisho API)                                  │
│     ├─ Lookup each word                                     │
│     ├─ Get: reading, meaning, examples                      │
│     └─ Rate limit: 1 request/second                         │
│                                                             │
│  3. PROCESS (validation)                                    │
│     ├─ Validate data completeness                           │
│     ├─ Remove duplicates                                    │
│     └─ Format for storage                                   │
│                                                             │
│  4. STORE (database + Anki)                                 │
│     ├─ Insert into SQLite (agent DB)                        │
│     └─ Add to Anki via AnkiConnect                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Scripts

### 1. Fetch JLPT Vocabulary

**Script:** `scripts/fetch_jlpt_vocab.py`

**Usage:**
```bash
# Fetch N5 vocabulary
python scripts/fetch_jlpt_vocab.py --level n5

# Fetch all levels
python scripts/fetch_jlpt_vocab.py --all

# Save to file
python scripts/fetch_jlpt_vocab.py --level n5 --output data/jlpt/n5_vocab.json
```

**Output Format:**
```json
[
    {
        "content": "食べる",
        "reading": "たべる",
        "meaning": "to eat",
        "part_of_speech": "verb",
        "level": "n5"
    },
    ...
]
```

---

### 2. Fetch Kanji

**Script:** `scripts/fetch_kanji.py`

**Usage:**
```bash
# Fetch N5 kanji
python scripts/fetch_kanji.py --level n5
```

**Output Format:**
```json
[
    {
        "character": "人",
        "on_reading": ["ジン", "ニン"],
        "kun_reading": ["ひと"],
        "meanings": ["person", "people"],
        "stroke_count": 2,
        "level": "n5"
    },
    ...
]
```

---

### 3. Jisho API Client

**Script:** `scripts/fetch_jisho.py`

**Usage:**
```python
from lib.jisho_client import JishoClient

client = JishoClient()

# Lookup a word
result = client.lookup("食べる")
# Returns: {"reading": "たべる", "meaning": "to eat", ...}

# Search words
results = client.search("food")
# Returns: list of matching words
```

**Rate Limiting:**
- 1 request per second
- Client handles retry automatically

---

### 4. Seed Anki

**Script:** `scripts/seed_anki.py`

**Usage:**
```bash
# Seed N5 vocabulary to Anki
python scripts/seed_anki.py --level n5

# Seed specific word list
python scripts/seed_anki.py --file data/custom_vocab.json

# Dry run (don't actually add)
python scripts/seed_anki.py --level n5 --dry-run
```

**What it does:**
1. Loads vocabulary from JLPT list or file
2. Enriches with Jisho API data (if not already enriched)
3. Creates Anki cards via AnkiConnect
4. Logs to agent database

---

## Data Processing

### Validation Rules

```python
def validate_word(word: dict) -> bool:
    """Validate a vocabulary word."""
    required_fields = ["content", "reading", "meaning", "level"]
    
    # Check required fields exist
    for field in required_fields:
        if not word.get(field):
            return False
    
    # Validate level
    valid_levels = ["n5", "n4", "n3", "n2", "n1"]
    if word["level"] not in valid_levels:
        return False
    
    # Validate reading (should be hiragana/katakana)
    if not is_valid_reading(word["reading"]):
        return False
    
    return True
```

### Deduplication

```python
def deduplicate_words(words: list) -> list:
    """Remove duplicate words."""
    seen = set()
    unique_words = []
    
    for word in words:
        key = word["content"]  # Use kanji as unique key
        if key not in seen:
            seen.add(key)
            unique_words.append(word)
    
    return unique_words
```

---

## Storage

### File Storage

```
data/
├── jlpt/
│   ├── n5_vocab.json          # Raw vocabulary
│   ├── n5_vocab_enriched.json # With Jisho data
│   ├── n4_vocab.json
│   └── ...
├── kanji/
│   ├── n5_kanji.json
│   └── ...
└── cache/
    └── jisho_cache.json       # API response cache
```

### Database Storage

Vocabulary is stored in `vocabulary` table with all metadata. See `DATABASE.md` for schema.

### Anki Storage

Cards are created in Anki with:
- Deck: `Japanese::{level}::Vocab`
- Model: `Basic`
- Front: Word (kanji)
- Back: Reading + Meaning + Part of speech

---

## Rate Limits & Caching

### Jisho API
- Limit: 1 request per second
- Cache responses in `data/cache/jisho_cache.json`
- Skip lookup if word already cached

### AnkiConnect
- No rate limit (local API)
- Batch adds when possible

### OpenRouter
- Depends on model and tier
- Free tier has lower limits
- Implement retry with backoff

---

## Incremental Updates

### Adding New Words

```bash
# Add words not yet in database
python scripts/add_vocab.py --words "勉強する,宿題,先生"

# System automatically:
# 1. Checks if word exists in DB
# 2. Looks up via Jisho if new
# 3. Adds to Anki
# 4. Logs to database
```

### Updating Existing Words

```bash
# Re-fetch enriched data for a word
python scripts/update_vocab.py --word "食べる"

# Update all words at a level
python scripts/update_vocab.py --level n5 --refresh
```

---

## Error Handling

### Jisho API Failures
```python
def safe_lookup(word: str) -> dict:
    """Lookup with retry logic."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return jisho_client.lookup(word)
        except RateLimitError:
            time.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            print(f"Error looking up {word}: {e}")
            return None
    return None
```

### AnkiConnect Failures
```python
def safe_add_note(deck: str, front: str, back: str) -> bool:
    """Add note with error handling."""
    try:
        result = anki_connector.add_note(deck, front, back)
        return result.get("error") is None
    except ConnectionError:
        print("Anki not running. Skipping.")
        return False
```

---

## Testing

### Test Jisho Client
```bash
python -m pytest tests/test_jisho_client.py
```

### Test Anki Connector
```bash
# Requires Anki running
python -m pytest tests/test_anki_connector.py
```

### Test Full Pipeline
```bash
# Dry run (no actual API calls or Anki changes)
python scripts/seed_anki.py --level n5 --dry-run
```
