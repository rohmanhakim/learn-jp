# Architecture

## Core Principle

**CLI-first, deterministic-heavy, LLM-minimal.**

```
┌─────────────────────────────────────────────────────────────┐
│              CLI + DETERMINISTIC SCRIPTS                    │
│              (Required - 90% of operations)                 │
├─────────────────────────────────────────────────────────────┤
│  • learn-jp start/end/status                                │
│  • AnkiConnect integration                                  │
│  • Mastery calculation                                      │
│  • Violation grading (heuristic)                            │
│  • Level progression (threshold)                            │
│  • Grammar Tier 1 (lookup table)                            │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ calls only for content
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              OPENROUTER API                                 │
│              (Required - 10% content generation)            │
├─────────────────────────────────────────────────────────────┤
│  • Story generation                                         │
│  • Question generation                                      │
│  • Grammar Tier 2-3                                         │
│  • Writing evaluation                                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              AGENT (pi) - OPTIONAL                          │
│              (Natural language interface only)              │
├─────────────────────────────────────────────────────────────┤
│  • Not required for workflow                                │
│  • Calls same CLI commands                                  │
│  • Provides natural language convenience                    │
└─────────────────────────────────────────────────────────────┘
```

---

## System Components

### 1. CLI Commands (Required)

| Command | Purpose | LLM? |
|---------|---------|------|
| `learn-jp start` | Pre-flight checks, show deck info | No |
| `learn-jp end` | Pull reviews, calculate mastery, show summary | No |
| `learn-jp status` | Show progress, next steps | No |
| `learn-jp story` | Generate story + comprehension quiz | OpenRouter |
| `learn-jp grammar` | Grammar drill session | Tier 1: No, Tier 2-3: OpenRouter |
| `learn-jp write` | Writing practice | OpenRouter |

### 2. Anki (Drill Engine)

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
├── Enrichment     ← violation words
└── ...
```

**AnkiConnect API:**
- Endpoint: `http://localhost:8765`
- Actions: `addNote`, `findNotes`, `getDeckStats`, `getReviews`, `createDeck`

### 3. Progress Database (SQLite)

**Role:** Track all learning progress

**File:** `progress/progress.db`

**Tables:**
- `vocabulary` - word list with metadata
- `kanji` - kanji data (unused initially)
- `grammar` - grammar patterns
- `sessions` - study session logs
- `item_reviews` - per-item performance
- `mastery` - mastery status per item
- `stories` - generated stories
- `reading_sessions` - comprehension results
- `violation_queue` - vocabulary violations
- `grammar_progress` - grammar mastery
- `grammar_question_cache` - cached grammar questions
- `writing_sessions` - writing practice logs
- `session_violations` - violation history
- `user_config` - system configuration

### 4. Content Pipeline

**Role:** Fetch vocabulary from JLPT sources

**Sources:**
| Source | Data | API/Method |
|--------|------|------------|
| Tanos.co.uk | JLPT word lists (N5-N1) | Web scraping |
| Jisho.org | Word readings, meanings, JLPT level | REST API |
| KANJIDIC | Kanji readings, meanings | XML/Text file |

**Flow:**
```
JLPT Lists → Fetch Script → Raw Data → Processing → DB + Anki
                    ↓
              Jisho API (vocabulary)
                    ↓
              Enriched card → AnkiConnect
```

### 5. Story Generator (OpenRouter)

**Role:** Generate reading practice material

**Package:** `japanese-story-generator`

**API:** OpenRouter via `OpenRouterClient` class

**Default Model:** `google/gemma-4-26b-a4b-it:free`

**Classes:**
- `StoryGenerator` - Generate stories from vocabulary
- `ConjugationVerifier` - Verify vocabulary usage in stories

**How it works:**
1. System queries DB for known vocabulary
2. Story generator creates story using ONLY those words
3. Conjugation verifier identifies violations
4. Violations graded and added to learning queue

### 6. Grammar System (Three-Tier)

**Role:** Grammar pattern practice

```
┌─────────────────────────────────────────────────────────────┐
│                    TIER 1: CORE GRAMMAR                     │
│                    (Deterministic, zero tokens)             │
├─────────────────────────────────────────────────────────────┤
│  • Pre-defined drills for essential patterns                │
│  • ~200 most essential patterns (N5-N4)                     │
│  • Template variations (no LLM needed)                      │
└─────────────────────────────────────────────────────────────┘
                         │
                         │ if pattern not in Tier 1
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    TIER 2: CACHED LLM                       │
│                    (One-time token cost)                    │
├─────────────────────────────────────────────────────────────┤
│  • LLM generates question once                              │
│  • Cache in database with metadata                          │
│  • Reuse with variations (change names/verbs)               │
└─────────────────────────────────────────────────────────────┘
                         │
                         │ if not cached or edge case
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    TIER 3: DYNAMIC LLM                      │
│                    (Per-session tokens)                     │
├─────────────────────────────────────────────────────────────┤
│  • Edge cases, rare patterns                                │
│  • Open-ended production tasks                              │
│  • Answer evaluation for complex responses                  │
└─────────────────────────────────────────────────────────────┘
```

