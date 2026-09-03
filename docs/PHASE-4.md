# Phase 4: Progress Tracking (Updated)

## Goal

Implement detailed progress tracking, mastery detection, and level progression.

**Reference:** See WORKFLOW-FINDINGS.md for full design.

---

## Overview

This phase implements:
1. Vocabulary mastery tracking (severity-based)
2. Grammar mastery tracking (accuracy-based)
3. Reading comprehension tracking (score-based)
4. Writing practice tracking
5. Violation history tracking
6. Level progression logic

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

## Tasks

### Task 1: Create Progress Tracker

**File:** `lib/progress_tracker.py`

```python
"""Progress tracking and mastery detection."""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional


class ProgressTracker:
    """Tracks learning progress and detects mastery."""
    
    MASTERY_CRITERIA = {
        "min_streak": 5,
        "min_days": 7,
        "min_reviews_in_14_days": 3
    }
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_db(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def update_mastery(self, item_id: str, severity: int):
        """Update mastery status after a review."""
        db = self.get_db()
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Get current mastery
        current = db.execute(
            "SELECT * FROM mastery WHERE item_id = ?",
            (item_id,)
        ).fetchone()
        
        if current:
            # Update existing
            new_streak = current['streak'] + 1 if severity <= 1 else 0
            new_total = current['total_reviews'] + 1
            new_correct = current['correct_reviews'] + (1 if severity <= 1 else 0)
            
            # Determine new status
            new_status = self._calculate_status(
                new_streak, new_total, new_correct, today
            )
            
            db.execute("""
                UPDATE mastery 
                SET streak = ?, total_reviews = ?, correct_reviews = ?,
                    last_review_date = ?, status = ?, updated_at = datetime('now')
                WHERE item_id = ?
            """, (new_streak, new_total, new_correct, today, new_status, item_id))
        else:
            # Create new
            new_streak = 1 if severity <= 1 else 0
            new_status = "learning"
            
            db.execute("""
                INSERT INTO mastery (item_id, item_type, status, streak, 
                                     last_review_date, total_reviews, correct_reviews)
                VALUES (?, 'vocabulary', ?, ?, ?, 1, ?)
            """, (item_id, new_status, new_streak, today, 1 if severity <= 1 else 0))
        
        db.commit()
    
    def _calculate_status(self, streak: int, total_reviews: int, 
                         correct_reviews: int, today: str) -> str:
        """Calculate mastery status based on criteria."""
        if total_reviews < 3:
            return "learning"
        
        if streak >= self.MASTERY_CRITERIA["min_streak"]:
            # Check time span
            # (simplified - would need to check actual dates)
            return "mastered"
        
        return "review"
    
    def get_mastery_status(self, item_id: str) -> dict:
        """Get mastery status for an item."""
        db = self.get_db()
        
        result = db.execute(
            "SELECT * FROM mastery WHERE item_id = ?",
            (item_id,)
        ).fetchone()
        
        if result:
            return dict(result)
        return {"item_id": item_id, "status": "new", "streak": 0}
    
    def get_items_needing_review(self, limit: int = 20) -> List[dict]:
        """Get items that need review."""
        db = self.get_db()
        
        # Items not mastered and not reviewed recently
        results = db.execute("""
            SELECT v.*, m.status, m.streak, m.last_review_date
            FROM vocabulary v
            LEFT JOIN mastery m ON v.item_id = m.item_id
            WHERE m.status != 'mastered' OR m.status IS NULL
            ORDER BY m.last_review_date ASC NULLS FIRST
            LIMIT ?
        """, (limit,)).fetchall()
        
        return [dict(row) for row in results]
    
    def get_items_at_risk(self) -> List[dict]:
        """Get mastered items at risk of regression."""
        db = self.get_db()
        
        # Mastered items not reviewed in 7+ days
        results = db.execute("""
            SELECT v.*, m.status, m.streak, m.last_review_date
            FROM vocabulary v
            JOIN mastery m ON v.item_id = m.item_id
            WHERE m.status = 'mastered'
              AND m.last_review_date < date('now', '-7 days')
            ORDER BY m.last_review_date ASC
        """).fetchall()
        
        return [dict(row) for row in results]
    
    def detect_regression(self, item_id: str, severity: int) -> bool:
        """Check if an item has regressed."""
        db = self.get_db()
        
        # Get recent reviews
        recent = db.execute("""
            SELECT ir.severity, ir.created_at
            FROM item_reviews ir
            WHERE ir.item_id = ?
            ORDER BY ir.created_at DESC
            LIMIT 3
        """, (item_id,)).fetchall()
        
        if not recent:
            return False
        
        # Count recent failures
        recent_failures = sum(1 for r in recent if r['severity'] >= 2)
        
        # Immediate regression on severity 3
        if severity == 3:
            return True
        
        # Regression if 2+ failures in last 3 reviews
        if recent_failures >= 2:
            return True
        
        return False
    
    def get_progress_summary(self, level: str = None) -> dict:
        """Get overall progress summary."""
        db = self.get_db()
        
        # Total vocabulary
        query = "SELECT COUNT(*) as count FROM vocabulary"
        params = ()
        if level:
            query += " WHERE level = ?"
            params = (level,)
        
        total = db.execute(query, params).fetchone()['count']
        
        # By status
        query = """
            SELECT m.status, COUNT(*) as count
            FROM mastery m
            JOIN vocabulary v ON m.item_id = v.item_id
        """
        params = ()
        if level:
            query += " WHERE v.level = ?"
            params = (level,)
        
        query += " GROUP BY m.status"
        
        status_counts = db.execute(query, params).fetchall()
        statuses = {row['status']: row['count'] for row in status_counts}
        
        # Recent activity
        recent_sessions = db.execute("""
            SELECT COUNT(*) as count
            FROM sessions
            WHERE date >= date('now', '-7 days')
        """).fetchone()['count']
        
        return {
            "total_vocabulary": total,
            "by_status": statuses,
            "mastered": statuses.get("mastered", 0),
            "in_review": statuses.get("review", 0),
            "learning": statuses.get("learning", 0),
            "not_started": total - sum(statuses.values()),
            "sessions_last_7_days": recent_sessions,
            "mastery_percentage": (
                statuses.get("mastered", 0) / total * 100 if total > 0 else 0
            )
        }
    
    def get_weak_areas(self) -> List[dict]:
        """Identify weak areas for focused study."""
        db = self.get_db()
        
        # Items with high failure rate
        weak = db.execute("""
            SELECT v.content, v.reading, v.meaning, v.level,
                   COUNT(ir.id) as reviews,
                   SUM(CASE WHEN ir.severity >= 2 THEN 1 ELSE 0 END) as failures
            FROM vocabulary v
            JOIN item_reviews ir ON v.item_id = ir.item_id
            GROUP BY v.item_id
            HAVING failures * 1.0 / reviews > 0.3
            ORDER BY failures DESC
            LIMIT 10
        """).fetchall()
        
        return [dict(row) for row in weak]
```

