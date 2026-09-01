# Database Schema

## Overview

The `progress/progress.db` SQLite database tracks all learning progress. It works alongside Anki's database but provides more detailed tracking for the AI mentor.

## Tables

### 1. vocabulary

Stores all vocabulary items the user has been exposed to.

```sql
CREATE TABLE vocabulary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT UNIQUE NOT NULL,          -- e.g., "n5-v-001", "n4-v-023"
    content TEXT NOT NULL,                  -- the word (kanji): 食べる
    reading TEXT,                           -- hiragana: たべる
    meaning TEXT,                           -- English: to eat
    level TEXT NOT NULL,                    -- JLPT level: 'n5', 'n4', 'n3', etc.
    part_of_speech TEXT,                    -- 'verb', 'noun', 'adjective', etc.
    source TEXT,                            -- 'jlpt', 'genki', 'jisho'
    anki_note_id INTEGER,                   -- Anki note ID (for linking)
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
```

**Indexes:**
```sql
CREATE INDEX idx_vocab_level ON vocabulary(level);
CREATE INDEX idx_vocab_item_id ON vocabulary(item_id);
```

**Example Data:**
| item_id | content | reading | meaning | level | part_of_speech |
|---------|---------|---------|---------|-------|----------------|
| n5-v-001 | 食べる | たべる | to eat | n5 | verb |
| n5-v-002 | 飲む | のむ | to drink | n5 | verb |
| n5-v-003 | 水 | みず | water | n5 | noun |

---

### 2. kanji

Stores kanji characters with readings and meanings.

```sql
CREATE TABLE kanji (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT UNIQUE NOT NULL,          -- e.g., "n5-k-001"
    character TEXT NOT NULL,               -- the kanji: 人
    on_reading TEXT,                       -- on'yomi: ジン、ニン
    kun_reading TEXT,                      -- kun'yomi: ひと
    meanings TEXT,                         -- JSON array: ["person", "people"]
    level TEXT NOT NULL,                   -- JLPT level
    stroke_count INTEGER,                  -- stroke count
    anki_note_id INTEGER,                  -- Anki note ID
    created_at TEXT DEFAULT (datetime('now'))
);
```

**Example Data:**
| item_id | character | on_reading | kun_reading | meanings | level |
|---------|-----------|------------|-------------|----------|-------|
| n5-k-001 | 人 | ジン、ニン | ひと | ["person", "people"] | n5 |
| n5-k-002 | 日 | ニチ、ジツ | ひ、か | ["day", "sun"] | n5 |

---

### 3. grammar

Stores grammar patterns and structures.

```sql
CREATE TABLE grammar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT UNIQUE NOT NULL,          -- e.g., "n5-g-001"
    pattern TEXT NOT NULL,                 -- e.g., "～ます"
    structure TEXT,                        -- e.g., "Verb stem + ます"
    meaning TEXT NOT NULL,                 -- e.g., "polite present tense"
    level TEXT NOT NULL,                   -- JLPT level
    examples TEXT,                         -- JSON array of example sentences
    notes TEXT,                            -- Additional notes
    created_at TEXT DEFAULT (datetime('now'))
);
```

**Example Data:**
| item_id | pattern | structure | meaning | level |
|---------|---------|-----------|---------|-------|
| n5-g-001 | ～ます | Verb stem + ます | polite present tense | n5 |
| n5-g-002 | ～てください | て-form + ください | please do | n5 |

---

### 4. sessions

Logs each study session.

```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,                    -- YYYY-MM-DD
    type TEXT NOT NULL,                    -- 'anki', 'reading', 'writing'
    items_studied INTEGER,                 -- number of items studied
    correct INTEGER,                       -- number correct
    accuracy REAL,                         -- accuracy percentage (0-100)
    time_spent_seconds INTEGER,            -- total time in seconds
    notes TEXT,                            -- user notes
    created_at TEXT DEFAULT (datetime('now'))
);
```

**Indexes:**
```sql
CREATE INDEX idx_sessions_date ON sessions(date);
CREATE INDEX idx_sessions_type ON sessions(type);
```

**Example Data:**
| id | date | type | items_studied | correct | accuracy | time_spent_seconds |
|----|------|------|---------------|---------|----------|-------------------|
| 1 | 2026-08-29 | anki | 20 | 17 | 85.0 | 300 |
| 2 | 2026-08-29 | reading | 1 | 1 | 100.0 | 180 |
| 3 | 2026-08-30 | anki | 25 | 22 | 88.0 | 360 |

---

### 5. item_reviews

Tracks individual item performance within sessions.

