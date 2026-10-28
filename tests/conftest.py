"""Shared fixtures for learn-jp tests."""
from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "progress" / "schema.sql"


@pytest.fixture
def temp_db_path() -> str:
    """A temp SQLite DB initialized with the project schema."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA_PATH.read_text())
        conn.commit()
    finally:
        conn.close()
    yield path
    os.remove(path)


@pytest.fixture
def tracker(temp_db_path: str):
    from learn_jp.progress import ProgressTracker

    return ProgressTracker(temp_db_path)
