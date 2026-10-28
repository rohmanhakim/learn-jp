"""Configuration for learn-jp, backed by the user_config table."""

from __future__ import annotations

from pathlib import Path

from .progress import DEFAULT_DB_PATH, ProgressTracker


class Config:
    """Read/write user configuration stored in progress.db."""

    def __init__(self, db_path: str | Path | None = None):
        self._tracker = ProgressTracker(db_path)

    def get(self, key: str, default: str | None = None) -> str | None:
        return self._tracker.get_config(key, default)

    def set(self, key: str, value: str) -> None:
        self._tracker.set_config(key, value)

    @property
    def current_level(self) -> str:
        return self.get("current_level", "n5")

    @current_level.setter
    def current_level(self, value: str) -> None:
        self.set("current_level", value)

    @property
    def level_threshold(self) -> float:
        try:
            return float(self.get("level_threshold", "0.8"))
        except (TypeError, ValueError):
            return 0.8

    @level_threshold.setter
    def level_threshold(self, value: float) -> None:
        self.set("level_threshold", str(value))

    @property
    def db_path(self) -> str:
        return self._tracker.db_path