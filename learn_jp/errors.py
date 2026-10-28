"""Pre-flight checks and error handling for learn-jp.

All checks are passive: they never write to the DB or to Anki.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.anki_connector import AnkiConnector  # noqa: E402


@dataclass(frozen=True)
class PreFlightResult:
    """Result of a pre-flight check."""

    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ErrorHandler:
    """Pre-flight checks run before a session starts."""

    def __init__(self, anki: AnkiConnector | None = None):
        self.anki = anki or AnkiConnector()

    def pre_flight_check(self) -> PreFlightResult:
        """Run every pre-flight check and return the combined result."""
        errors: list[str] = []
        warnings: list[str] = []

        if not self.anki.is_available():
            errors.append(
                "Anki is not running or AnkiConnect is not reachable "
                "(http://localhost:8765). "
                "Start Anki and install the AnkiConnect add-on (2055492159)."
            )

        return PreFlightResult(
            success=not errors,
            errors=errors,
            warnings=warnings,
        )