### 7. Reading Comprehension

**Role:** Test understanding of generated stories

**Adaptive Question Design:**

| Level | Vocabulary | Language | Types |
|-------|-----------|----------|-------|
| N5 early | < 100 | English | Multiple choice |
| N5 late | 100-200 | English | MC + short answer |
| N4 | 200-500 | Mixed | MC + short answer + fill blank |
| N3 | 500-1000 | Japanese | Short answer + production |
| N2-N1 | 1000+ | Japanese | Open-ended + analysis |

**Question Count:** Adaptive (3-5 based on story length), max configurable.

### 8. Writing Practice

**Role:** Production skill complementing reading

**Progressive Types:**

| Level | Writing Type |
|-------|-------------|
| N5 early | Guided construction (word bank) |
| N5 late | Simple translation |
| N4 | Translation with grammar |
| N3+ | Free writing prompts |

---

## Data Flow

### Daily Study Session

```
$ learn-jp start
    │
    ├─ Check Anki is running
    ├─ Show current level and deck info
    └─ User opens Anki, reviews cards

$ learn-jp end
    │
    ├─ Pull reviews from AnkiConnect
    ├─ Calculate mastery per item
    ├─ Update progress database
    ├─ Check level progression
    └─ Show session summary

$ learn-jp story (optional)
    │
    ├─ Query known vocabulary
    ├─ Generate story (OpenRouter)
    ├─ Run comprehension quiz
    ├─ Track score
    └─ Add violations to learning queue
```

### Level Progression

```
When mastery >= 80% for vocab + grammar:
    │
    ├─ Add queued violations (immediate)
    ├─ Fetch foundation batch (top 50 words)
    ├─ Update current level
    └─ User continues with new level
```

---

## Mastery Models

### Vocabulary Mastery

| Criterion | Requirement |
|-----------|-------------|
| Consecutive sessions | 5 |
| Severity per session | ≤ 1 |
| Time span | ≥ 7 days |
| Review count | ≥ 3 in last 14 days |

### Grammar Mastery

| Criterion | Requirement |
|-----------|-------------|
| Sessions | ≥ 3 |
| Accuracy per session | ≥ 80% |
| Time span | ≥ 7 days |
| Regression trigger | accuracy < 60% after mastery |

### Reading Comprehension Mastery

| Criterion | Requirement |
|-----------|-------------|
| Sessions | ≥ 3 |
| Score per session | ≥ 70% |
| Time span | ≥ 7 days |
| Regression trigger | score < 50% after mastery |

---

## Error Handling

| Scenario | Handling |
|----------|----------|
| Anki not running | Block session, notify user |
| OpenRouter API down | Fallback to cached stories |
| Database locked | Error message, exit |
| Network unavailable | Offline mode (limited) |

---

## File Structure

```
learn-jp/
├── learn_jp/                    # Main package
│   ├── __init__.py
│   ├── cli.py                  # CLI entry point
│   ├── session.py              # Session management
│   ├── progress.py             # Progress tracking
│   ├── grammar.py              # Grammar system
│   ├── reading.py              # Reading comprehension
│   ├── writing.py              # Writing practice
│   ├── errors.py               # Error handling
│   └── config.py               # Configuration
│
├── lib/                         # Existing library code
│   ├── anki_connector.py
│   ├── jisho_client.py
│   ├── jlpt_fetcher.py
│   └── ...
│
├── scripts/                     # Utility scripts
│   ├── init_db.py
│   ├── seed_anki.py
│   └── ...
│
├── progress/                    # Database
│   ├── schema.sql
│   └── progress.db
│
├── data/                        # Cached data
│   ├── jlpt/
│   ├── grammar/                # Tier 1 grammar drills
│   └── cache/
│
└── docs/                        # Documentation
    ├── README.md
    ├── ARCHITECTURE.md
    ├── DATABASE.md
    ├── WORKFLOW-FINDINGS.md
    └── ...
```

---

## External APIs

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

### OpenRouter API

**Base URL:** `https://openrouter.ai/api/v1`

**Default Model:** `google/gemma-4-26b-a4b-it:free`

**Usage:** Story generation, question generation, writing evaluation

### Jisho API

**Base URL:** `https://jisho.org/api/v1/search/words`

**Usage:** Word lookup (readings, meanings, JLPT level)

---

## LLM Usage Summary

| Layer | Model | Purpose | Required? |
|-------|-------|---------|----------|
| Deterministic | None | 90% of operations | ✅ Yes |
| OpenRouter | Small (Gemma/Qwen) | Content generation | ✅ Yes |
| Agent | Capable (Claude/GPT-4) | Natural language | ❌ No |

**System works with just OpenRouter API key. No capable models required.**