---

### Task 2: Create Study Suggestions

**File:** `lib/study_suggester.py`

```python
"""Generate study suggestions based on progress."""

from datetime import datetime, timedelta
from typing import List


class StudySuggester:
    """Suggests what to study based on progress."""
    
    def __init__(self, progress_tracker):
        self.tracker = progress_tracker
    
    def get_today_suggestion(self, level: str = None) -> dict:
        """Get study suggestions for today."""
        suggestions = {
            "anki_review": [],
            "new_vocabulary": [],
            "reading_practice": False,
            "weak_areas": []
        }
        
        # Check for items needing review
        due_items = self.tracker.get_items_needing_review(limit=10)
        if due_items:
            suggestions["anki_review"] = due_items
        
        # Check for items at risk
        at_risk = self.tracker.get_items_at_risk()
        if at_risk:
            suggestions["weak_areas"] = at_risk[:5]  # Top 5
        
        # Check if reading practice is appropriate
        progress = self.tracker.get_progress_summary(level)
        if progress["in_review"] + progress["mastered"] >= 20:
            suggestions["reading_practice"] = True
        
        return suggestions
    
    def get_review_schedule(self, level: str) -> List[dict]:
        """Get suggested review schedule for the week."""
        schedule = []
        
        # Get items by status
        due_today = self.tracker.get_items_needing_review(limit=10)
        at_risk = self.tracker.get_items_at_risk()
        
        # Simple schedule: review due items + at-risk items
        for item in due_today:
            schedule.append({
                "item": item,
                "reason": "Due for review",
                "priority": "high"
            })
        
        for item in at_risk[:5]:
            schedule.append({
                "item": item,
                "reason": "At risk of regression",
                "priority": "high"
            })
        
        return schedule
    
    def get_mastery_forecast(self, current_rate: float) -> dict:
        """Forecast when mastery will be achieved."""
        progress = self.tracker.get_progress_summary()
        
        remaining = progress["not_started"] + progress["learning"]
        
        if current_rate > 0:
            days_to_mastery = remaining / current_rate
            estimated_date = datetime.now() + timedelta(days=days_to_mastery)
        else:
            days_to_mastery = None
            estimated_date = None
        
        return {
            "items_remaining": remaining,
            "daily_rate": current_rate,
            "estimated_days": days_to_mastery,
            "estimated_completion": estimated_date.strftime("%Y-%m-%d") if estimated_date else None
        }
```