```sql
CREATE TABLE item_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,           -- FK → sessions.id
    item_id TEXT NOT NULL,                 -- FK → vocabulary.item_id or kanji.item_id
    item_type TEXT NOT NULL,               -- 'vocabulary', 'kanji', 'grammar'
    severity INTEGER NOT NULL,             -- 0=instant, 1=slow, 2=partial, 3=miss
    response_time_ms INTEGER,              -- response time in milliseconds
    error_type TEXT,                       -- 'reading', 'meaning', 'spelling', NULL
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

**Indexes:**
```sql
CREATE INDEX idx_item_reviews_item ON item_reviews(item_id);
CREATE INDEX idx_item_reviews_session ON item_reviews(session_id);
CREATE INDEX idx_item_reviews_severity ON item_reviews(severity);
```

**Severity Scale:**
| Severity | Meaning | Response Time |
|----------|---------|---------------|
| 0 | Instant recall | < 2000ms |
| 1 | Slow recall | 2000-5000ms |
| 2 | Partial (forgot reading OR meaning) | > 5000ms or partial |
| 3 | Complete miss | N/A |

---

### 6. mastery

Tracks mastery status for each item.

```sql
CREATE TABLE mastery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT UNIQUE NOT NULL,          -- FK → vocabulary.item_id
    item_type TEXT NOT NULL,               -- 'vocabulary', 'kanji', 'grammar'
    status TEXT NOT NULL DEFAULT 'new',    -- 'new', 'learning', 'review', 'mastered'
    streak INTEGER DEFAULT 0,              -- consecutive sessions with severity ≤ 1
    last_review_date TEXT,                 -- YYYY-MM-DD
    next_review_date TEXT,                 -- YYYY-MM-DD (for scheduling)
    total_reviews INTEGER DEFAULT 0,
    correct_reviews INTEGER DEFAULT 0,
    mastery_date TEXT,                     -- when mastered (NULL if not mastered)
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
```

**Status Values:**
| Status | Meaning |
|--------|---------|
| `new` | Never reviewed |
| `learning` | In learning phase (< 3 reviews) |
| `review` | In review phase (3+ reviews, not mastered) |
| `mastered` | Met all mastery criteria |

**Mastery Criteria:**
```sql
-- An item is mastered when:
-- 1. streak >= 5 (5 consecutive sessions with severity ≤ 1)
-- 2. Total reviews >= 3 in last 14 days
-- 3. last_review_date is within 7 days of mastery_date
```

---

### 7. stories

Stores generated stories for reading practice.

```sql
CREATE TABLE stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,                    -- YYYY-MM-DD
    theme TEXT,                            -- story theme
    content TEXT NOT NULL,                 -- the story text
    vocab_used TEXT,                       -- JSON array of item_ids used
    vocab_count INTEGER,                   -- number of vocabulary items used
    difficulty TEXT,                       -- 'strict', 'flexible'
    length INTEGER,                        -- character count
    created_at TEXT DEFAULT (datetime('now'))
);
```

---

### 8. reading_sessions

Tracks reading comprehension exercises.

```sql
CREATE TABLE reading_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER,                      -- FK → stories.id
    date TEXT NOT NULL,                    -- YYYY-MM-DD
    time_spent_seconds INTEGER,
    comprehension_score REAL,              -- 0.0 to 1.0
    questions_answered INTEGER,
    questions_correct INTEGER,
    new_words_learned TEXT,                -- JSON array of new item_ids
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (story_id) REFERENCES stories(id)
);
```

---

### 9. violation_queue

Stores vocabulary violations from story generation, prioritized for learning.

```sql
CREATE TABLE violation_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT UNIQUE NOT NULL,              -- the violation word (kanji)
    reading TEXT,                           -- hiragana reading
    meaning TEXT,                           -- English meaning
    pos TEXT,                               -- part of speech
    jlpt_level TEXT,                        -- JLPT level of this word
    level_distance INTEGER,                -- distance from user's current level
    priority INTEGER NOT NULL,              -- 1 = introduce soon, 2 = later
    first_seen DATE,                        -- first time seen as violation
    last_seen DATE,                         -- most recent sighting
    frequency INTEGER DEFAULT 1,           -- how many times seen as violation
    status TEXT DEFAULT 'queued',           -- 'queued', 'promoted', 'introduced', 'skipped'
    source_story_id INTEGER,               -- FK → stories.id (which story revealed this)
    promoted_date DATE,                    -- when moved from queue to vocabulary
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (source_story_id) REFERENCES stories(id)
);

