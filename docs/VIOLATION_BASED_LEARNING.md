# Violation-Based Learning (Hybrid Curriculum)

## Overview

This document describes a hybrid approach for vocabulary acquisition that combines:

1. **JLPT Curriculum** - Systematic learning following N5 → N4 → N3 progression
2. **Violation Enrichment** - Context-driven vocabulary from story generation failures

### Core Idea

Follow the JLPT curriculum as your base, but enrich it with vocabulary that the story generator needs:

1. Learn JLPT vocabulary for your current level
2. Generate stories with your known vocabulary
3. Identify violations (words the generator needed but weren't in your vocabulary)
4. Grade violations - if they're at your current level, add them to your deck
5. Continue JLPT curriculum + enriched vocabulary
6. When violations drop to near-zero, begin reading comprehension tests

### Why This Works

- **Structured foundation**: JLPT provides proven progression and comprehensive coverage
- **Context enrichment**: Violations add words you'll actually need for reading
- **Balanced approach**: Structure + relevance
- **Self-validating**: Decreasing violations indicate growing comprehension
- **Motivating**: Clear progress metric (decreasing violations)

---

## System Flow

```
┌─────────────────────────────────────────────────────────────┐
│              HYBRID LEARNING: CURRICULUM + ENRICHMENT        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  DAILY FLOW                                                 │
│                                                             │
│  1. Study JLPT vocabulary for current level                 │
│     └─ Standard flashcard review (Anki)                     │
│                                                             │
│  2. Generate story with known vocabulary                    │
│     └─ StoryGenerator.generate(vocab, strict=True)          │
│                                                             │
│  3. Verify vocabulary usage                                 │
│     └─ ConjugationVerifier.verify(story, vocab)             │
│                                                             │
│  4. Extract violations (words not in vocabulary)            │
│     └─ violations = result["violations"]                    │
│                                                             │
│  5. Grade violations (heuristic algorithm)                  │
│     ├─ At current level? → Add to deck (enrichment)         │
│     ├─ One level above? → Priority queue                    │
│     └─ Too advanced? → Skip                                 │
│                                                             │
│  6. Add enrichment words to Anki                            │
│     └─ These supplement your JLPT curriculum                │
│                                                             │
│  7. Repeat tomorrow                                         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  TRANSITION TO READING TESTS                                │
│                                                             │
│  Trigger: Violations < threshold (e.g., < 5% or 0)          │
│                                                             │
│  1. Generate story with comprehension questions             │
│     └─ StoryGenerator.generate_with_questions(vocab)        │
│                                                             │
│  2. User reads story and answers questions                  │
│                                                             │
│  3. Continue JLPT curriculum + enrichment in parallel       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Violation Grading Heuristic

### Input

```python
{
    "surface": "痛い",           # Actual word in story
    "suspected_base": "痛い",    # Dictionary form
    "pos": "形容詞",             # Part of speech
    "reading": "いたい"          # Reading in hiragana
}
```

### Grading Algorithm

```python
def grade_violation(violation: dict, current_level: str, known_grammar: list) -> str:
    """
    Grade a vocabulary violation.
    
    Returns:
        "introduce_now" - Add to vocabulary immediately
        "queue" - Add to priority queue for later
        "skip" - Too advanced, skip for now
    """
    word = violation["surface"]
    pos = violation["pos"]
    
    # 1. Get JLPT level of violation word
    word_level = get_jlpt_level(word)  # From Jisho or pre-fetched data
    
    # 2. Calculate level distance
    level_order = ["n5", "n4", "n3", "n2", "n1"]
    current_idx = level_order.index(current_level) if current_level in level_order else 0
    word_idx = level_order.index(word_level) if word_level in level_order else 2
    distance = word_idx - current_idx
    
    # 3. Check if conjugated form of known word
    if is_conjugated_form(violation, known_vocab):
        return "introduce_now"  # User already knows base form
    
    # 4. Grade by level distance
    if distance <= 0:
        # Same level or below - should know this
        return "introduce_now"
    elif distance == 1:
        # One level above - good candidate
        return "introduce_now"
    elif distance == 2:
        # Two levels above - queue for later
        return "queue"
    else:
        # Three+ levels above - too advanced
        return "skip"
    
    # 5. Optional: Grammar prerequisite check
    if requires_grammar(violation, known_grammar):
        return "queue"  # Wait until grammar is learned
```

### Level Distance Thresholds

| Distance | Action | Rationale |
|----------|--------|-----------|
| ≤ 0 | introduce_now | Should already know this |
| 1 | introduce_now | Natural next step |
| 2 | queue | Hold for later |
| ≥ 3 | skip | Too advanced |

### Optional: Grammar Prerequisites

Some vocabulary requires grammar knowledge:

| Vocabulary | Grammar Needed |
|------------|----------------|
| て-form verbs | て-form pattern |
| ない-form verbs | ない-form pattern |
| Adjective + です | な/い adjective rules |
| Compound verbs | Verb conjugation basics |

---

## Cold Start Thresholds

### Minimum Vocabulary for Story Generation

Based on experiments with `japanese-story-generator`:

| Vocabulary Size | Story Quality | Violations | Recommendation |
|-----------------|---------------|------------|----------------|
| < 50 words | Poor/incoherent | Very high | No stories yet |
| 50-100 words | Basic sentences | High (~20-30%) | Start violation learning |
| 100-200 words | Simple stories | Medium (~15-20%) | Continue building |
| 200-500 words | Coherent stories | Low (~10-15%) | Approaching readiness |
| 500+ words | Good stories | Very low (<10%) | Consider reading tests |

### Recommended Start Point

**Start violation-based learning at ~100 words**

Below 100 words, stories are too incoherent to generate meaningful violations.

### Transition to Reading Tests

**Begin reading comprehension when:**
- Violations < 5% of story words
- OR violations are only from N2/N1 levels (if user is at N4)
- OR after reaching ~500 words

---

## Implementation Plan

### Phase 1: Foundation (learn-jp)

1. **Database schema update**
   - Add `violations` table to track seen violations
   - Add `violation_queue` table for priority queue
   - Track both JLPT curriculum progress AND enrichment words

2. **Violation tracking**
   - Log each violation with metadata
   - Track frequency (how often a word appears as violation)
   - Track grade (introduce_now, queue, skip)
   - Distinguish between curriculum words and enrichment words

3. **Heuristic engine**
   - Implement `grade_violation()` function
   - Integrate with Jisho for JLPT level lookup
   - Handle grammar prerequisites
   - Only enrich with words at current level or one level above

### Phase 2: Integration

1. **Study session flow**
   ```
   User: "I want to study"
   → Check current vocabulary size
   → If < threshold: Generate story, extract violations
   → Grade violations
   → Present new words to learn
   → Add to Anki
   ```

2. **Progress tracking**
   - Track violation reduction over time
   - Show progress metric: "Violations: 15% → 8% → 3%"

3. **Transition detection**
   - Monitor when to switch to reading tests
   - Auto-suggest transition when ready

---

## Data Structures

### Violation Record

```sql
CREATE TABLE violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL,
    reading TEXT,
    pos TEXT,
    jlpt_level TEXT,
    grade TEXT,  -- 'introduce_now', 'queue', 'skip'
    first_seen DATE,
    last_seen DATE,
    frequency INTEGER DEFAULT 1,
    introduced BOOLEAN DEFAULT FALSE,
    introduced_date DATE
);
```

### Priority Queue

```sql
CREATE TABLE violation_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL,
    priority INTEGER,  -- Lower = higher priority
    added_date DATE,
    reason TEXT,  -- Why it was queued
    UNIQUE(word)
);
```

---

## Example Session

### Current State
- JLPT Progress: Learning N5 vocabulary (100/200 words completed)
- Enrichment: 50 additional words from violations
- Total vocabulary: 150 words
- Grammar: Basic particles, ます-form, て-form

### Session Flow

1. **Morning: JLPT curriculum**
   - Review N5 flashcards in Anki
   - Learn 5-10 new JLPT words

2. **Afternoon: Story generation + enrichment**
   ```python
   # Generate story with all known vocabulary
   story = generator.generate(vocab_150_words, strict=True)
   # → "寒い日に、彼は薬局で薬を買いました。"
   ```

3. **Verify vocabulary**
   ```python
   result = verifier.verify(story, vocab_150_words)
   # violations: [{"surface": "日", "pos": "名詞", "reading": "ひ"}]
   ```

4. **Grade violation**
   ```python
   grade = grade_violation(
       {"surface": "日", "reading": "ひ"},
       current_level="n5"
   )
   # → "introduce_now" (N5 word, should know)
   ```

5. **Add enrichment word to vocabulary**
   - Add "日" to Anki deck (as enrichment, not curriculum)
   - Update database
   - This word supplements your JLPT studies

6. **Repeat**
   - Next story uses "日" → no longer a violation
   - Continue JLPT curriculum + enrichment
   - Eventually violations drop to < 5%

---

## Metrics & Monitoring

### Key Metrics

1. **Violation Rate** = violations / total_words_in_story
2. **Introduction Rate** = words_introduced / total_violations
3. **Level Distribution** = histogram of violation JLPT levels
4. **Time to Zero** = sessions until violations < threshold

### Progress Visualization

```
Session 1: ████████████████████ 20% violations
Session 2: ██████████████ 14% violations
Session 3: ██████████ 10% violations
Session 4: █████ 5% violations
Session 5: █ 2% violations → Ready for reading tests!
```

---

## Open Questions

1. **Optimal threshold for transition**: Is 5% the right number? Should we use absolute count (e.g., < 3 violations)?

2. **Grammar integration**: How to deterministically check grammar prerequisites?

3. **Frequency weighting**: Should high-frequency violations be prioritized even if level distance is 2?

4. **Compound word handling**: Should compound words be split for grading?

5. **Session pacing**: How many new words per session? Fixed number or adaptive?

---

## References

- [japanese-story-generator](/home/arif/Projects/japanese-story-generator) - Story generation package
- [CONJUGATION_HANDLING_GUIDE.md](/home/arif/Projects/japanese-story-generator/docs/CONJUGATION_HANDLING_GUIDE.md) - Verifier documentation
- [DATABASE.md](DATABASE.md) - Database schema
- [CONTENT-PIPELINE.md](CONTENT-PIPELINE.md) - Vocabulary fetching
