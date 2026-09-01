# Phase 3: Study Workflow

## Goal

Integrate Anki, story generator, and agent into a cohesive study workflow.

# Phase 3: Study Workflow

## Goal

Integrate Anki, story generator, and agent into a cohesive study workflow with violation-based vocabulary enrichment.

## Overview

This phase implements:
1. Study session management
2. **Violation-based learning** (hybrid curriculum)
3. Reading comprehension exercises
4. Session logging and statistics

### Hybrid Curriculum Approach

- **JLPT curriculum** is the foundation (N5 → N4 → N3)
- **Violations enrich** the curriculum (context-driven vocabulary)
- **Algorithm grades** violations (deterministic, not agent judgment)
- **Agent executes** decisions (follow algorithm output)

---

## Tasks

### Task 1: Create Violation Grading Algorithm

**File:** `lib/violation_grader.py`

```python
"""Grade vocabulary violations from story generation."""

import sqlite3
from typing import Literal


# JLPT level order for distance calculation
JLPT_LEVELS = ["n5", "n4", "n3", "n2", "n1"]


def get_jlpt_level(word: str, db_path: str) -> str:
    """
    Get JLPT level of a word.
    
    Checks vocabulary table first, then returns None if unknown.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT level FROM vocabulary WHERE content = ?",
        (word,)
    )
    row = cursor.fetchone()
    conn.close()
    
    return row[0] if row else None


def calculate_level_distance(current_level: str, word_level: str) -> int:
    """
    Calculate distance between JLPT levels.
    
    Returns:
        Positive number = word is ahead of current level
        Zero or negative = word is at or below current level
    """
    if current_level not in JLPT_LEVELS:
        current_idx = 0
    else:
        current_idx = JLPT_LEVELS.index(current_level)
    
    if word_level not in JLPT_LEVELS:
        word_idx = 2  # Default to N3 if unknown
    else:
        word_idx = JLPT_LEVELS.index(word_level)
    
    return word_idx - current_idx


def grade_violation(
    violation: dict,
    current_level: str,
    db_path: str
) -> Literal["introduce_now", "queue", "skip"]:
    """
    Grade a vocabulary violation.
    
    Args:
        violation: Dict with 'surface', 'reading', 'pos' keys
        current_level: User's current JLPT level (e.g., 'n5')
        db_path: Path to progress database
    
    Returns:
        "introduce_now" - Add to vocabulary immediately
        "queue" - Add to priority queue for later
        "skip" - Too advanced, skip for now
    """
    word = violation["surface"]
    
    # 1. Get JLPT level of violation word
    word_level = get_jlpt_level(word, db_path)
    
    # 2. Calculate level distance
    distance = calculate_level_distance(current_level, word_level)
    
    # 3. Grade by distance
    if distance <= 1:
        # Same level or one above - should learn now
        return "introduce_now"
    elif distance == 2:
        # Two levels above - queue for later
        return "queue"
    else:
        # Three+ levels above - too advanced
        return "skip"


def process_violations(
    violations: list,
    current_level: str,
    db_path: str
) -> dict:
    """
    Process a list of violations and return graded results.
    
    Returns:
        Dict with 'introduce_now', 'queue', 'skip' lists
    """
    result = {
        "introduce_now": [],
        "queue": [],
        "skip": []
    }
    
    for v in violations:
        grade = grade_violation(v, current_level, db_path)
        result[grade].append(v)
    
    return result
```

---

### Task 2: Create Study Session Manager

**File:** `lib/study_manager.py`

