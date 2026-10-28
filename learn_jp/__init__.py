"""learn-jp — CLI-first Japanese study tool.

The `learn_jp` package contains the orchestration layer (CLI, sessions)
and the domain kernel (ProgressTracker).  `lib/` remains for standalone
clients (AnkiConnect, Jisho, JLPT fetcher).
"""

from .progress import ProgressTracker, SessionResult, ItemReview, SessionSummary, Status
from .session import SessionManager, StartResult, EndResult
from .errors import ErrorHandler, PreFlightResult

__all__ = [
    "ProgressTracker",
    "SessionResult",
    "ItemReview",
    "SessionSummary",
    "Status",
    "SessionManager",
    "StartResult",
    "EndResult",
    "ErrorHandler",
    "PreFlightResult",
]