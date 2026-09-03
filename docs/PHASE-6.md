# Phase 6: Reading Comprehension & Writing

## Goal

Implement reading comprehension and writing practice with adaptive question design.

**Reference:** See WORKFLOW-FINDINGS.md for full design.

---

## Reading Comprehension

### Adaptive Question Design

| Level | Vocabulary | Language | Types | Production |
|-------|-----------|----------|-------|------------|
| N5 early | < 100 | English | Multiple choice | None |
| N5 late | 100-200 | English | MC + short answer | Minimal |
| N4 | 200-500 | Mixed | MC + short answer + fill blank | Simple |
| N3 | 500-1000 | Japanese | Short answer + production | Moderate |
| N2-N1 | 1000+ | Japanese | Open-ended + analysis | Extended |

### Question Count (Adaptive with Max)

```python
MAX_QUESTIONS = get_config("max_comprehension_questions")  # default: 5

def get_question_count(story_length: int, vocab_size: int) -> int:
    """Determine question count, enforced deterministically."""
    if story_length < 200:
        ideal = 3
    elif story_length < 500:
        ideal = 4
    else:
        ideal = 5
    
    return min(ideal, MAX_QUESTIONS)  # Hard limit
```

### Tasks

#### Task 1: Reading Comprehension Engine

**File:** `learn_jp/reading.py`

```python
"""Reading comprehension system."""

import sqlite3
from typing import Dict, List


class ReadingComprehension:
    """Manages reading comprehension exercises."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_question_config(self, vocab_size: int, level: str) -> Dict:
        """Determine question format based on vocabulary size."""
        if vocab_size < 100:
            return {
                "language": "english",
                "types": ["multiple_choice"],
                "count": 3,
                "production": False
            }
        elif vocab_size < 200:
            return {
                "language": "english",
                "types": ["multiple_choice", "short_answer"],
                "count": 4,
                "production": "minimal"
            }
        elif vocab_size < 500:
            return {
                "language": "mixed",
                "types": ["multiple_choice", "short_answer", "fill_blank"],
                "count": 5,
                "production": "simple"
            }
        elif vocab_size < 1000:
            return {
                "language": "japanese",
                "types": ["short_answer", "production"],
                "count": 5,
                "production": "moderate"
            }
        else:
            return {
                "language": "japanese",
                "types": ["open_ended", "production", "analysis"],
                "count": 5,
                "production": "extended"
            }
    
    def log_session(self, story_id: int, score: float, 
                   questions_total: int, questions_correct: int,
                   time_spent: int, source: str = "generated"):
        """Log reading comprehension session."""
        conn = sqlite3.connect(self.db_path)
        
        conn.execute("""
            INSERT INTO reading_sessions 
            (story_id, date, time_spent_seconds, comprehension_score,
             questions_answered, questions_correct, notes)
            VALUES (?, DATE('now'), ?, ?, ?, ?, ?)
        """, (story_id, time_spent, score, questions_total, 
               questions_correct, f"source:{source}"))
        
        conn.commit()
        conn.close()
    
    def check_answer(self, user_answer: str, correct_answer: str, 
                    question_type: str) -> bool:
        """Check if answer is correct."""
        user_answer = user_answer.strip().lower()
        correct_answer = correct_answer.strip().lower()
        
        if question_type == "multiple_choice":
            return user_answer == correct_answer
        elif question_type == "short_answer":
            return user_answer == correct_answer
        else:
            # For open-ended, use LLM evaluation
            return None  # Needs LLM
```

#### Task 2: Story + Questions Integration

**File:** `learn_jp/story_session.py`

```python
"""Story generation and comprehension session."""

from japanese_story_generator import StoryGenerator, ConjugationVerifier
from .reading import ReadingComprehension
from .violation_grader import process_violations


class StorySession:
    """Manages story generation and comprehension."""
    
    def __init__(self, db_path: str, api_key: str):
        self.db_path = db_path
        self.generator = StoryGenerator(api_key)
        self.verifier = ConjugationVerifier()
        self.reader = ReadingComprehension(db_path)
    
    def run_session(self, vocab_words: List[str], level: str,
                   theme: str = None, max_questions: int = 5) -> Dict:
        """Run full story + comprehension session."""
        # 1. Generate story
        story = self.generator.generate(
            vocab_words, 
            theme=theme,
            strict_vocab=True
        )
        
        # 2. Verify vocabulary (find violations)
        verification = self.verifier.verify(story, vocab_words)
        violations = verification["violations"]
        
        # 3. Get question config
        config = self.reader.get_question_config(len(vocab_words), level)
        question_count = min(config["count"], max_questions)  # Enforce max
        
        # 4. Generate questions (via LLM)
        questions = self._generate_questions(
            story, level, config, question_count
        )
        
        # 5. Present to user and collect answers
        score = self._run_quiz(questions)
        
        # 6. Log session
        self.reader.log_session(
            story_id=None,  # Would be saved story ID
            score=score,
            questions_total=len(questions),
            questions_correct=score * len(questions),
            time_spent=0,  # Would be actual time
            source="generated"
        )
        
        return {
            "story": story,
            "violations": violations,
            "score": score,
            "questions": questions
        }
    
    def _generate_questions(self, story: str, level: str,
                          config: Dict, count: int) -> List[Dict]:
        """Generate comprehension questions."""
        # TODO: Implement LLM question generation
        return []
    
    def _run_quiz(self, questions: List[Dict]) -> float:
        """Run quiz and return score."""
        # TODO: Implement interactive quiz
        return 0.0
```