```python
"""Study session management and workflow orchestration."""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional

from .anki_connector import connector
from .story_generator import StoryGenerator


class StudyManager:
    """Manages study sessions and workflow."""
    
    def __init__(self, db_path: str, openrouter_key: str):
        self.db_path = db_path
        self.story_gen = StoryGenerator(openrouter_key)
    
    def get_db(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_due_items(self, level: str = None) -> List[dict]:
        """Get items due for review."""
        db = self.get_db()
        
        query = """
            SELECT v.*, m.status, m.streak, m.last_review_date
            FROM vocabulary v
            LEFT JOIN mastery m ON v.item_id = m.item_id
            WHERE m.status != 'mastered' OR m.status IS NULL
        """
        
        if level:
            query += " AND v.level = ?"
            params = (level,)
        else:
            params = ()
        
        query += " ORDER BY m.last_review_date ASC NULLS FIRST"
        
        cursor = db.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_known_vocabulary(self, level: str = None) -> List[str]:
        """Get vocabulary user has learned (mastered or in review)."""
        db = self.get_db()
        
        query = """
            SELECT v.content
            FROM vocabulary v
            JOIN mastery m ON v.item_id = m.item_id
            WHERE m.status IN ('review', 'mastered')
        """
        
        if level:
            query += " AND v.level = ?"
            params = (level,)
        else:
            params = ()
        
        cursor = db.execute(query, params)
        return [row['content'] for row in cursor.fetchall()]
    
    def start_anki_session(self, level: str) -> dict:
        """Get Anki deck stats for study session."""
        deck_name = f"Japanese::{level.upper()}::Vocab"
        
        stats = connector.deck_stats([deck_name])
        
        return {
            "deck": deck_name,
            "new_cards": stats.get(deck_name, {}).get("new_count", 0),
            "due_cards": stats.get(deck_name, {}).get("review_count", 0),
            "total_cards": stats.get(deck_name, {}).get("total_in_deck", 0)
        }
    
    def generate_story_and_process_violations(self, level: str, theme: str = None) -> dict:
        """
        Generate story and process violations for vocabulary enrichment.
        
        This is the main method for violation-based learning.
        """
        from japanese_story_generator import ConjugationVerifier
        from .violation_grader import process_violations
        
        # Get vocabulary user knows
        known_vocab = self.get_known_vocabulary(level)
        
        if len(known_vocab) < 10:
            return {
                "error": "Not enough vocabulary for story generation",
                "min_required": 10,
                "current": len(known_vocab)
            }
        
        # Use up to 50 words for story generation
        vocab_for_story = known_vocab[:50]
        
        # Generate story (strict mode to identify violations)
        story = self.story_gen.generate(
            vocab_words=vocab_for_story,
            theme=theme,
            strict_vocab=True
        )
        
        # Verify vocabulary usage
        verifier = ConjugationVerifier()
        verification = verifier.verify(story, vocab_for_story)
        violations = verification["violations"]
        
        # Grade violations using algorithm
        graded = process_violations(violations, level, self.db_path)
        
        # Log story to database
        db = self.get_db()
        cursor = db.execute("""
            INSERT INTO stories (date, theme, content, vocab_used, vocab_count, difficulty)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            theme,
            story,
            str(vocab_for_story),
            len(vocab_for_story),
            "strict"
        ))
        db.commit()
        story_id = cursor.lastrowid
        
        return {
            "story_id": story_id,
            "story": story,
            "vocab_used": len(vocab_for_story),
            "violations": violations,
            "graded": graded,
            "introduce_now": graded["introduce_now"],
            "queue": graded["queue"],
            "skip": graded["skip"]
        }
    
    def add_violation_to_vocabulary(self, violation: dict, level: str) -> int:
        """
        Add a violation word to vocabulary table.
        
        Returns: vocabulary id
        """
        db = self.get_db()
        
        # Generate item_id
        cursor = db.execute(
            "SELECT COUNT(*) as cnt FROM vocabulary WHERE level = ?",
            (level,)
        )
        count = cursor.fetchone()['cnt'] + 1
        item_id = f"{level}-v-{count:03d}"
        
        # Insert vocabulary
        cursor = db.execute("""
            INSERT INTO vocabulary (item_id, content, reading, meaning, level, part_of_speech, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            item_id,
            violation["surface"],
            violation.get("reading"),
            violation.get("meaning"),
            level,
            violation.get("pos"),
            "violation"
        ))
        db.commit()
        
        return cursor.lastrowid
    
    def add_violation_to_queue(self, violation: dict, level: str) -> int:
        """
        Add a violation word to priority queue.
        
        Returns: queue entry id
        """
        from .violation_grader import calculate_level_distance, get_jlpt_level
        
        db = self.get_db()
        word = violation["surface"]
        word_level = get_jlpt_level(word, self.db_path)
        distance = calculate_level_distance(level, word_level)
        
        # Priority based on distance
        priority = 1 if distance == 2 else 2
        
        # Insert or update frequency
        cursor = db.execute("""
            INSERT INTO violation_queue (word, reading, meaning, pos, jlpt_level, 
                                        level_distance, priority, frequency, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, DATE('now'), DATE('now'))
            ON CONFLICT(word) DO UPDATE SET 
                frequency = frequency + 1,
                last_seen = DATE('now'),
                priority = MIN(priority, excluded.priority)
        """, (
            word,
            violation.get("reading"),
            violation.get("meaning"),
            violation.get("pos"),
            word_level,
            distance,
            priority
        ))
        db.commit()
        
        return cursor.lastrowid
    
    def promote_queued_words(self, completed_level: str) -> list:
        """
        Promote queued words when user advances a level.
        
        Returns list of promoted words.
        """
        db = self.get_db()
        
        # Get queued words at completed level with priority 1
        cursor = db.execute("""
            SELECT * FROM violation_queue
            WHERE jlpt_level = ?
              AND priority = 1
              AND status = 'queued'
            ORDER BY frequency DESC
        """, (completed_level,))
        
        words = [dict(row) for row in cursor.fetchall()]
        
        # Update status to promoted
        db.execute("""
            UPDATE violation_queue
            SET status = 'promoted', promoted_date = DATE('now')
            WHERE jlpt_level = ?
              AND priority = 1
              AND status = 'queued'
        """, (completed_level,))
        db.commit()
        
        return words
    
    def get_queued_words(self, status: str = 'queued') -> list:
        """Get words from violation queue."""
        db = self.get_db()
        cursor = db.execute("""
            SELECT * FROM violation_queue
            WHERE status = ?
            ORDER BY priority ASC, frequency DESC
        """, (status,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def generate_reading_exercise(self, level: str, theme: str = None) -> dict:
        """Generate a reading exercise using known vocabulary."""
        # Get vocabulary user knows
        known_vocab = self.get_known_vocabulary(level)
        
        if len(known_vocab) < 10:
            return {
                "error": "Not enough vocabulary for reading exercise",
                "min_required": 10,
                "current": len(known_vocab)
            }
        
        # Use up to 50 words for story generation
        vocab_for_story = known_vocab[:50]
        
        # Determine difficulty based on level
        strict_vocab = level in ["n5", "n4"]
        
        # Generate story with questions
        result = self.story_gen.generate_with_questions(
            vocab_words=vocab_for_story,
            level=level,
            theme=theme
        )
        
        # Log to database
        db = self.get_db()
        cursor = db.execute("""
            INSERT INTO stories (date, theme, content, vocab_used, vocab_count, difficulty)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            theme,
            result["story"],
            str(vocab_for_story),
            len(vocab_for_story),
            "strict" if strict_vocab else "flexible"
        ))
        db.commit()
        
        result["story_id"] = cursor.lastrowid
        return result
    
    def log_anki_session(self, level: str, items_studied: int, 
                         correct: int, time_spent: int, notes: str = None):
        """Log an Anki study session."""
        accuracy = (correct / items_studied * 100) if items_studied > 0 else 0
        
        db = self.get_db()
        cursor = db.execute("""
            INSERT INTO sessions (date, type, items_studied, correct, accuracy, 
                                  time_spent_seconds, notes)
            VALUES (?, 'anki', ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            items_studied,
            correct,
            accuracy,
            time_spent,
            notes
        ))
        db.commit()
        
        return cursor.lastrowid
    
    def log_reading_session(self, story_id: int, comprehension_score: float,
                           questions_answered: int, questions_correct: int,
                           time_spent: int, notes: str = None):
        """Log a reading comprehension session."""
        db = self.get_db()
        cursor = db.execute("""
            INSERT INTO reading_sessions (story_id, date, time_spent_seconds,
                                          comprehension_score, questions_answered,
                                          questions_correct, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            story_id,
            datetime.now().strftime("%Y-%m-%d"),
            time_spent,
            comprehension_score,
            questions_answered,
            questions_correct,
            notes
        ))
        db.commit()
        
        return cursor.lastrowid
    
    def get_study_stats(self, days: int = 7) -> dict:
        """Get study statistics for last N days."""
        db = self.get_db()
        
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # Session stats
        sessions = db.execute("""
            SELECT type, COUNT(*) as count, 
                   SUM(items_studied) as total_items,
                   AVG(accuracy) as avg_accuracy
            FROM sessions
            WHERE date >= ?
            GROUP BY type
        """, (start_date,)).fetchall()
        
        # Mastery stats
        mastery = db.execute("""
            SELECT status, COUNT(*) as count
            FROM mastery
            GROUP BY status
        """).fetchall()
        
        return {
            "period_days": days,
            "sessions": {row['type']: dict(row) for row in sessions},
            "mastery": {row['status']: row['count'] for row in mastery}
        }
```

