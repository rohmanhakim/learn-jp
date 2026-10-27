#!/usr/bin/env python3
"""Initialize the learn-jp database."""

import sqlite3
from pathlib import Path

SCHEMA_FILE = Path(__file__).parent.parent / "progress" / "schema.sql"
DB_FILE = Path(__file__).parent.parent / "progress" / "progress.db"


def init_db():
    """Initialize database with schema."""
    # Ensure progress directory exists
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Read schema
    with open(SCHEMA_FILE, 'r') as f:
        schema = f.read()
    
    # Create database
    conn = sqlite3.connect(str(DB_FILE))
    conn.executescript(schema)
    
    # Log schema version
    conn.execute(
        "INSERT OR IGNORE INTO schema_version (version) VALUES (2)"
    )
    conn.commit()
    conn.close()
    
    print(f"Database initialized at {DB_FILE}")


if __name__ == "__main__":
    init_db()