---

## Writing Practice

### Progressive Writing Types

| Level | Writing Type | Example |
|-------|-------------|---------|
| N5 early | Guided construction (word bank) | "Make sentence: 食べる + 今日 + ごはん" |
| N5 late | Simple translation | "I eat sushi" → ? |
| N4 | Translation with grammar | "I ate sushi yesterday" → ? |
| N3+ | Free writing prompts | "Write about your weekend" |

### Tasks

#### Task 1: Writing Practice Engine

**File:** `learn_jp/writing.py`

```python
"""Writing practice system."""

import sqlite3
from typing import Dict


class WritingPractice:
    """Manages writing exercises."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_writing_prompt(self, vocab_size: int, 
                          grammar_mastery: float) -> Dict:
        """Get writing prompt based on level."""
        if vocab_size < 100:
            return {
                "type": "construction",
                "words": ["食べる", "今日", "ごはん"],
                "prompt": "Make a sentence using these words"
            }
        elif vocab_size < 300:
            return {
                "type": "translation",
                "english": "I eat sushi",
                "hint": "Use ～ます form"
            }
        else:
            return {
                "type": "prompt",
                "prompt": "昨日、何を食べましたか？日本語で書いてください。",
                "grammar_hint": "～ました"
            }
    
    def log_session(self, prompt_type: str, prompt: str,
                   user_response: str, score: float,
                   feedback: str, time_spent: int):
        """Log writing session."""
        conn = sqlite3.connect(self.db_path)
        
        conn.execute("""
            INSERT INTO writing_sessions
            (date, prompt_type, prompt, user_response, score, 
             feedback, time_spent)
            VALUES (DATE('now'), ?, ?, ?, ?, ?, ?)
        """, (prompt_type, prompt, user_response, score, 
               feedback, time_spent))
        
        conn.commit()
        conn.close()
    
    def evaluate_writing(self, prompt: str, user_response: str,
                        vocab_words: List[str]) -> Dict:
        """Evaluate writing (uses LLM for naturalness)."""
        # Check vocabulary usage
        vocab_used = [w for w in vocab_words if w in user_response]
        
        # TODO: Use LLM for naturalness evaluation
        return {
            "vocab_used": vocab_used,
            "score": 0.0,  # Would be LLM score
            "feedback": ""  # Would be LLM feedback
        }
```

---

## Error Handling

### Tasks

#### Task 1: Error Handler

**File:** `learn_jp/errors.py`

```python
"""Error handling for learn-jp."""

import requests
from typing import Dict, List


class ErrorHandler:
    """Handles errors and pre-flight checks."""
    
    def __init__(self, anki_url: str = "http://localhost:8765"):
        self.anki_url = anki_url
    
    def pre_flight_check(self) -> Dict:
        """Run pre-flight checks before session."""
        errors = []
        
        # 1. Check Anki (required)
        if not self.check_anki():
            errors.append("Anki is not running. Please start Anki and try again.")
        
        # 2. Check database
        if not self.check_database():
            errors.append("Database locked. Close other instances.")
        
        # 3. Check network (warning only)
        if not self.check_network():
            print("⚠ Network unavailable. Some features disabled.")
        
        return {
            "success": len(errors) == 0,
            "errors": errors
        }
    
    def check_anki(self) -> bool:
        """Check if Anki is running."""
        try:
            response = requests.get(self.anki_url, timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def check_database(self) -> bool:
        """Check if database is accessible."""
        return True  # TODO: Implement
    
    def check_network(self) -> bool:
        """Check if network is available."""
        try:
            response = requests.get("https://jisho.org", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def handle_story_generation(self, api_key: str) -> Dict:
        """Handle story generation with fallback."""
        try:
            # Try generating new story
            from japanese_story_generator import StoryGenerator
            gen = StoryGenerator(api_key)
            story = gen.generate(vocab_words, strict_vocab=True)
            return {"story": story, "source": "generated"}
        except Exception as e:
            # Fallback to cached story
            story = self._get_cached_story()
            return {"story": story, "source": "cached"}
    
    def _get_cached_story(self) -> str:
        """Get cached story for fallback."""
        # TODO: Implement story caching
        return "Cached story placeholder"
```

