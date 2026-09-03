# Workflow Design Findings

**Status:** Temporary doc capturing design discussions
**Date:** 2025-09-01

---

## Problem Statement

Current system design has gaps that create friction and confusion:

1. **Too much manual work** during sessions
2. **No clear guidance** on when to use story generation
3. **Deck bloat** from mixing JLPT curriculum + violation enrichment
4. **Agent dependency** for basic operations

---

## Ideal Workflow (User Requirement)

```
$ learn-jp start
  → System auto-checks decks, fetches if missing
  → Shows: "Ready. Deck: Japanese::N5::Vocab"

[Open Anki, do reviews]

$ learn-jp end
  → System auto-pulls reviews from AnkiConnect
  → Calculates mastery, shows summary
  → Updates progress

$ learn-jp status
  → Shows current level, mastery %, next milestones
```

**Key principles:**
- CLI-based (no agent conversation required)
- Automatic session recording (no manual reporting)
- One command to start, one to end
- System adjusts to current skill state

---

## Gap Analysis: Current Design vs Ideal

| Aspect | Current Design | Ideal Design |
|--------|---------------|--------------|
| Interface | Agent conversation | CLI commands |
| Session start | "I want to study today" | `learn-jp start` |
| Session recording | Manual: "Got 15/20 correct" | Auto via AnkiConnect |
| Story generation | Tightly coupled to session | Separate, optional feature |
| Agent dependency | Required for orchestration | Optional layer |

### What's Missing

1. **CLI entry point** (`learn-jp start/end/status`)
2. **Automatic session recording** from AnkiConnect
3. **Decoupled story generation** (not part of every session)
4. **Deterministic orchestration** (scripts, not LLM)

---

## Story Generation: When and How

### The Problem

When vocabulary is small:
- Story generator produces many violations (30-60%)
- Adding all violations + JLPT curriculum = overwhelming deck
- No guidance on what to prioritize

### The Solution: Phased Approach

```
Phase 1: Foundation (0-150 words)
├── Focus ONLY on JLPT curriculum
├── Do NOT use story generation
├── Reason: Stories are incoherent, violations too high
└── Deck size: Just JLPT words

Phase 2: Enrichment (150+ words)
├── Story generation becomes useful
├── Violations drop to ~15-20%
├── Add only violations at current JLPT level
└── Deck size: JLPT + filtered violations

Phase 3: Reading Comprehension (500+ words)
├── Violations < 5%
├── Stories are coherent
├── Focus shifts to comprehension practice
└── Deck size: Mostly stable
```

### Violation Filtering Rules

| Violation Level | Action | Reason |
|-----------------|--------|--------|
| Same as current JLPT | **Add now** | Should know this |
| One level above | **Queue** | Good next step |
| Two+ levels above | **Skip** | Too advanced, will overwhelm |

**Example:** User at N5, violation is N3 → Skip it.

### Deck Size Management

| Scenario | Strategy |
|----------|----------|
| < 150 words | JLPT only, no violations |
| 150-300 words | JLPT + N5 violations only |
| 300-500 words | JLPT + N5/N4 violations |
| 500+ words | Full enrichment, low violation rate |

---

## System Architecture

### Core Principle

**CLI-first, deterministic-heavy, LLM-minimal.**

```
┌─────────────────────────────────────────────────────────┐
│              CLI + DETERMINISTIC SCRIPTS                │
│              (Required - handles 90% of operations)     │
├─────────────────────────────────────────────────────────┤
│  • learn-jp start/end/status                            │
│  • AnkiConnect integration                              │
│  • Mastery calculation                                  │
│  • Violation grading (heuristic)                        │
│  • Level progression (threshold)                        │
│  • Session recording                                    │
│  • Progress tracking                                    │
│  • Grammar Tier 1 (lookup table)                        │
│  • Template variations                                  │
└─────────────────────────────────────────────────────────┘
                         │
                         │ calls only for content generation
                         ▼
┌─────────────────────────────────────────────────────────┐
│              OPENROUTER API                             │
│              (Required - 10% content generation)        │
├─────────────────────────────────────────────────────────┤
│  • Story generation                                     │
│  • Comprehension question generation                    │
│  • Grammar questions (Tier 2-3)                         │
│  • Writing evaluation                                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              AGENT (pi) - OPTIONAL                      │
│              (Natural language interface only)          │
├─────────────────────────────────────────────────────────┤
│  • Not required for workflow                            │
│  • Calls same CLI commands                              │
│  • Provides natural language convenience                │
└─────────────────────────────────────────────────────────┘
```

