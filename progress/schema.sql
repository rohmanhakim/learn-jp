-- learn-jp database schema

-- Vocabulary table
CREATE TABLE IF NOT EXISTS vocabulary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT UNIQUE NOT NULL,
    content TEXT NOT NULL,
    reading TEXT,
    meaning TEXT,
    level TEXT NOT NULL,
    part_of_speech TEXT,
    source TEXT,
    anki_note_id INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_vocab_level ON vocabulary(level);
CREATE INDEX IF NOT EXISTS idx_vocab_item_id ON vocabulary(item_id);

-- Kanji table
CREATE TABLE IF NOT EXISTS kanji (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT UNIQUE NOT NULL,
    character TEXT NOT NULL,
    on_reading TEXT,
    kun_reading TEXT,
    meanings TEXT,
    level TEXT NOT NULL,
    stroke_count INTEGER,
    anki_note_id INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Grammar table
CREATE TABLE IF NOT EXISTS grammar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT UNIQUE NOT NULL,
    pattern TEXT NOT NULL,
    structure TEXT,
    meaning TEXT NOT NULL,
    level TEXT NOT NULL,
    examples TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    type TEXT NOT NULL,
    items_studied INTEGER,
    correct INTEGER,
    accuracy REAL,
    time_spent_seconds INTEGER,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(date);
CREATE INDEX IF NOT EXISTS idx_sessions_type ON sessions(type);

-- Item reviews table
CREATE TABLE IF NOT EXISTS item_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    item_type TEXT NOT NULL,
    severity INTEGER NOT NULL,
    response_time_ms INTEGER,
    error_type TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_item_reviews_item ON item_reviews(item_id);
CREATE INDEX IF NOT EXISTS idx_item_reviews_session ON item_reviews(session_id);

-- Mastery table
CREATE TABLE IF NOT EXISTS mastery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT UNIQUE NOT NULL,
    item_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    streak INTEGER DEFAULT 0,
    last_review_date TEXT,
    next_review_date TEXT,
    total_reviews INTEGER DEFAULT 0,
    correct_reviews INTEGER DEFAULT 0,
    mastery_date TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Stories table
CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    theme TEXT,
    content TEXT NOT NULL,
    vocab_used TEXT,
    vocab_count INTEGER,
    difficulty TEXT,
    length INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Reading sessions table
CREATE TABLE IF NOT EXISTS reading_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER,
    date TEXT NOT NULL,
    time_spent_seconds INTEGER,
    comprehension_score REAL,
    questions_answered INTEGER,
    questions_correct INTEGER,
    new_words_learned TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (story_id) REFERENCES stories(id)
);

-- Grammar progress tracking (Phase 4)
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    created_at TEXT DEFAULT (datetime('now')),
    last_used_at TEXT
);

-- Grammar sessions
CREATE TABLE IF NOT EXISTS grammar_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    pattern TEXT,
    question_type TEXT,
    correct INTEGER,
    time_spent INTEGER
);

-- Writing practice sessions
CREATE TABLE IF NOT EXISTS writing_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT DEFAULT (datetime('now'))
);
