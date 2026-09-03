# Phase Update Summary

**Date:** 2025-09-03
**Purpose:** Summary of changes needed to align phases with WORKFLOW-FINDINGS.md

---

## Overview

Current phases need updates to reflect:
1. CLI-first workflow (not agent-first)
2. Automatic session recording (not manual reporting)
3. Three-tier grammar system
4. Writing practice
5. Error handling
6. Level progression with deck management

---

## Phase Status

| Phase | Status | Updates Needed |
|-------|--------|----------------|
| Phase 0 | ✅ Complete | Minor: verify CLI integration |
| Phase 1 | ✅ Complete | Minor: add new tables to schema |
| Phase 2 | 🔄 In Progress | Add CLI entry point, complete tasks |
| Phase 3 | ⚠️ Needs Rewrite | Major: CLI-first workflow |
| Phase 4 | ⚠️ Needs Update | Add new tracking requirements |
| Phase 5 | ⚠️ Becomes Optional | AGENTS.md is now optional layer |
| Phase 6 | ⚠️ Needs Update | Add grammar, writing, error handling |

---

## Detailed Changes by Phase

### Phase 0: Story Generator (✅ Complete)
**No major changes needed.**
- Story generator is already refactored as package
- `generate_with_questions()` exists but needs integration
- Verify CLI works with learn-jp system

---

### Phase 1: Foundation (✅ Complete)
**Minor updates needed.**

Add to schema.sql:
```sql
-- Grammar progress tracking
CREATE TABLE IF NOT EXISTS grammar_progress (...);
CREATE TABLE IF NOT EXISTS grammar_question_cache (...);
CREATE TABLE IF NOT EXISTS grammar_sessions (...);

-- Writing practice
CREATE TABLE IF NOT EXISTS writing_sessions (...);

-- Violation tracking
CREATE TABLE IF NOT EXISTS session_violations (...);

-- Level progression config
CREATE TABLE IF NOT EXISTS user_config (...);
```

---

### Phase 2: Content Pipeline (🔄 In Progress)
**Add CLI entry point.**

Current tasks: Mostly done
New tasks:
- [ ] Create CLI entry point (`learn-jp`)
- [ ] Implement `learn-jp start`
- [ ] Implement `learn-jp end`
- [ ] Implement `learn-jp status`
- [ ] Implement `learn-jp story`

---

### Phase 3: Study Workflow (⚠️ Needs Major Rewrite)

**Current design (to be replaced):**
```
User → Agent → Scripts → Anki → User reports → Agent logs
```

**New design:**
```
User → CLI → Scripts → Anki → Auto-pull → Done
```

**New tasks:**
1. CLI Commands
   - `learn-jp start` - Pre-flight checks, show deck info
   - `learn-jp end` - Pull reviews, calculate mastery, show summary
   - `learn-jp status` - Show progress, mastery, next steps
   - `learn-jp story` - Generate story + comprehension test
   - `learn-jp grammar` - Grammar drill session
   - `learn-jp write` - Writing practice

2. Session Recording
   - Auto-pull reviews from AnkiConnect
   - Calculate mastery deterministically
   - No manual reporting

3. Error Handling
   - Check Anki is running before start
   - Fallback to cached stories
   - Offline mode support

---

### Phase 4: Progress Tracking (⚠️ Needs Update)

**Add new tracking requirements:**

1. Violation History
   - Track violation count per session
   - Show reduction trend over time

2. Level Progression
   - Configurable threshold (default 80%)
   - Auto-fetch next level deck when ready
   - Promote queued violations

3. Grammar Progress
   - Track per-pattern mastery
   - Three-tier system (core, cached, dynamic)

4. Writing Progress
   - Track completion and scores
   - Evaluate naturalness (LLM)

5. Reading Comprehension
   - Track comprehension score
   - Adaptive question count (max enforced)

---

### Phase 5: AGENTS.md (⚠️ Becomes Optional)

**Current:** Core component
**New:** Optional natural language interface

Move to Phase 7 or later:
- Agent as optional CLI wrapper
- Natural language interface
- "How's my progress?" → calls `learn-jp status`

---

### Phase 6: Polish & Testing (⚠️ Needs Update)

**Add new test cases:**
- CLI commands
- Error handling (Anki offline, API down)
- Grammar system (three-tier)
- Writing practice
- Level progression
- Offline mode

---

## Recommended Phase Order

```
Phase 0: Story Generator (DONE)
Phase 1: Foundation (DONE)
Phase 2: Content Pipeline (finish current tasks + CLI)
Phase 3: CLI Workflow (REWRITE)
Phase 4: Progress Tracking (UPDATE)
Phase 5: Grammar System (NEW)
Phase 6: Reading Comprehension (NEW)
Phase 7: Writing Practice (NEW)
Phase 8: Error Handling (NEW)
Phase 9: Polish & Testing (UPDATE)
Phase 10: AGENTS.md (OPTIONAL, later)
```

---

## File Structure (Target)

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
    ├── WORKFLOW-FINDINGS.md
    ├── PHASE-*.md
    └── ...
```