CREATE INDEX idx_queue_priority ON violation_queue(priority);
CREATE INDEX idx_queue_status ON violation_queue(status);
CREATE INDEX idx_queue_level ON violation_queue(jlpt_level);
```

**Priority Values:**
| Priority | Meaning | When to Introduce |
|----------|---------|-------------------|
| 1 | High priority | When user reaches next JLPT level |
| 2 | Medium priority | Two levels ahead |
| 3 | Low priority | Three+ levels ahead (rarely) |

**Status Values:**
| Status | Meaning |
|--------|---------|
| queued | Waiting in priority queue |
| promoted | Ready to add to vocabulary (user reached appropriate level) |
| introduced | Added to vocabulary and Anki |
| skipped | Decided not to learn (too rare, too advanced, etc.) |

**Example Data:**
| word | reading | jlpt_level | priority | frequency | status |
|------|---------|------------|----------|-----------|--------|
| 雪 | ゆき | n4 | 1 | 3 | queued |
| 痛い | いたい | n5 | 1 | 2 | queued |
| 幸せ | しあわせ | n3 | 2 | 1 | queued |

**How it works:**
1. Story generated → violation detected (e.g., 雪)
2. Heuristic grades it: N4 word, user is at N5 → priority 1
3. Added to violation_queue
4. When user starts N4 → words with priority 1 get promoted
5. User adds promoted words to Anki

---

## Relationships

```
┌─────────────────┐      ┌─────────────────┐
│   vocabulary    │      │     kanji       │
│                 │      │                 │
│  item_id (PK)   │      │  item_id (PK)   │
└────────┬────────┘      └────────┬────────┘
         │                        │
         │    ┌───────────────────┘
         │    │
         ▼    ▼
┌─────────────────────────────────────────┐
│            item_reviews                 │
│                                         │
│  item_id (FK)                           │
│  session_id (FK)                        │
│  severity, response_time_ms, error_type │
└─────────────────────────────────────────┘
         │
         │
         ▼
┌─────────────────┐
│    sessions     │
│                 │
│  id (PK)        │
│  date, type     │
└─────────────────┘
```

---

## Common Queries

### Get all items at a specific level
```sql
SELECT * FROM vocabulary WHERE level = 'n5';
```

### Get items needing review (severity > 0 in last session)
```sql
SELECT v.* 
FROM vocabulary v
JOIN item_reviews ir ON v.item_id = ir.item_id
JOIN (
    SELECT item_id, MAX(session_id) as last_session
    FROM item_reviews
    GROUP BY item_id
) latest ON ir.item_id = latest.item_id AND ir.session_id = latest.last_session
WHERE ir.severity > 0;
```

### Get mastery statistics
```sql
SELECT 
    status,
    COUNT(*) as count
FROM mastery
GROUP BY status;
```

### Get items with broken mastery streak
```sql
SELECT item_id, streak, last_review_date
FROM mastery
WHERE status = 'mastered'
  AND streak < 5;
```

### Get study history for last 7 days
```sql
SELECT date, type, items_studied, accuracy
FROM sessions
WHERE date >= date('now', '-7 days')
ORDER BY date DESC;
```

### Get queued violations ready for promotion (when user advances a level)
```sql
SELECT * FROM violation_queue
WHERE status = 'queued'
  AND jlpt_level = 'n5'  -- words at the level user just completed
  AND priority = 1
ORDER BY frequency DESC;  -- most frequent first
```

### Get most frequent violations (to prioritize learning)
```sql
SELECT word, reading, frequency, jlpt_level
FROM violation_queue
WHERE status = 'queued'
ORDER BY frequency DESC
LIMIT 10;
```

### Check if a word is already queued
```sql
SELECT id, status FROM violation_queue
WHERE word = '雪';
```

---

## Data Sources for Vocabulary Enrichment

### Jisho API
Provides vocabulary data:
- Word, reading, multiple meanings
- Parts of speech, JLPT level
- Usage notes and restrictions
- Alternative forms

### KANJIDIC
Provides kanji data:
- On'yomi and Kun'yomi readings
- Kanji meanings
- JLPT level (for kanji)
- Grade level (Japanese school grade)
- Stroke count

### Example Sentence Gap
Example sentences are available on Jisho web pages but not via API. For the current version:
- Cards will not include example sentences
- Story generator provides contextual reading practice instead
- Manual enrichment is possible via AnkiConnect update

---

## Migration Notes

- Database is created by `scripts/init_db.py`
- Schema version tracked in `schema_version` table
- Use `progress/schema.sql` as source of truth
- All timestamps use ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