### Components

| Component | Type | Required? | LLM? |
|-----------|------|-----------|------|
| `learn-jp start` | CLI command | ✅ Yes | No |
| `learn-jp end` | CLI command | ✅ Yes | No |
| `learn-jp status` | CLI command | ✅ Yes | No |
| `learn-jp story` | CLI command | ✅ Yes | OpenRouter |
| `learn-jp grammar` | CLI command | ✅ Yes | Tier 1: No, Tier 2-3: OpenRouter |
| `learn-jp write` | CLI command | ✅ Yes | OpenRouter |
| Deck fetching | Deterministic script | ✅ Yes | No |
| Session recording | AnkiConnect API | ✅ Yes | No |
| Mastery calculation | SQL queries | ✅ Yes | No |
| Violation grading | Heuristic algorithm | ✅ Yes | No |
| Progress reports | SQL + formatting | ✅ Yes | No |
| Story generation | OpenRouter API | ✅ Yes | Yes (small model) |
| Comprehension questions | OpenRouter API | ✅ Yes | Yes (small model) |
| Grammar (Tier 1) | Pre-defined drills | ✅ Yes | No |
| Grammar (Tier 2) | Cached + variation | ✅ Yes | Once |
| Grammar (Tier 3) | Dynamic OpenRouter | ✅ Yes | Yes |
| Grammar tracking | SQL queries | ✅ Yes | No |
| **Agent (pi)** | Optional layer | ❌ No | Capable model |

### No Agent Required

The system works completely via CLI:

```bash
# Start session
$ learn-jp start
  ✓ Anki running
  Current level: N5
  Ready! Open Anki and review.

# End session (auto-pull reviews)
$ learn-jp end
  Session Summary
  Reviews: 25, Correct: 20 (80%)
  N5 Vocab: 180/200 mastered (90%)

# Check progress
$ learn-jp status
  Vocabulary: 90%, Grammar: 56%
  Ready for N4: No (grammar needs work)

# Story practice
$ learn-jp story
  [Generates story, runs quiz, tracks score]

# Grammar drill
$ learn-jp grammar
  [Selects drill, tracks mastery]

# Writing practice
$ learn-jp write
  [Gets prompt, evaluates, tracks progress]
```

### Agent Usage (Optional)

If using agent (pi), it just calls CLI commands:

```
User: "I want to study"
Agent: calls `learn-jp start`
Agent: presents results in natural language

User: "How's my progress?"
Agent: calls `learn-jp status`
Agent: formats nicely for user
```

**Agent is convenience, not requirement.**

### LLM Usage Split

| Layer | Model | Purpose | Required? |
|-------|-------|---------|----------|
| Deterministic | None | 90% of operations | ✅ Yes |
| OpenRouter | Small (Gemma/Qwen) | Content generation | ✅ Yes |
| Agent | Capable (Claude/GPT-4) | Natural language | ❌ No |

**System works with just OpenRouter API key. No capable models required.**

---

## Implementation Priorities

### Phase 2 (Current): Content Pipeline
- [x] JLPT vocabulary fetcher
- [x] Jisho client
- [ ] Anki card creation scripts
- [ ] CLI entry point (`learn-jp`)

### Phase 3: Progress Tracking
- [ ] Automatic session recording (AnkiConnect)
- [ ] Mastery calculation engine
- [ ] `learn-jp status` command
- [ ] `learn-jp start/end` commands

### Phase 4: Violation Detection
- [ ] Story generation integration
- [ ] Violation grading heuristic
- [ ] Level-based filtering
- [ ] Enrichment word management

### Phase 5: Reading Comprehension
- [ ] Comprehension question generation
- [ ] Reading session tracking
- [ ] Transition detection (violations < 5%)

### Phase 6: Grammar Study
- [ ] Define Tier 1 core grammar patterns (N5-N4)
- [ ] Create pre-defined drills for Tier 1
- [ ] Build question caching system (Tier 2)
- [ ] Implement adaptive question format
- [ ] Build grammar tracking (same model as vocabulary)
- [ ] Integrate Tier 3 dynamic LLM generation

---

## Reading Comprehension: Adaptive Question Design

### Question Types