---

### Task 2: Create Reading Comprehension Handler

**File:** `lib/reading_handler.py`

```python
"""Handle reading comprehension exercises."""

from typing import List, Optional


class ReadingHandler:
    """Manages reading comprehension exercises."""
    
    @staticmethod
    def parse_questions(text: str) -> List[dict]:
        """Parse questions from generated text."""
        questions = []
        
        # Simple parsing logic
        lines = text.split("\n")
        current_question = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect question (starts with number)
            if line[0].isdigit() and "." in line[:3]:
                if current_question:
                    questions.append(current_question)
                
                current_question = {
                    "question": line.split(".", 1)[1].strip(),
                    "options": [],
                    "answer": None
                }
            
            # Detect option (A, B, C)
            elif current_question and len(line) > 2 and line[0] in "ABC" and line[1] == ")":
                current_question["options"].append(line[2:].strip())
            
            # Detect answer
            elif "answer:" in line.lower():
                answer = line.split(":", 1)[1].strip()
                if current_question:
                    current_question["answer"] = answer
        
        if current_question:
            questions.append(current_question)
        
        return questions
    
    @staticmethod
    def format_question_for_user(question: dict, index: int) -> str:
        """Format a question for display."""
        output = f"\n{index}. {question['question']}\n"
        
        if question.get('options'):
            for i, option in enumerate(question['options']):
                letter = chr(65 + i)  # A, B, C, ...
                output += f"   {letter}) {option}\n"
        
        return output
    
    @staticmethod
    def check_answer(user_answer: str, correct_answer: str) -> bool:
        """Check if user's answer is correct."""
        # Normalize answers
        user_answer = user_answer.strip().lower()
        correct_answer = correct_answer.strip().lower()
        
        # Handle letter answers (A, B, C)
        if len(user_answer) == 1 and user_answer.isalpha():
            return user_answer == correct_answer
        
        # Handle text answers (case-insensitive)
        return user_answer == correct_answer
```

