# learn-jp - Development Guide

## Project Overview

A Japanese language learning system that integrates:
- **Anki** (spaced repetition flashcards) via AnkiConnect
- **SQLite** (progress tracking, mastery detection)
- **OpenRouter API** (content generation via small models)
- **CLI** (user interface, no agent required)

## Goal

Create a CLI-based Japanese learning system where:
- 90% of operations are deterministic (no LLM)
- 10% use OpenRouter for content generation (stories, questions)
- Agent (pi) is optional, not required

## Core Principle

**CLI-first, deterministic-heavy, LLM-minimal.**

```bash
$ learn-jp start    # Pre-flight checks, show deck info
$ learn-jp end      # Auto-pull reviews, calculate mastery
$ learn-jp status   # Show progress, next steps
$ learn-jp story    # Generate story + comprehension quiz
$ learn-jp grammar  # Grammar drill session
$ learn-jp write    # Writing practice
```

## Core Skills Tracked

| Skill | How It's Practiced | Tool | LLM? |
|-------|-------------------|------|------|
| **Vocabulary** | Flashcard drill | Anki | No |
| **Grammar** | Pattern drills | CLI + Anki | Tier 1: No, Tier 2-3: OpenRouter |
| **Reading** | Story comprehension | OpenRouter | Yes |
| **Writing** | Sentence production | OpenRouter | Yes |
| **Kanji** | Implicit through vocab | - | No |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    learn-jp System                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              CLI + Deterministic Scripts              │  │
│  │              (Required - 90% of operations)           │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │  • learn-jp start/end/status                          │  │
│  │  • AnkiConnect integration                            │  │
│  │  • Mastery calculation                                │  │
│  │  • Violation grading (heuristic)                      │  │
│  │  • Level progression (threshold)                      │  │
│  │  • Grammar Tier 1 (lookup table)                      │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          │ calls only for content           │
│                          ▼                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              OpenRouter API                           │  │
│  │              (Required - 10% content generation)      │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │  • Story generation                                   │  │
│  │  • Question generation                                │  │
│  │  • Grammar Tier 2-3                                   │  │
│  │  • Writing evaluation                                 │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              External Services                        │  │
│  │  ├─ AnkiConnect (localhost:8765)                      │  │
│  │  ├─ OpenRouter (google/gemma-4-26b-a4b-it:free)       │  │
│  │  ├─ Jisho API (jisho.org)                             │  │
│  │  └─ Tanos.co.uk (JLPT vocabulary lists)               │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Progress Database (SQLite)               │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
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

## Development Phases

| Phase | Focus | Status |
|-------|-------|--------|
| **0** | Refactor story generator to package | ✅ Complete |
| **1** | Foundation (DB, repo, AnkiConnect) | ✅ Complete |
| **2** | Content pipeline + CLI entry point | 🔄 In Progress (near complete) |
| **3** | CLI workflow (start/end/status) | 🔄 In Progress (core done) |
| **4** | Progress tracking + level progression | 🔄 In Progress (kernel done) |
| **5** | Grammar system (three-tier) | ⬜ Pending |
| **6** | Reading comprehension + writing | ⬜ Pending |

## Documentation Structure

```
docs/
├── README.md                      # This file
├── ARCHITECTURE.md                # System architecture details
├── DATABASE.md                    # SQLite schema reference
├── WORKFLOW-FINDINGS.md           # Design decisions & rationale
├── PHASE-UPDATE-SUMMARY.md        # Phase update summary
├── ANKI-INTEGRATION.md            # AnkiConnect API details
├── OPENROUTER-INTEGRATION.md      # OpenRouter API details
├── CONTENT-PIPELINE.md            # JLPT + Jisho fetching
├── VIOLATION_BASED_LEARNING.md    # Heuristic curriculum approach
├── PHASE-0.md                     # Story generator refactoring
├── PHASE-1.md                     # Foundation setup
├── PHASE-2.md                     # Content pipeline + CLI
├── PHASE-3.md                     # CLI workflow
├── PHASE-4.md                     # Progress tracking
├── PHASE-5.md                     # Grammar system
├── PHASE-6.md                     # Reading & writing
└── AGENTS-TEMPLATE.md             # Mentor instructions (optional)
```

## Key Design Decisions

### 1. CLI-First Design
- System works entirely via CLI commands
- No agent required for daily workflow
- Agent is optional natural language convenience

### 2. Deterministic-Heavy
- 90% of operations use no LLM
- AnkiConnect for review data
- Heuristic algorithms for mastery
- Template-based grammar drills (Tier 1)

### 3. LLM-Minimal
- OpenRouter only for content generation
- Stories, questions, writing evaluation
- Uses small/cheap models (Gemma, Qwen)
- No capable models required

### 4. Anki as Drill Engine
- Anki handles spaced repetition scheduling
- System tracks detailed progress in SQLite
- AnkiConnect bridges the two systems

### 5. Adaptive Everything
- Question format adapts to vocabulary size
- Question count adapts to story length
- Grammar drills adapt to mastery level
- Writing prompts adapt to skill level

### 6. Level Progression
- Configurable threshold (default 80%)
- Vocab + grammar mastery required
- Gradual deck fetching (violations → foundation → story)
- No time minimum

### 7. Violation-Based Learning
- Story violations feed vocabulary enrichment
- Graded by JLPT level (heuristic)
- Only add violations at current level
- Self-validating: violations decrease as vocabulary grows

## External Resources

| Resource | URL | Purpose |
|----------|-----|---------|
| AnkiConnect | https://ankiweb.net/shared/info/2055492159 | Anki plugin for API access |
| OpenRouter | https://openrouter.ai | AI model API |
| Jisho | https://jisho.org | Japanese dictionary API |
| Tanos | https://www.tanos.co.uk/jlpt/ | JLPT vocabulary lists |
| JLPT Guide | https://www.jlpt.jp/e/guideline/ | Official JLPT info |

## Quick Start

```bash
# 1. Install Anki plugin
# Open Anki → Tools → Add-ons → Get Add-ons → Code: 2055492159

# 2. Setup learn-jp
cd learn-jp
python scripts/init_db.py

# 3. Seed initial vocabulary
python scripts/seed_anki.py --level n5

# 4. Set OpenRouter API key
export OPENROUTER_API_KEY="sk-or-v1-..."

# 5. Start studying
$ learn-jp start
$ learn-jp end
$ learn-jp story
```