| Type | Category | Description |
|------|----------|-------------|
| Multiple choice | Receptive | Recognize correct answer |
| Fill in blank | Partial production | Complete a sentence |
| Short answer | Production | Write answer in language |
| Use word in sentence | Production | Create new sentence |
| Summarize | Production | Extended writing |

**Receptive** = understanding input (reading, listening)
**Productive** = creating output (writing, speaking)

### Adaptive Strategy by Level

| Level | Vocabulary | Language | Types | Production |
|-------|-----------|----------|-------|------------|
| N5 early | < 100 | English | Multiple choice | None |
| N5 late | 100-200 | English | MC + short answer | Minimal |
| N4 | 200-500 | Mixed | MC + short answer + fill blank | Simple |
| N3 | 500-1000 | Japanese | Short answer + production | Moderate |
| N2-N1 | 1000+ | Japanese | Open-ended + analysis | Extended |

### Why Adaptive?

- Early learners lack vocabulary for Japanese questions
- Open-ended too hard with small vocabulary
- Multiple choice works for recognition stage
- Production ability grows with vocabulary

### Example Progression

```
Session 1 (50 words):
  Q: Where did Taro go?
     A) Store  B) School  C) Home
  → English, multiple choice, recognition only

Session 20 (150 words):
  Q: What did Taro buy?
  → English, short answer, minimal production

Session 50 (300 words):
  Q: 太郎はどこに______________？
  → Japanese, fill blank, partial production

Session 100 (600 words):
  Q: 太郎は何を買いましたか？
  → Japanese, short answer, production

Session 200 (1200 words):
  Q: なぜ太郎は市場に行きましたか？詳しく説明してください。
  → Japanese, open-ended, extended production
```

### Deterministic Config

```python
def get_question_config(vocab_size: int, level: str) -> dict:
    if vocab_size < 100:
        return {"language": "english", "types": ["multiple_choice"], "production": False}
    elif vocab_size < 200:
        return {"language": "english", "types": ["multiple_choice", "short_answer"], "production": "minimal"}
    elif vocab_size < 500:
        return {"language": "mixed", "types": ["multiple_choice", "short_answer", "fill_blank"], "production": "simple"}
    elif vocab_size < 1000:
        return {"language": "japanese", "types": ["short_answer", "production"], "production": "moderate"}
    else:
        return {"language": "japanese", "types": ["open_ended", "production", "analysis"], "production": "extended"}
```

---

## Reading Comprehension: Performance Tracking

### Metrics (All Deterministic)

| Metric | How to Calculate | Equivalent to Anki |
|--------|------------------|--------------------|
| Comprehension score | correct / total | severity scale |
| Score trend | AVG(score) over time | mastery progression |
| Weak vocabulary | Words missed in questions | weak items |
| Difficulty readiness | AVG(score) >= 0.8 | level mastery |
| Regression | score < 50% after mastery | severity spike |

### Mastery Criteria

| Criterion | Requirement |
|-----------|-------------|
| Sessions | >= 3 |
| Score per session | >= 70% |
| Time span | >= 7 days |
| Regression trigger | score < 50% after mastery |

### Database Schema

```sql
CREATE TABLE comprehension_performance (
    id INTEGER PRIMARY KEY,
    story_id INTEGER,
    date TEXT,
    score REAL,              -- 0.0 to 1.0
    questions_total INTEGER,
    questions_correct INTEGER,
    time_spent INTEGER,
    difficulty_level TEXT,   -- n5, n4, etc.
    vocab_coverage REAL,    -- % of story words user knows
    question_types TEXT,     -- JSON: ["multiple_choice", "short_answer"]
    language_used TEXT       -- english, japanese, mixed
);

CREATE TABLE comprehension_missed_words (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,
    word TEXT,
    question_id INTEGER,
    FOREIGN KEY (session_id) REFERENCES comprehension_performance(id)
);
```

### Example Queries

