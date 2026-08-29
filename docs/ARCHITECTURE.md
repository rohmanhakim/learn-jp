# Architecture

## System Components

### 1. Anki (Drill Engine)
**Role:** Spaced repetition flashcard system

- Handles card display and review scheduling
- Manages review intervals (spaced repetition)
- Provides review statistics via AnkiConnect

**Deck Structure:**
```
Japanese (deck)
├── N5
│   ├── Vocab
│   └── Kanji
├── N4
│   ├── Vocab
│   └── Kanji
├── N3
│   ├── Vocab
│   └── Kanji
└── ...
```

**AnkiConnect API:**
- Endpoint: `http://localhost:8765`
- Actions: `addNote`, `findNotes`, `getDeckStats`, etc.

---

### 2. Agent (Brain)
**Role:** Orchestrator, progress tracker, study planner

**Responsibilities:**
- Fetch new content from JLPT sources
- Add cards to Anki via AnkiConnect
- Generate reading/writing exercises
- Track mastery in SQLite database
- Suggest what to study next
- Detect regression in skills
- Provide feedback on exercises

**Database:** `progress/progress.db` (SQLite)

---

### 3. Story Generator (Reading Engine)
**Role:** Generate reading practice material

**Source:** Refactored from `/home/arif/Projects/japanese-story-generator`

**API:** OpenRouter (free model: `google/gemma-4-31b-it:free`)

**How it works:**
1. Agent queries DB: "what vocabulary has user mastered?"
2. Story generator creates story using ONLY those words
3. User reads story (reading comprehension practice)
4. Agent generates comprehension questions based on level

---

### 4. Content Pipeline
**Role:** Fetch vocabulary and kanji from external sources

**Sources:**
| Source | Data | API/Method |
|--------|------|------------|
| Tanos.co.uk | JLPT word lists (N5-N1) | Web scraping |
| Jisho.org | Word readings, meanings, examples | REST API |
| Kanken Dojo | Kanji by JLPT level | Web scraping |

**Flow:**
```
JLPT Lists → Fetch Script → Raw Data → Processing → DB + Anki
```

---

## Data Flow

### Study Session Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    STUDY SESSION FLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User: "I want to study today"                              │
│                                                             │
│  1. Agent checks DB                                         │
│     └─ "What hasn't been studied recently?"                 │
│                                                             │
│  2. Agent fetches new items (if needed)                     │
│     └─ JLPT lists → Jisho API → AnkiConnect                 │
│                                                             │
│  3. User opens Anki                                         │
│     └─ Reviews flashcards (spaced repetition)               │
│                                                             │
│  4. User tells AI results                                   │
│     └─ "Got 15/20 correct, missed: X, Y, Z"                │
│                                                             │
│  5. Agent logs session                                      │
│     └─ Updates DB, calculates mastery                       │
│                                                             │
│  6. Agent generates reading exercise                        │
│     └─ Story using known vocab → comprehension questions    │
│                                                             │
│  7. User completes exercise                                 │
│     └─ Answers questions (adapted to level)                 │
│                                                             │
│  8. Agent logs and suggests next session                    │
│     └─ "Review these 3 words tomorrow"                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Data Storage

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA STORAGE                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Anki Database                                              │
│  └─ collection.anki2                                        │
│     ├─ Cards (with spaced repetition data)                  │
│     └─ Review history (Anki's internal tracking)            │
│                                                             │
│  Agent Database                                             │
│  └─ progress/progress.db                                    │
│     ├─ vocabulary (word list with metadata)                 │
│     ├─ kanji (character data)                               │
│     ├─ sessions (study session logs)                        │
│     ├─ item_reviews (per-item performance)                  │
│     ├─ stories (generated stories)                          │
│     └─ reading_sessions (comprehension results)             │
│                                                             │
│  File System                                                │
│  └─ data/jlpt/                                              │
│     ├─ n5_vocab.json                                        │
│     ├─ n4_vocab.json                                        │
│     └─ ...                                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## API Integrations

### AnkiConnect

**Base URL:** `http://localhost:8765`

**Key Actions:**
| Action | Purpose |
|--------|---------|
| `addNote` | Add a card to Anki |
| `findNotes` | Find cards matching query |
| `getDeckStats` | Get review statistics |
| `getReviews` | Get review history |
| `createDeck` | Create a new deck |

**Example Request:**
```python
import requests

def add_card(deck, front, back):
    return requests.post("http://localhost:8765", json={
        "action": "addNote",
        "version": 6,
        "params": {"note": {
            "deckName": deck,
            "modelName": "Basic",
            "fields": {
                "Front": front,
                "Back": back
            }
        }}
    })
```

---

### OpenRouter API

**Base URL:** `https://openrouter.ai/api/v1`

**Model:** `google/gemma-4-31b-it:free`

**Usage:** Story generation

**Example Request:**
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="your-openrouter-key"
)

