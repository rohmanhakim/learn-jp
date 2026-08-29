# learn-jp - Development Guide

## Project Overview

A Japanese language learning system that integrates:
- **Anki** (spaced repetition flashcards) via AnkiConnect
- **AI Mentor** (progress tracking, study planning) via SQLite
- **Story Generator** (reading practice) via OpenRouter API
- **Content Pipeline** (vocabulary fetching) via JLPT lists + Jisho API

## Goal

Create a system similar to `dsa/` repo for learning Data Structures & Algorithms, but for Japanese language learning. The AI acts as a language coach and mentor.

## Core Skills Tracked

| Skill | How It's Practiced | Tool |
|-------|-------------------|------|
| **Vocabulary** | Flashcard drill | Anki |
| **Kanji** | Flashcard drill | Anki |
| **Reading** | Story comprehension | Agent + Story Generator |
| **Writing** | Sentence production | Agent-guided |
| **Grammar** | Pattern recognition | Agent-guided |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    learn-jp System                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐ │
│  │    Anki     │      │    Agent    │      │   Story     │ │
│  │  (Drill)    │◄────►│   (Brain)   │◄────►│  Generator  │ │
│  └─────────────┘      └─────────────┘      └─────────────┘ │
│         │                    │                    │          │
│         │                    │                    │          │
│         ▼                    ▼                    ▼          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Progress Database (SQLite)              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              External APIs                           │   │
│  │  ├─ AnkiConnect (localhost:8765)                     │   │
│  │  ├─ OpenRouter (google/gemma-4-31b-it:free)         │   │
│  │  ├─ Jisho API (jisho.org)                           │   │
│  │  └─ Tanos.co.uk (JLPT vocabulary lists)             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Development Phases

| Phase | Focus | Estimated Days | Status |
|-------|-------|----------------|--------|
| **0** | Refactor story generator to package | 1-2 | ⬜ Not started |
| **1** | Foundation (DB, repo, AnkiConnect) | 2-3 | ⬜ Not started |
| **2** | Content pipeline (JLPT, Jisho) | 2-3 | ⬜ Not started |
| **3** | Study workflow integration | 3-4 | ⬜ Not started |
| **4** | Progress tracking | 2-3 | ⬜ Not started |
| **5** | AGENTS.md mentor rules | 2-3 | ⬜ Not started |
| **6** | Polish & testing | 1-2 | ⬜ Not started |

## Documentation Structure

```
docs/
├── README.md                      # This file
├── ARCHITECTURE.md                # System architecture details
├── DATABASE.md                    # SQLite schema reference
├── ANKI-INTEGRATION.md            # AnkiConnect API details
├── OPENROUTER-INTEGRATION.md      # OpenRouter API details
├── CONTENT-PIPELINE.md            # JLPT + Jisho fetching
├── PHASE-0.md                     # Story generator refactoring
├── PHASE-1.md                     # Foundation setup
├── PHASE-2.md                     # Content pipeline
├── PHASE-3.md                     # Study workflow
├── PHASE-4.md                     # Progress tracking
├── PHASE-5.md                     # AGENTS.md mentor rules
├── PHASE-6.md                     # Polish & testing
└── AGENTS-TEMPLATE.md             # Mentor instructions template
```

## Key Design Decisions

### 1. Anki as Drill Engine
- Anki handles spaced repetition scheduling
- Agent tracks detailed progress and mastery
- AnkiConnect bridges the two systems

### 2. Auto-Seeding Vocabulary
- System fetches JLPT vocabulary lists (N5-N1)
- Uses Jisho API for readings, meanings, examples
- Creates Anki cards automatically via AnkiConnect
- No manual vocabulary input required (but supported)

### 3. Adaptive Reading Comprehension
- Questions evolve based on user's level
- Beginner: Multiple choice in English
- Intermediate: Short answer in English
- Advanced: Translation, summary, analysis

### 4. Story Generator via OpenRouter
- Uses free model: `google/gemma-4-31b-it:generate stories using only user's known vocabulary
- Adaptdifficulty to level

### 5. Unified Progress Database
- Tracks all skills (vocab, kanji, reading, writing)
- Single source of truth for mastery
- Enables smart study suggestions

## External Resources

| Resource | URL | Purpose |
|----------|-----|---------|
| AnkiConnect | https://ankiweb.net/shared/info/2055492159 | Anki plugin for API access |
| OpenRouter | https://openrouter.ai | AI model API |
| Jisho | https://jisho.org | Japanese dictionary API |
| Tanos | https://www.tanos.co.uk/jlpt/ | JLPT vocabulary lists |
| JLPT Guide | https://www.jlpt.jp/e/guideline/ | Official JLPT info |

## Quick Start (after development)

```bash
# 1. Install Anki plugin
# Open Anki → Tools → Add-ons → Get Add-ons → Code: 2055492159

# 2. Setup learn-jp
cd learn-jp
# (setup instructions will be added per phase)

# 3. Seed initial vocabulary
python scripts/seed_anki.py --level n5

# 4. Start studying
# Open Anki and review cards
# Then ask AI mentor: "I want to study today"
```
