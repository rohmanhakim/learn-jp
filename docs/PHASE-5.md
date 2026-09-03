# Phase 5: Grammar System

## Goal

Implement three-tier grammar system with adaptive question format.

**Reference:** See WORKFLOW-FINDINGS.md - Grammar Study section.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    TIER 1: CORE GRAMMAR                 │
│                    (Deterministic, zero tokens)         │
├─────────────────────────────────────────────────────────┤
│  • Pre-defined drills for essential patterns            │
│  • ~200 most essential patterns (N5-N4)                 │
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
└─────────────────────────────────────────────────────────┘
```

---

## Tasks

### Task 1: Core Grammar Database (Tier 1)

**File:** `data/grammar/n5_grammar.json`

```json
[
  {
    "pattern": "～ます",
    "structure": "Verb stem + ます",
    "meaning": "Polite present/future",
    "level": "n5",
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
```

### Task 2: Grammar Drill Engine

**File:** `learn_jp/grammar.py`

```python
"""Grammar drill system with three-tier architecture."""

import sqlite3
import json
import random
from pathlib import Path
from typing import Dict, List, Optional


class GrammarEngine:
    """Manages grammar drills."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.tier1_data = self._load_tier1()
    
    def _load_tier1(self) -> Dict:
        """Load Tier 1 grammar data."""
        data_file = Path(__file__).parent.parent / "data" / "grammar" / "n5_grammar.json"
        if data_file.exists():
            with open(data_file, 'r') as f:
                return json.load(f)
        return []
    
    def get_drill(self, pattern: str = None, mastery: float = 0) -> Dict:
        """Get a grammar drill, adapting to mastery level."""
        # 1. Try Tier 1 (pre-defined)
        if pattern:
            tier1 = self._get_tier1_drill(pattern)
            if tier1:
                return tier1
        
        # 2. Try Tier 2 (cached)
        tier2 = self._get_tier2_drill(pattern, mastery)
        if tier2:
            return tier2
        
        # 3. Fall back to Tier 3 (dynamic LLM)
        return self._get_tier3_drill(pattern, mastery)
    
    def _get_tier1_drill(self, pattern: str) -> Optional[Dict]:
        """Get drill from Tier 1 (pre-defined)."""
        for item in self.tier1_data:
            if item["pattern"] == pattern:
                # Return random drill
                drill = random.choice(item["drills"])
                drill["tier"] = 1
                drill["pattern"] = pattern
                return drill
        return None
    
    def _get_tier2_drill(self, pattern: str, mastery: float) -> Optional[Dict]:
        """Get drill from Tier 2 (cached)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT * FROM grammar_question_cache
            WHERE pattern = ?
              AND difficulty BETWEEN ? - 0.2 AND ? + 0.2
            ORDER BY effectiveness DESC, times_used ASC
            LIMIT 1
        """, (pattern, mastery, mastery))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # Generate variation
            return self._generate_variation(row)
        return None
    
    def _get_tier3_drill(self, pattern: str, mastery: float) -> Dict:
        """Generate drill with LLM (Tier 3)."""
        # TODO: Implement LLM generation
        # For now, return placeholder
        return {
            "tier": 3,
            "type": "multiple_choice",
            "question": f"What is the {pattern} form?",
            "options": ["Option A", "Option B", "Option C"],
            "answer": "A",
            "needs_llm": True
        }
    
    def _generate_variation(self, cached: Dict) -> Dict:
        """Generate variation of cached question."""
        # TODO: Implement variation generation
        return {
            "tier": 2,
            "type": cached["question_type"],
            "question": cached["base_question"],
            "options": json.loads(cached["options"]) if cached["options"] else [],
            "answer": cached["correct_answer"],
            "pattern": cached["pattern"]
        }
    
    def check_answer(self, pattern: str, user_answer: str, expected: str) -> Dict:
        """Check grammar answer."""
        # Normalize
        user_answer = user_answer.strip()
        expected = expected.strip()
        
        # Exact match
        if user_answer == expected:
            return {"correct": True, "confidence": 1.0}
        
        # Partial match (e.g., て-form check)
        if pattern and "て" in pattern:
            if user_answer.endswith(("て", "で")):
                return {"correct": True, "confidence": 0.8}
        
        return {"correct": False, "confidence": 0}
    
    def get_question_format(self, mastery: float) -> Dict:
        """Determine question format based on mastery."""
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

---

## Tier 1 Grammar Patterns

### N5 Essential Patterns (~50-80)

| Pattern | Meaning | Structure |
|---------|---------|-----------|
| ～ます | Polite present | Verb stem + ます |
| ～ない | Negative | Verb stem + ない |
| ～て | Te-form | Varies by verb type |
| ～た | Past tense | Varies by verb type |
| い adj + です | Polite adjective | い adj + です |
| な adj + です | Polite adjective | な adj + です |
| ～があります | Existence | Noun + があります |
| ～がいます | Animate existence | Noun + がいます |
| ～から | From/because | Time/Place + から |
| ～まで | Until | Time/Place + まで |
| ～たい | Want to | Verb stem + たい |
| ～てもいい | Permission | て-form + もいい |
| ～なければならない | Obligation | なければならない |
| ... | ... | ... |

**Full list:** Research during implementation using Genki textbook, JLPT study guides.

---

## Adaptive Question Format

```python
def get_question_format(mastery: float) -> Dict:
    """Adapt based on mastery level."""
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

---

## Testing

```bash
# Test Tier 1 drill
$ learn-jp grammar --pattern ～ます
Pattern: ～ます
Q: What is the polite form of 食べる?
> 食べます
✓ Correct!

# Test adaptive format
$ learn-jp grammar
[Auto-selects pattern based on mastery]
```

---

## Checklist

- [ ] Create grammar data files (Tier 1)
- [ ] Implement GrammarEngine class
- [ ] Implement Tier 1 drill loading
- [ ] Implement Tier 2 caching
- [ ] Implement Tier 3 LLM generation
- [ ] Implement adaptive question format
- [ ] Add grammar_progress table
- [ ] Add grammar_question_cache table
- [ ] Add grammar_sessions table
- [ ] Test grammar drills
- [ ] Test answer checking
- [ ] Test adaptive format
- [ ] Research full Tier 1 pattern list

## Tasks

### Task 1: Create AGENTS.md

**File:** `AGENTS.md`

```markdown
This IS a personal Japanese learning workflow. 

To use this repo, open it using your AI agentic coding tool of your choice (Claude Code, Codex, OpenCode, Cline, Cursor, etc.) then use the AI to assist you in your learning.

The user then replaces this file with AGENTS.template.md so the AI uses that file for the master instruction.

For more information on how the AI would assist the user, read AGENTS.template.md
```

---

### Task 2: Create Full AGENTS.template.md

**File:** `AGENTS.template.md`

(This is the comprehensive version - see Phase 3 for initial version. This phase expands it with all rules.)

```markdown
You're my Japanese language coach and mentor. This repo is my archive of my learning progress. Each session I may consult with you about studying, in which you'll guide me so that I can improve my Japanese skills.

The main goal for each session is to help me learn Japanese effectively. I want to understand the language, not just memorize.

My main goal is to pass JLPT N5 initially, then progress through N4, N3, N2, and N1.

# Mode Discipline

The conversation alternates between two modes: **plan** (read-only analysis) and **act** (execute changes). Respect the current mode strictly.

## Plan Mode Rules
- **Read-only only.** No DB writes, no file edits, no state-changing commands.
- You MAY: read files, run `grep`/`find`/`sqlite3` SELECT queries, search codebase.
- **Present your analysis and proposed changes** as a clear plan.
- End your response with the full plan and **wait for the user to switch to act mode** before executing.

## Act Mode Rules
- Execute the prepared plan: run the SQL, make the file edits.
- You may still review/verify after executing.

## Pre-flight Check
Before every write operation, mentally confirm: "am I in act mode?" If the answer is no or uncertain, **stop and present the plan instead**.

# Progress Tracking

Progress is tracked in a SQLite database at `progress/progress.db`. The schema is defined in `progress/schema.sql`.

## Database Schema

### vocabulary table
One row per unique vocabulary item.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment primary key |
| item_id | TEXT | Unique identifier, e.g., "n5-v-001" |
| content | TEXT | The word (kanji): 食べる |
| reading | TEXT | Hiragana: たべる |
| meaning | TEXT | English: to eat |
| level | TEXT | JLPT level: "n5", "n4", etc. |
| part_of_speech | TEXT | "verb", "noun", etc. |
| source | TEXT | "jlpt", "jisho", etc. |

### sessions table
One row per study session.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment primary key |
| date | TEXT | YYYY-MM-DD |
| type | TEXT | "anki", "reading", "writing" |
| items_studied | INTEGER | Number of items studied |
| correct | INTEGER | Number correct |
| accuracy | REAL | Accuracy percentage |
| time_spent_seconds | INTEGER | Time in seconds |

### item_reviews table
Per-item performance in a session.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment primary key |
| session_id | INTEGER | FK → sessions.id |
| item_id | TEXT | FK → vocabulary.item_id |
| item_type | TEXT | "vocabulary", "kanji", "grammar" |
| severity | INTEGER | 0=instant, 1=slow, 2=partial, 3=miss |
| response_time_ms | INTEGER | Response time in ms |

### mastery table
Tracks mastery status for each item.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment primary key |
| item_id | TEXT | FK → vocabulary.item_id |
| status | TEXT | "new", "learning", "review", "mastered" |
| streak | INTEGER | Consecutive sessions with severity ≤ 1 |
| last_review_date | TEXT | Last review date |

## Severity Scale

| Severity | Meaning | Response Time |
|----------|---------|---------------|
| 0 | **Instant recall** - knew it immediately | < 2 seconds |
| 1 | **Slow recall** - knew it but took time | 2-5 seconds |
| 2 | **Partial recall** - forgot reading OR meaning | > 5 seconds or partial |
| 3 | **Complete miss** - didn't know it | N/A |

## Mastery Criteria

To promote an item to "mastered" status, ALL of these must be true:

| Criterion | Requirement |
|-----------|-------------|
| Consecutive sessions with severity ≤ 1 | 5 |
| Time span | ≥ 7 days |
| Total reviews in last 14 days | ≥ 3 |

# Workflow

## Session Start

When user starts a study session:

1. **Check the DB** - See current progress, what needs review
2. **Suggest study plan** - Based on progress and time available
3. **Guide the session** - Help with Anki, reading, writing

## Anki Drill

When user is doing Anki reviews:

1. **Get deck stats** - How many cards due?
2. **Guide through reviews** - User does flashcards in Anki
3. **Log results** - User reports what they got right/wrong

### Logging Anki Session

```sql
-- Log the session
INSERT INTO sessions (date, type, items_studied, correct, accuracy, time_spent_seconds)
VALUES ('YYYY-MM-DD', 'anki', ?, ?, ?, ?);

-- Log individual items
INSERT INTO item_reviews (session_id, item_id, item_type, severity, response_time_ms)
VALUES (?, ?, 'vocabulary', ?, ?);

-- Update mastery
UPDATE mastery SET streak = ?, last_review_date = ?, status = ?
WHERE item_id = ?;
```

## Reading Practice

When user wants reading practice:

1. **Get known vocabulary** - Query DB for mastered/review items
2. **Generate story** - Use story generator with known vocab
3. **Present story** - User reads and answers questions
4. **Check answers** - Verify comprehension
5. **Log results** - Track reading session

### Reading Comprehension Levels

**Beginner (N5):**
- Multiple choice questions in English
- Simple comprehension

**Elementary (N5 with 50+ words):**
- Multiple choice with more options
- Vocabulary in context

**Intermediate (N4-N3):**
- Short answer in English
- Fill in the blank

**Advanced (N2-N1):**
- Translation exercises
- Summary and analysis

## Writing Practice

When user wants writing practice:

1. **Select vocabulary** - Choose 3-5 words to practice
2. **Give prompt** - "Write a sentence using these words"
3. **Review writing** - Check grammar, vocabulary usage
4. **Provide feedback** - Corrections and suggestions
5. **Log results** - Track writing session

# Regression Detection

Regression is NOT triggered by a single failure. It requires evidence of sustained decline.

## Triggers

1. **Severity 3 on mastered item** → Immediate regression flag
2. **Two or more sessions with severity ≥ 2 in last 3 days** → Regression flag

## Action on Regression

1. Move item status back to "review"
2. Schedule for focused review
3. Suggest related vocabulary review

# Study Suggestions

## Daily Suggestions

Based on progress, suggest:
1. **Due items** - Vocabulary needing review
2. **At-risk items** - Mastered items at risk of regression
3. **New vocabulary** - If appropriate to add more
4. **Reading practice** - If enough vocabulary known
5. **Weak areas** - Focus on high-failure items

## Weekly Review

On weekly basis:
1. **Progress summary** - Items mastered this week
2. **Weak areas** - Items with high failure rates
3. **Schedule adjustment** - Modify study plan based on progress

# When You're About to Update Progress Files

1. **Check the DB** - See current status
2. **Calculate changes** - What improved, what regressed
3. **Update mastery** - Update streak, status
4. **Update overview** - Update progress/overview.md
5. **Suggest next steps** - What to focus on next

# Rules for the Mentor

## When Reviewing

- Before presenting vocabulary, always check pronunciation
- If unsure about meaning, look it up via Jisho
- Never present unverified information
- Acknowledge mistakes and correct them

## When Suggesting Study

- Balance between review and new material
- Consider user's available time
- Prioritize weak areas
- Mix vocabulary types (verbs, nouns, adjectives)

## When Providing Feedback

- Be encouraging but honest
- Explain why something is wrong
- Provide examples
- Suggest alternatives

# Miscellaneous

## Query Examples

```sql
-- Get vocabulary at a specific level
SELECT * FROM vocabulary WHERE level = 'n5';

-- Get items needing review
SELECT v.*, m.status, m.streak
FROM vocabulary v
LEFT JOIN mastery m ON v.item_id = m.item_id
WHERE m.status != 'mastered' OR m.status IS NULL;

-- Get mastery statistics
SELECT status, COUNT(*) FROM mastery GROUP BY status;

-- Get study history
SELECT date, type, accuracy FROM sessions ORDER BY date DESC LIMIT 10;
```
```

---

## Testing

### Test AGENTS.md Loading
```bash
# Verify AGENTS.md exists and is readable
cat AGENTS.md
```

### Test Queries
```bash
# Test sample queries from AGENTS.md
sqlite3 progress/progress.db "SELECT status, COUNT(*) FROM mastery GROUP BY status;"
```

---

## Checklist

- [ ] Create AGENTS.md (simplified)
- [ ] Create AGENTS.template.md (comprehensive)
- [ ] Include all database queries
- [ ] Include severity scale
- [ ] Include mastery criteria
- [ ] Include workflow rules
- [ ] Include regression detection
- [ ] Test sample queries