message = client.chat.completions.create(
    model="google/gemma-4-31b-it:free",
    messages=[{"role": "user", "content": prompt}]
)
```

---

### Jisho API

**Base URL:** `https://jisho.org/api/v1/search/words`

**Usage:** Word lookup (readings, meanings, examples)

**Example Request:**
```python
import requests

def lookup_word(word):
    response = requests.get(
        f"https://jisho.org/api/v1/search/words?keyword={word}"
    )
    return response.json()
```

---

## Mastery Model

### Severity Scale

| Severity | Meaning | Maps to |
|----------|---------|---------|
| 0 | **Instant recall** (< 2 seconds) | Independent |
| 1 | **Slow recall** (2-5 seconds) | Independent |
| 2 | **Partial recall** (forgot reading OR meaning) | Needs review |
| 3 | **Complete miss** | Needs relearning |

### Mastery Criteria

To mark a vocabulary item as "mastered":

| Criterion | Requirement |
|-----------|-------------|
| Consecutive sessions | 5 |
| Severity per session | ≤ 1 |
| Time span | ≥ 7 days |
| Review count | ≥ 3 reviews in last 14 days |

### Regression Detection

**Triggers:**
1. Severity 3 on mastered item → immediate regression
2. 2+ sessions with severity ≥ 2 in last 3 days → regression

**Action:**
- Move item back to "in progress"
- Schedule for review

---

## File Structure

```
learn-jp/
├── AGENTS.md                    # Simplified mentor instructions
├── AGENTS.template.md           # Full mentor instructions
├── README.md                    # Project overview
│
├── progress/
│   ├── schema.sql               # Database schema
│   ├── progress.db              # SQLite database
│   ├── overview.md              # Compact progress index
│   ├── weaknesses.md            # Tracked weaknesses
│   ├── practice-plan.md         # Study schedule
│   └── queries/                 # SQL queries
│       └── mastery-check.sql
│
├── scripts/
│   ├── seed_anki.py             # Initial vocabulary seeding
│   ├── fetch_jlpt_vocab.py      # Fetch JLPT word lists
│   ├── fetch_jisho.py           # Jisho API client
│   ├── add_vocab.py             # Add custom vocabulary
│   └── hhmmss_to_seconds.py     # Time conversion utility
│
├── lib/
│   ├── __init__.py
│   ├── anki_connector.py        # AnkiConnect API wrapper
│   ├── story_generator.py       # Story generation (from refactored project)
│   ├── jisho_client.py          # Jisho API client
│   └── jlpt_fetcher.py          # JLPT vocabulary fetcher
│
├── data/
│   ├── jlpt/                    # JLPT vocabulary files
│   │   ├── n5_vocab.json
│   │   ├── n4_vocab.json
│   │   └── ...
│   └── kanji/                   # Kanji data files
│
├── docs/                        # This documentation
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── DATABASE.md
│   └── ...
│
└── .gitignore
```
