# Phase 6: Polish & Testing

## Goal

Final testing, error handling, documentation, and deployment preparation.

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