```sql
-- Ready for harder stories?
SELECT AVG(score) as avg_score
FROM comprehension_performance
WHERE difficulty_level = 'n5'
  AND date >= date('now', '-14 days');
-- If avg_score >= 0.8 → ready for N4 stories

-- What vocabulary needs work?
SELECT word, COUNT(*) as times_missed
FROM comprehension_missed_words
GROUP BY word
ORDER BY times_missed DESC
LIMIT 10;

-- Is user improving?
SELECT date, AVG(score) as daily_score
FROM comprehension_performance
GROUP BY date
ORDER BY date DESC
LIMIT 7;

-- Comprehension mastery status
SELECT 
    difficulty_level,
    COUNT(*) as sessions,
    AVG(score) as avg_score,
    CASE 
        WHEN COUNT(*) >= 3 AND AVG(score) >= 0.7 THEN 'mastered'
        ELSE 'in_progress'
    END as status
FROM comprehension_performance
GROUP BY difficulty_level;
```

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   DETERMINISTIC LAYER                   │
├─────────────────────────────────────────────────────────┤
│  • Track score per session                              │
│  • Track which words were missed                        │
│  • Calculate average score                              │
│  • Detect improvement/decline                           │
│  • Detect readiness for next difficulty                 │
│  • Aggregate weak vocabulary                            │
│  • Determine question format (language, type, count)    │
└─────────────────────────────────────────────────────────┘
                         │
                         │ uses data from
                         ▼
┌─────────────────────────────────────────────────────────┐
│                      LLM LAYER                          │
├─────────────────────────────────────────────────────────┤
│  • Generate questions (in determined format)            │
│  • Evaluate open-ended answers                          │
│  • Provide feedback/explanation                         │
└─────────────────────────────────────────────────────────┘
```

---

## Grammar Study: Three-Tier Architecture

### The Problem

- Japanese grammar has 800+ patterns across N5-N1
- Pre-defined drills for all patterns is massive work (~2400-4000 drills)
- But grammar patterns are FIXED (unlike creative stories)
- Need balance: deterministic where possible, LLM where needed

### Solution: Three-Tier System

```
┌─────────────────────────────────────────────────────────┐
│                    TIER 1: CORE GRAMMAR                 │
│                    (Deterministic, zero tokens)         │
├─────────────────────────────────────────────────────────┤
│  • Pre-defined drills for essential patterns            │
│  • N5: ～ます, ～ない, ～て, ～た, adj+です                 │
│  • N4: ～ている, ～てしまう, ～そうだ                       │
│  • ~200 most essential patterns                         │
│  • Template variations (no LLM needed)                  │
└─────────────────────────────────────────────────────────┘
                         │
                         │ if pattern not in Tier 1
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    TIER 2: CACHED LLM                   │
│                    (One-time token cost)                │
├─────────────────────────────────────────────────────────┤
│  • LLM generates question once                          │
│  • Cache in database with metadata                      │
│  • Reuse with variations (change names/verbs)           │
│  • Tracks effectiveness per question                    │
└─────────────────────────────────────────────────────────┘
                         │
                         │ if not cached or edge case
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    TIER 3: DYNAMIC LLM                  │
│                    (Per-session tokens)                 │
├─────────────────────────────────────────────────────────┤
│  • Edge cases, rare patterns                            │
│  • Open-ended production tasks                          │
│  • Answer evaluation for complex responses              │
│  • Grammar explanations when asked                      │
└─────────────────────────────────────────────────────────┘
```

### What Goes Where

| Tier | Patterns | Drill Type | LLM? | Token Cost |
|------|----------|-----------|------|------------|
| **Tier 1** | ～ます, ～ない, ～て, ～た, adj+です | MC, fill blank | No | Zero |
| **Tier 2** | ～ている, ～てしまう, ～そうだ | Cached + variation | Once | One-time |
| **Tier 3** | Rare patterns, production tasks | Dynamic generation | Yes | Per session |

### Tier 1: Core Grammar Example

```python
TIER1_GRAMMAR = {
    "n5": [
        {
            "pattern": "～ます",
            "structure": "Verb stem + ます",
            "meaning": "Polite present/future",
            "drills": [
                {
                    "type": "multiple_choice",
                    "question": "What is the polite form of 食べる?",
                    "options": ["食べる", "食べて", "食べます"],
                    "answer": "C"
                },
                {
                    "type": "fill_blank",
                    "sentence": "毎日、日本語を____。",
                    "options": ["勉強する", "勉強して", "勉強します"],
                    "answer": "勉強します"
                }
            ]
        }
    ]
}
```

### Tier 2: Caching Strategy

**Flow:**
1. User encounters pattern not in Tier 1
2. System calls LLM: "Generate fill-blank drill for ～ている"
3. LLM returns question
4. Cache in DB with metadata
5. Future sessions: reuse with variations
   - "太郎は今、本を____。" → "マリーは今、音楽を____。"
   - Template-based variation, no LLM needed

**Smart Reuse Logic:**

```python
def get_grammar_question(pattern: str, mastery: float) -> dict:
    # 1. Try cached question with good effectiveness
    cached = db.execute("""
        SELECT * FROM grammar_question_cache
        WHERE pattern = ?
          AND difficulty BETWEEN ? - 0.2 AND ? + 0.2
        ORDER BY effectiveness DESC, times_used ASC
        LIMIT 1
    """, (pattern, mastery, mastery))
    
    if cached:
        return generate_variation(cached)  # No LLM
    
    # 2. Generate new with LLM
    new_question = llm_generate(pattern, mastery)
    cache_question(new_question)
    return new_question