---

## Testing

```bash
# Test reading comprehension
$ learn-jp story
Generating story...

Story:
太郎は昨日、市場に行きました。彼は寿司を食べました。

Questions:
1. Where did Taro go yesterday?
   A) Store  B) Market  C) School
> B
✓ Correct!

2. What did he eat?
   A) Sushi  B) Ramen  C) Curry
> A
✓ Correct!

Score: 2/2 (100%)

# Test writing practice
$ learn-jp write
Prompt: Write what you ate yesterday using ～ました
> 私は昨日、ラーメンを食べました。
✓ Great! Natural sentence.

# Test error handling
$ learn-jp start
✗ Anki is not running. Please start Anki and try again.
```

---

## Checklist

### Reading Comprehension
- [ ] Create ReadingComprehension class
- [ ] Create StorySession class
- [ ] Implement adaptive question config
- [ ] Implement question count limits
- [ ] Implement session logging
- [ ] Test reading comprehension flow

### Writing Practice
- [ ] Create WritingPractice class
- [ ] Implement adaptive prompt generation
- [ ] Implement session logging
- [ ] Test writing practice flow

### Error Handling
- [ ] Create ErrorHandler class
- [ ] Implement pre-flight checks
- [ ] Implement Anki detection
- [ ] Implement network detection
- [ ] Implement story fallback
- [ ] Test error scenarios

### Integration
- [ ] Integrate with CLI commands
- [ ] Test full session flow
- [ ] Test offline mode
- [ ] Test level progression

## Tasks

### Task 1: End-to-End Testing

Create test scripts to verify all components work together.

**File:** `tests/test_workflow.py`

```python
"""End-to-end workflow tests."""

import pytest
import sqlite3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.anki_connector import AnkiConnector
from lib.jisho_client import JishoClient
from lib.progress_tracker import ProgressTracker
from lib.study_manager import StudyManager


@pytest.fixture
def test_db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    
    # Load schema
    schema_file = Path(__file__).parent.parent / "progress" / "schema.sql"
    with open(schema_file) as f:
        conn.executescript(f.read())
    
    return str(db_path)


class TestJishoClient:
    def test_lookup(self):
        client = JishoClient()
        result = client.lookup("食べる")
        assert result is not None
        assert "reading" in result
        assert "meaning" in result


class TestProgressTracker:
    def test_update_mastery(self, test_db):
        tracker = ProgressTracker(test_db)
        
        # First review - severity 0 (instant recall)
        tracker.update_mastery("n5-v-001", 0)
        
        status = tracker.get_mastery_status("n5-v-001")
        assert status["streak"] == 1
        assert status["status"] == "learning"
    
    def test_mastery_streak(self, test_db):
        tracker = ProgressTracker(test_db)
        
        # 5 consecutive good reviews
        for _ in range(5):
            tracker.update_mastery("n5-v-001", 0)
        
        status = tracker.get_mastery_status("n5-v-001")
        assert status["streak"] == 5
    
    def test_regression_detection(self, test_db):
        tracker = ProgressTracker(test_db)
        
        # Build up streak
        for _ in range(5):
            tracker.update_mastery("n5-v-001", 0)
        
        # Then miss
        is_regression = tracker.detect_regression("n5-v-001", 3)
        assert is_regression == True


class TestStudyManager:
    def test_get_known_vocabulary(self, test_db):
        manager = StudyManager(test_db, "test-key")
        
        # This would need mock data
        # Just testing method exists
        vocab = manager.get_known_vocabulary("n5")
        assert isinstance(vocab, list)
```

---

### Task 2: Error Handling

Create comprehensive error handling throughout the codebase.

**File:** `lib/error_handler.py`

```python
"""Error handling utilities."""

import logging
from functools import wraps


def handle_errors(func):
    """Decorator for consistent error handling."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ConnectionError as e:
            logging.error(f"Connection error in {func.__name__}: {e}")
            return {"error": "Connection failed", "details": str(e)}
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {e}")
            return {"error": "Unexpected error", "details": str(e)}
    return wrapper


class AnkiConnectionError(Exception):
    """Anki is not running or AnkiConnect not installed."""
    pass


class JishoAPIError(Exception):
    """Jisho API request failed."""
    pass


class DatabaseError(Exception):
    """Database operation failed."""
    pass
```

---

### Task 3: Create Setup Script

**File:** `scripts/setup.py`