---

### Task 3: Create Progress Reports

**File:** `lib/progress_reporter.py`

```python
"""Generate progress reports."""

from datetime import datetime


class ProgressReporter:
    """Generates progress reports."""
    
    def __init__(self, progress_tracker):
        self.tracker = progress_tracker
    
    def daily_report(self, level: str = None) -> str:
        """Generate daily progress report."""
        progress = self.tracker.get_progress_summary(level)
        
        report = f"""
=== Daily Progress Report ===
Date: {datetime.now().strftime("%Y-%m-%d")}

--- Vocabulary Summary ---
Total Items: {progress['total_vocabulary']}
Mastered: {progress['mastered']} ({progress['mastery_percentage']:.1f}%)
In Review: {progress['in_review']}
Learning: {progress['learning']}
Not Started: {progress['not_started']}

--- Recent Activity ---
Sessions (last 7 days): {progress['sessions_last_7_days']}
"""
        
        # Add weak areas if any
        weak = self.tracker.get_weak_areas()
        if weak:
            report += "\n--- Weak Areas ---\n"
            for item in weak[:5]:
                rate = item['failures'] / item['reviews'] * 100
                report += f"- {item['content']} ({item['reading']}): {rate:.0f}% failure rate\n"
        
        return report
    
    def weekly_report(self, level: str = None) -> str:
        """Generate weekly progress report."""
        # This would aggregate data from multiple days
        # Simplified version
        return self.daily_report(level)
```

---

## Testing

### Test Progress Tracker
```bash
python -c "
from lib.progress_tracker import ProgressTracker
pt = ProgressTracker('progress/progress.db')
print(pt.get_progress_summary('n5'))
"
```

### Test Study Suggestions
```bash
python -c "
from lib.progress_tracker import ProgressTracker
from lib.study_suggester import StudySuggester
pt = ProgressTracker('progress/progress.db')
ss = StudySuggester(pt)
print(ss.get_today_suggestion('n5'))
"
```

---

## Checklist

### Core Progress Tracking
- [ ] Create ProgressTracker class
- [ ] Create StudySuggester class
- [ ] Create ProgressReporter class
- [ ] Test mastery detection
- [ ] Test regression detection
- [ ] Test study suggestions
- [ ] Test progress reports

### New Requirements (from WORKFLOW-FINDINGS.md)
- [ ] Add grammar_progress table to schema
- [ ] Add grammar_question_cache table to schema
- [ ] Add grammar_sessions table to schema
- [ ] Add writing_sessions table to schema
- [ ] Add session_violations table to schema
- [ ] Add user_config table to schema
- [ ] Implement grammar mastery tracking
- [ ] Implement reading comprehension tracking
- [ ] Implement writing practice tracking
- [ ] Implement violation history tracking
- [ ] Implement level progression logic
- [ ] Add configurable threshold (default 80%)

---

## Database Schema Updates

Add to schema.sql:

```sql
-- Grammar progress tracking
CREATE TABLE IF NOT EXISTS grammar_progress (
    pattern TEXT PRIMARY KEY,
    level TEXT,
    tier INTEGER,                    -- 1, 2, or 3
    mastery REAL DEFAULT 0,          -- 0.0 to 1.0
    sessions INTEGER DEFAULT 0,
    correct INTEGER DEFAULT 0,
    last_practiced TEXT,
    status TEXT DEFAULT 'new'        -- new, learning, mastered
);

-- Grammar question cache (for Tier 2)
CREATE TABLE IF NOT EXISTS grammar_question_cache (
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
    effectiveness REAL,
    created_at TEXT,
    last_used_at TEXT
);

-- Grammar sessions
CREATE TABLE IF NOT EXISTS grammar_sessions (
    id INTEGER PRIMARY KEY,
    date TEXT,
    pattern TEXT,
    question_type TEXT,
    correct INTEGER,
    time_spent INTEGER
);

-- Writing practice sessions
CREATE TABLE IF NOT EXISTS writing_sessions (
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

-- Session violations (for tracking reduction)
CREATE TABLE IF NOT EXISTS session_violations (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,
    violation_count INTEGER,
    violation_rate REAL,
    date TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- User configuration
CREATE TABLE IF NOT EXISTS user_config (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);
```