```

**When to Reuse vs Generate:**

| Condition | Action |
|-----------|--------|
| Question exists, effectiveness > 70% | Reuse (variation) |
| Question exists, effectiveness < 50% | Reuse more (needs practice) |
| No question for this pattern | Generate new |
| All questions used recently | Generate new variation |

### Adaptive Question Format

Adapt based on mastery level:

```python
def get_question_format(mastery: float) -> dict:
    if mastery < 0.3:
        return {
            "type": "multiple_choice",
            "language": "english",
            "description": "Recognition stage"
        }
    elif mastery < 0.7:
        return {
            "type": "fill_blank_options",
            "language": "mixed",
            "description": "Practice stage"
        }
    else:
        return {
            "type": "transform",
            "language": "japanese",
            "description": "Mastery stage"
        }
```

**Example by Stage:**

```
Mastery < 0.3 (Learning):
  Q: What is the て-form of 食べる?
     A) 食べる  B) 食べて  C) 食べます
  → Multiple choice, English

Mastery 0.3-0.7 (Practice):
  Q: ジョンは昨日、寿司を____いました。
     A) 食べる  B) 食べて  C) 食べます
  → Fill blank with options

Mastery > 0.7 (Mastery):
  Q: 食べる → て-form
  A: 食べて
  → Transform, Japanese
```

### Tracking (Same as Vocabulary)

**Mastery Criteria:**

| Criterion | Requirement |
|-----------|-------------|
| Sessions | >= 3 |
| Accuracy per session | >= 80% |
| Time span | >= 7 days |
| Regression trigger | accuracy < 60% after mastery |

**Database Schema:**

```sql
CREATE TABLE grammar_progress (
    pattern TEXT PRIMARY KEY,
    level TEXT,
    tier INTEGER,                    -- 1, 2, or 3
    mastery REAL DEFAULT 0,          -- 0.0 to 1.0
    sessions INTEGER DEFAULT 0,
    correct INTEGER DEFAULT 0,
    last_practiced TEXT,
    status TEXT DEFAULT 'new'        -- new, learning, mastered
);

CREATE TABLE grammar_question_cache (
    id INTEGER PRIMARY KEY,
    pattern TEXT NOT NULL,
    question_type TEXT NOT NULL,
    base_question TEXT NOT NULL,
    slots JSON,                     -- Template slots for variation
    correct_answer TEXT NOT NULL,
    options JSON,
    difficulty REAL,
    times_used INTEGER DEFAULT 0,
    times_correct INTEGER DEFAULT 0,
    effectiveness REAL,             -- times_correct / times_used
    created_at TEXT,
    last_used_at TEXT
);

CREATE TABLE grammar_sessions (
    id INTEGER PRIMARY KEY,
    date TEXT,
    pattern TEXT,
    question_type TEXT,
    correct INTEGER,
    time_spent INTEGER
);
```

### Token Usage Comparison

| Scenario | Without Caching | With This Design |
|----------|----------------|------------------|
| N5 grammar (80 patterns) | ~80,000 tokens | ~0 tokens (Tier 1) |
| N4 grammar (120 patterns) | ~120,000 tokens | ~12,000 tokens (Tier 2) |
| Daily practice | ~2,000 tokens/session | ~200 tokens/session |
| **Monthly** | ~60,000 tokens | ~6,000 tokens |
| **Savings** | | **~90%** |

### Why This Works for Learning

| Factor | Benefit |
|--------|--------|
| Spaced repetition | Same pattern seen repeatedly reinforces memory |
| Variation | Changing names/verbs prevents rote memorization |
| Consistency | Same grammar point, different context |
| Adaptation | Format matches current skill level |
| Tracking | Clear progress metrics |

---

## Level Progression

### When to Advance

Ready for next level when **both** conditions met:

| Skill | Threshold | Configurable |
|-------|-----------|--------------|
| Vocabulary mastery | >= 80% | Yes |
| Grammar mastery | >= 80% | Yes |

**No time minimum** - can advance as fast as mastery allows.

### Progression Logic

```python
def should_advance(level: str) -> bool:
    """Check if user is ready for next level."""
    vocab_mastery = get_vocab_mastery(level)
    grammar_mastery = get_grammar_mastery(level)
    
    threshold = get_config("level_threshold")  # default 0.8
    
    return vocab_mastery >= threshold and grammar_mastery >= threshold