---

### Task 3: Create AGENTS.md Template

**File:** `AGENTS.template.md`

```markdown
You're my Japanese language coach and mentor. This repo is my archive of my learning progress, including vocabulary, kanji, grammar, reading practice, and writing exercises. Each session I may consult with you about studying, in which you'll guide me so that I can improve my Japanese skills.

The main goal for each session is to help me learn Japanese effectively, not just to give me answers. I want to understand the language, not just memorize.

My main goal is to pass JLPT N5 initially, then progress through N4, N3, N2, and N1.

# Mode Discipline

The conversation alternates between two modes: **plan** (read-only analysis) and **act** (execute changes). Respect the current mode strictly.

## Plan Mode Rules
- **Read-only only.** No DB writes, no file edits, no state-changing commands.
- You MAY: read files, run SELECT queries, search codebase.
- **Present your analysis and proposed changes** as a clear plan.
- End your response with the full plan and **wait for the user to switch to act mode**.

## Act Mode Rules
- Execute the prepared plan: run the SQL, make the file edits.
- You may still review/verify after executing.

# Study Workflow

## Daily Study Session
1. **Check progress** - Query DB for current status
2. **Fetch new items** (if needed) - Add vocabulary/kanji to Anki
3. **Anki drill** - User reviews flashcards in Anki
4. **Reading practice** - Generate story using known vocabulary
5. **Writing practice** - Write sentences based on today's vocabulary
6. **Log session** - Update database with results

## Vocabulary Mastery Model

### Severity Scale
| Severity | Meaning |
|----------|---------|
| 0 | Instant recall (< 2 seconds) |
| 1 | Slow recall (2-5 seconds) |
| 2 | Partial recall (forgot reading OR meaning) |
| 3 | Complete miss |

### Mastery Criteria
An item is mastered when:
1. 5 consecutive sessions with severity ≤ 1
2. Sessions span at least 7 days
3. At least 3 reviews in last 14 days

# Session Logging

After each session, log to the database:

```sql
-- Log vocabulary session
INSERT INTO sessions (date, type, items_studied, correct, accuracy, time_spent_seconds)
VALUES ('YYYY-MM-DD', 'anki', ?, ?, ?, ?);

-- Log individual item performance
INSERT INTO item_reviews (session_id, item_id, item_type, severity, response_time_ms)
VALUES (?, ?, 'vocabulary', ?, ?);
```

# Reading Comprehension

Questions adapt to user's level:

## Beginner (N5)
- Multiple choice in English
- Simple comprehension

## Intermediate (N4-N3)
- Short answer in English
- Vocabulary in context

## Advanced (N2-N1)
- Translation exercises
- Summary and analysis
```

---

## Testing

### Test Study Manager
```bash
python -c "
from lib.study_manager import StudyManager
sm = StudyManager('progress/progress.db', 'your-api-key')
print(sm.get_due_items('n5'))
"
```

### Test Reading Exercise Generation
```bash
python -c "
from lib.study_manager import StudyManager
sm = StudyManager('progress/progress.db', 'your-api-key')
result = sm.generate_reading_exercise('n5')
print(result)
"
```

---

## Checklist

### Violation-Based Learning
- [ ] Create `lib/violation_grader.py` with grading algorithm
- [ ] Add `generate_story_and_process_violations()` to StudyManager
- [ ] Add `add_violation_to_vocabulary()` to StudyManager
- [ ] Add `add_violation_to_queue()` to StudyManager
- [ ] Add `promote_queued_words()` to StudyManager
- [ ] Add `get_queued_words()` to StudyManager

### Core Study Workflow
- [ ] Create StudyManager class
- [ ] Create ReadingHandler class
- [ ] Create AGENTS.template.md
- [ ] Test study session workflow
- [ ] Test reading exercise generation
- [ ] Test session logging
- [ ] Test statistics retrieval

### Integration Tests
- [ ] Test story generation + violation extraction
- [ ] Test violation grading algorithm
- [ ] Test queue promotion on level advance
- [ ] Test end-to-end enrichment workflow