```python
#!/usr/bin/env python3
"""Initial setup for learn-jp."""

import os
import sys
from pathlib import Path

# Add parent directory
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_anki():
    """Check if Anki is running."""
    from lib.anki_connector import connector
    
    if connector.is_available():
        print("✓ Anki is running and AnkiConnect is available")
        return True
    else:
        print("✗ Anki is not running or AnkiConnect not installed")
        print("  Please install AnkiConnect plugin (code: 2055492159)")
        return False


def check_api_key():
    """Check if OpenRouter API key is set."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        print("✓ OpenRouter API key is set")
        return True
    
    # Check file
    key_file = Path(".openrouter-api-key")
    if key_file.exists():
        print("✓ OpenRouter API key file exists")
        return True
    
    print("✗ OpenRouter API key not found")
    print("  Please set OPENROUTER_API_KEY or create .openrouter-api-key file")
    return False


def init_database():
    """Initialize database."""
    from scripts.init_db import init_db
    
    db_file = Path("progress/progress.db")
    if db_file.exists():
        print("✓ Database already exists")
    else:
        init_db()
        print("✓ Database initialized")


def main():
    print("=== learn-jp Setup ===\n")
    
    checks = [
        ("Anki", check_anki),
        ("API Key", check_api_key),
    ]
    
    all_passed = True
    for name, check in checks:
        print(f"\nChecking {name}...")
        if not check():
            all_passed = False
    
    print("\n--- Database ---")
    init_database()
    
    print("\n=== Setup Complete ===")
    
    if all_passed:
        print("\nYou're ready to start learning!")
        print("Run: python scripts/seed_anki.py --level n5")
    else:
        print("\nPlease fix the issues above before continuing.")


if __name__ == "__main__":
    main()
```

---

### Task 4: Create README.md

**File:** `README.md`

```markdown
# learn-jp

A Japanese language learning system with AI-powered mentoring.

## Features

- 📚 **Vocabulary Management** - Auto-fetch JLPT vocabulary
- 🎴 **Anki Integration** - Seamless flashcard drilling
- 📖 **Reading Practice** - AI-generated stories using your vocabulary
- ✍️ **Writing Practice** - Guided writing exercises
- 📊 **Progress Tracking** - Detailed mastery tracking
- 🤖 **AI Mentor** - Personalized study suggestions

## Quick Start

### Prerequisites

1. **Anki** - Download from https://apps.ankiweb.net/
2. **AnkiConnect Plugin** - Code: `2055492159`
3. **OpenRouter API Key** - Get from https://openrouter.ai

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd learn-jp

# Setup
python scripts/setup.py

# Seed initial vocabulary
python scripts/seed_anki.py --level n5
```

### Usage

1. Open Anki and review your flashcards
2. Ask your AI mentor: "I want to study today"
3. Follow the mentor's guidance

## Project Structure

```
learn-jp/
├── AGENTS.md              # AI mentor instructions
├── progress/
│   ├── schema.sql         # Database schema
│   └── progress.db        # Your progress data
├── scripts/
│   ├── setup.py           # Initial setup
│   ├── seed_anki.py       # Add vocabulary to Anki
│   └── init_db.py         # Initialize database
├── lib/
│   ├── anki_connector.py  # Anki API wrapper
│   ├── jisho_client.py    # Japanese dictionary
│   └── progress_tracker.py # Progress tracking
└── data/
    └── jlpt/              # JLPT vocabulary data
```

## Documentation

See `docs/` folder for detailed documentation:
- [Architecture](docs/ARCHITECTURE.md)
- [Database Schema](docs/DATABASE.md)
- [Anki Integration](docs/ANKI-INTEGRATION.md)
- [Phase Documentation](docs/PHASE-*.md)
```

---

### Task 5: Create .gitignore

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
.jisho_cache.json

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

# OS
.DS_Store
Thumbs.db
```

---

### Task 6: Final Documentation Review

Ensure all documentation is complete:

- [ ] README.md is clear and comprehensive
- [ ] All phases documented
- [ ] Database schema documented
- [ ] API integrations documented
- [ ] Examples are working
- [ ] Error handling is documented

---

## Testing Checklist

- [ ] Setup script works
- [ ] Database initializes correctly
- [ ] Anki connection works
- [ ] Jisho API works
- [ ] Vocabulary can be seeded
- [ ] Progress tracking works
- [ ] Reading exercises generate
- [ ] Study suggestions work
- [ ] Error handling works

---

## Deployment Checklist

- [ ] All tests pass
- [ ] Documentation is complete
- [ ] .gitignore is correct
- [ ] No sensitive data in repo
- [ ] Setup instructions are clear
- [ ] Error messages are helpful
```

---

## Checklist

- [ ] Create test scripts
- [ ] Add error handling
- [ ] Create setup script
- [ ] Create README.md
- [ ] Create .gitignore
- [ ] Test end-to-end workflow
- [ ] Review all documentation
- [ ] Verify all imports work
- [ ] Check for sensitive data
- [ ] Final testing