def advance_level(current_level: str):
    """Advance to next level."""
    next_level = get_next_level(current_level)  # n5 → n4
    
    # 1. Add queued violations at current level
    add_queued_violations(current_level)
    
    # 2. Fetch foundation batch for next level
    fetch_foundation_batch(next_level)  # Top 50 common words
    
    # 3. Update user's current level
    update_config("current_level", next_level)
```

### Deck Management

**Structure:** Separate decks per level

```
Japanese::N5::Vocab     (active drilling)
Japanese::N5::Kanji     (active drilling)
Japanese::Enrichment     (violation words)
Japanese::N4::Vocab     (fetched when ready)
Japanese::N4::Kanji     (fetched when ready)
```

**Rules:**
- Keep old decks (don't delete)
- Anki still reviews mature cards automatically
- Violation words go to separate Enrichment deck
- Gradual fetch, not bulk

### Deck Fetching Strategy

**Hybrid approach:**

```
When advancing N5 → N4:

Step 1: Immediate (0 tokens)
└── Add all queued N5 violations marked as N4 level
    (Words you've already seen in stories)

Step 2: Foundation batch (0 tokens)
└── Add top 50 most common N4 words
    (Pre-defined list, deterministic)

Step 3: Story-guided (ongoing)
└── Each session, system checks:
    ├── Generate story with current vocab
    ├── Find violations
    ├── Filter: N4 level violations → add to deck
    └── Words appear naturally in reading context
```

**Why this works:**

| Phase | What Gets Added | Why |
|-------|-----------------|-----|
| Immediate | Queued violations | You've seen them, higher retention |
| Foundation | Top 50 common N4 | Essential for basic comprehension |
| Story-guided | New violations | Contextual, needed for reading |

### Violation Level Detection

**Deterministic** - no LLM needed.

**Three-tier lookup:**

```python
def get_word_level(word: str) -> str:
    """Hybrid: local first, then API if needed."""
    
    # 1. Check local JLPT lists (instant)
    local_level = check_local_lists(word)
    if local_level:
        return local_level
    
    # 2. Check database (words we've seen before)
    db_level = check_database(word)
    if db_level:
        return db_level
    
    # 3. Call Jisho API (comprehensive)
    api_level = call_jisho_api(word)
    if api_level:
        cache_to_database(word, api_level)
        return api_level
    
    return None
```

**Methods:**

| Method | Speed | Coverage | Cost |
|--------|-------|----------|------|
| Local JLPT lists | Instant | JLPT words only | Zero |
| Database cache | Fast | Previously looked up | Zero |
| Jisho API | Slow | All words | API calls |
| **Hybrid** | **Fast** | **All words** | **Minimal API calls** |

---

## Kanji Study

### Decision: Vocab Only (No Separate Kanji Study)

**Approach:** Learn kanji implicitly through vocabulary.

```
You learn: 食べる → implicitly learn kanji 食
You learn: 飲む → implicitly learn kanji 飲
You learn: 水 → learn single kanji word
```

### Why Vocab Only Works

| Aspect | Vocab Only | Separate Kanji |
|--------|-----------|----------------|
| Early progress | Faster | Slower |
| Complexity | Simpler | More complex |
| Reading ability | ✅ Sufficient | ✅ Also works |
| Kanji knowledge | Implicit | Explicit |

### Kanji Table Status

| Action | Decision |
|--------|----------|
| Keep table in schema | **Yes** (for future) |
| Populate initially | **No** |
| Use in code | **Not now** |
| Enable later | **Optional** |

### Phase Scope

```
Phase 2-5: No kanji table usage
├── Vocabulary: tracked ✅
├── Grammar: tracked ✅
├── Reading: tracked ✅
└── Kanji: table exists, unused ⏸️

Phase 6+ (optional): Enable kanji study
└── If user wants explicit kanji drilling
```

---

## Writing Practice (Production Skill)

### Decision: Yes, include writing practice

**Purpose:** Production skill complementing reading (receptive skill).

### Progression by Level

| Level | Writing Type | Example |
|-------|-------------|---------|
| N5 early | Guided construction (word bank) | "Make sentence: 食べる + 今日 + ごはん" |
| N5 late | Simple translation | "I eat sushi" → ? |
| N4 | Translation with grammar | "I ate sushi yesterday" → ? |
| N3+ | Free writing prompts | "Write about your weekend" |

### How It Fits with Existing Design

```
Reading (receptive) → Grammar (pattern) → Writing (production)

Story: "太郎は寿司を食べました"
  ↓
Grammar: ～ました (past polite)
  ↓
Writing: "Write what you ate yesterday using ～ました"
  ↓
User: "私は昨日、ラーメンを食べました"
  ↓
Evaluation: grammar ✓, vocabulary ✓, naturalness ✓
```

### Writing Types

| Type | Guided? | LLM Needed? | Best For |
|------|---------|-------------|----------|
| Word bank construction | Yes | No | Early learners |
| Translation | Yes | Optional | Pattern practice |
| Guided prompt | Semi | Yes | Contextual writing |
| Free writing | No | Yes | Advanced learners |

### Adaptive by Mastery

```python
def get_writing_prompt(vocab_size: int, grammar_mastery: float) -> dict:
    if vocab_size < 100:
        # Word bank construction
        return {
            "type": "construction",
            "words": ["食べる", "今日", "ごはん"],
            "prompt": "Make a sentence using these words"
        }
    elif vocab_size < 300:
        # Simple translation
        return {
            "type": "translation",
            "english": "I eat sushi",
            "hint": "Use ～ます form"
        }
    else:
        # Guided or free writing
        return {
            "type": "prompt",
            "prompt": "昨日、何を食べましたか？日本語で書いてください。",
            "grammar_hint": "～ました"
        }
```

### Evaluation

| Aspect | How to Check | LLM? |
|--------|-------------|------|
| Completeness | Did they write something? | No |
| Vocabulary used | Check against known vocab | No |
| Grammar correct | Check pattern usage | Optional |
| Naturalness | Does it sound right? | **Yes** |

### Session Flow

```
1. Anki drill (vocabulary/grammar)
2. Reading comprehension (story + questions)
3. Writing (production practice)
4. Summary
```

### Database Tracking

```sql
CREATE TABLE writing_sessions (
    id INTEGER PRIMARY KEY,
    date TEXT,
    prompt_type TEXT,        -- 'construction', 'translation', 'prompt', 'free'
    prompt TEXT,
    user_response TEXT,
    vocabulary_used TEXT,     -- JSON: words used
    grammar_patterns TEXT,    -- JSON: patterns used
    score REAL,              -- 0.0 to 1.0
    feedback TEXT,           -- LLM feedback
    time_spent INTEGER
);
```

---

## Error Handling

### Pre-flight Checks

```python
class ErrorHandler:
    def check_anki(self) -> bool:
        """Check if Anki is running."""
        try:
            response = requests.get("http://localhost:8765", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def start_session(self) -> dict:
        """Pre-flight checks before session."""
        errors = []
        
        # 1. Check Anki (required)
        if not self.check_anki():
            errors.append("Anki is not running. Please start Anki and try again.")
        
        # 2. Check database
        if not self.check_database():
            errors.append("Database locked. Close other instances.")
        
        # 3. Check network (optional)
        if not self.check_network():
            errors.append("Network unavailable. Some features disabled.")
        
        if errors:
            return {"success": False, "errors": errors}
        
        return {"success": True}
```

### Error Scenarios

| Scenario | Handling |
|----------|----------|
| Anki not running | **Block session, notify user** |
| API down | **Fallback to cached stories** |
| Database locked | **Error message, exit** |
| Network unavailable | **Offline mode (limited)** |
| Invalid API key | **Clear error message** |

### Cached Stories + Performance Tracking

**Problem:** Cached stories have old vocabulary violations.

**Solution:** Track story source, use differently:

```python
story = get_cached_story()
story["source"] = "cached"

# Performance tracking still works
log_comprehension_session(
    story_id=story["id"],
    score=score,           # ✅ Valid
    questions_answered=n,  # ✅ Valid
    source="cached"        # Track source
)

# But don't use for violation detection
if story["source"] == "generated":
    detect_violations(story)  # Add new words to deck
else:
    pass  # Skip violation detection for cached stories
```

**Tracking validity:**

| Tracking | Cached Story | Generated Story |
|----------|--------------|------------------|
| Comprehension score | ✅ Valid | ✅ Valid |
| Violation detection | ❌ Skip | ✅ Use |
| Vocabulary enrichment | ❌ Skip | ✅ Use |

### Offline Mode

**Strategy:** Pre-cache questions, skip LLM tasks when offline.

| Component | Offline Strategy |
|-----------|------------------|
| Grammar (Tier 1) | Already offline ✅ |
| Grammar (Tier 2-3) | Pre-cache questions |
| Reading comprehension | Pre-cache 5-10 questions per story |
| Writing prompts | Pre-cache generic prompts |
| Story generation | Use cached stories |
| Writing evaluation | Skip, evaluate later when online |

**Progression impact:**

```python
def calculate_progress(days: int) -> dict:
    """Calculate progress, accounting for skipped sessions."""
    sessions = get_sessions(days)
    
    return {
        "completed_sessions": len([s for s in sessions if not s.skipped]),
        "skipped_sessions": len([s for s in sessions if s.skipped]),
        "mastery_based_on": "completed sessions only",
    }
```

**Rule:** Skipped tests don't count toward mastery.

### Error Reporting

- CLI error output with verbose mode
- Exit code 1 on failure
- Verbose flag shows stack trace and details

---

## Open Questions (All Resolved)

| # | Question | Resolution |
|---|----------|------------|
| 1 | Session timeout | **Manual** - user runs `learn-jp end` when done |
| 2 | Multiple decks | **Separate decks** per level |
| 3 | Violation history | **Yes** - track violation count per session for trend visualization |
| 4 | Story generation trigger | **Phased** - no story tests until ready, then mandatory |
| 5 | AnkiConnect dependency | **Block session** if Anki not running |
| 6 | Question count | **Adaptive with max** - 3-5 questions, configurable max enforced deterministically |
| 7 | Tier 1 grammar scope | **Research during implementation** - separate session with agent |

### Detailed Resolutions

#### 1. Session Timeout
- User runs `learn-jp end` when done
- No auto-detection
- Simple, no false triggers

#### 3. Violation History
```sql
-- Track violations per session
CREATE TABLE session_violations (
    session_id INTEGER,
    violation_count INTEGER,
    violation_rate REAL,  -- violations / total_words
    date TEXT
);

-- Query for trend
SELECT date, violation_count, violation_rate
FROM session_violations
ORDER BY date;
```

#### 4. Story Generation Trigger
```
Phase 1 (0-150 words): NO story generation
├── Focus on vocabulary + grammar drills
├── Deck is small, manageable
└── System blocks story generation

Phase 2 (150+ words): Story generation MANDATORY
├── Must complete reading comprehension each session
├── Violations feed back to vocabulary
└── System enforces this rule
```

#### 6. Question Count (Adaptive with Max)

```python
# Configurable max (deterministic enforcement)
MAX_QUESTIONS = get_config("max_comprehension_questions")  # default: 5

def get_question_count(story_length: int, vocab_size: int) -> int:
    """Determine question count, enforced deterministically."""
    
    # Calculate ideal count based on story
    if story_length < 200:
        ideal = 3
    elif story_length < 500:
        ideal = 4
    else:
        ideal = 5
    
    # Apply configurable max (hard limit)
    return min(ideal, MAX_QUESTIONS)

# Before LLM call, enforce limit
question_count = get_question_count(story.length, vocab_size)
prompt = f"Generate exactly {question_count} questions..."
```

**Enforcement:** Deterministic check BEFORE LLM call, not after.

#### 7. Tier 1 Grammar Scope
- Research task during implementation
- Use separate agent session to define
- Start with most common N5 patterns (~50-80)
- Reference: Genki textbook, JLPT study guides

---

## Reference

- [ARCHITECTURE.md](ARCHITECTURE.md) - Original system design
- [VIOLATION_BASED_LEARNING.md](VIOLATION_BASED_LEARNING.md) - Violation detection concept
- [PHASE-2.md](PHASE-2.md) - Content pipeline tasks
