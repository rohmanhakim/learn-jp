"""learn-jp CLI entry point.

Commands:
    start   Pre-flight checks + show current status
    end     Pull reviews from Anki, record session, show summary
    status  Show current progress
"""

from __future__ import annotations

import argparse
import sys

from .session import EndResult, SessionManager, StartResult


def _fmt_status(status) -> str:
    lines = [
        f"Current level: {status.level.upper()}",
        f"Vocabulary: {status.vocab_mastered}/{status.vocab_total} mastered "
        f"({status.vocab_percent:.0f}%)",
        f"Grammar: {status.grammar_mastered}/{status.grammar_total} mastered "
        f"({status.grammar_percent:.0f}%)",
        f"Violation rate (7d): {status.violation_rate:.1%}",
    ]
    if status.last_session:
        lines.append(f"Last session: {status.last_session}")
    lines.append(f"Streak: {status.streak} day(s)")
    return "\n".join(lines)


def cmd_start(manager: SessionManager) -> int:
    result: StartResult = manager.start_session()
    if result.aborted:
        for err in result.errors or []:
            print(f"✗ {err}", file=sys.stderr)
        return 1
    status = result.status
    print("\n✓ Pre-flight checks passed")
    print(f"Current level: {status.level.upper()}")
    print(f"Deck: Japanese::{status.level.upper()}::Vocab")
    print(
        f"Vocabulary: {status.vocab_mastered}/{status.vocab_total} "
        f"mastered ({status.vocab_percent:.0f}%)"
    )
    print("\nReady! Open Anki and review.")
    return 0


def cmd_end(manager: SessionManager) -> int:
    result: EndResult = manager.end_session()
    if result.aborted:
        for err in result.errors or []:
            print(f"✗ {err}", file=sys.stderr)
        return 1
    if result.no_reviews:
        print("No new reviews found for today.")
        return 0
    summary = result.summary
    print("\nSession Summary")
    print("───────────────")
    print(f"Reviews: {summary.items_studied}")
    print(f"Correct: {summary.correct} ({summary.accuracy:.0f}%)")
    weak = [e for e in (summary.events or []) if e.type in ("regressed", "at_risk")]
    if weak:
        print("Weak items: " + ", ".join(e.item_id or "?" for e in weak))
    print("\nMastery Update")
    print("──────────────")
    for e in summary.events or []:
        if e.type == "mastery_gained":
            print(f"  ✓ {e.item_id} mastered")
        elif e.type == "level_up":
            print(f"  🎉 {e.detail}")
    if result.unmapped:
        print(
            f"\n⚠ {result.unmapped} review(s) could not be mapped to "
            f"vocabulary items"
        )
    return 0


def cmd_status(manager: SessionManager) -> int:
    status = manager.show_status()
    print(_fmt_status(status))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="learn-jp", description="Japanese learning system"
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("start", help="Start study session (pre-flight + status)")
    sub.add_parser("end", help="End study session (pull reviews, record mastery)")
    sub.add_parser("status", help="Show current progress")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    manager = SessionManager()

    if args.command == "start":
        return cmd_start(manager)
    if args.command == "end":
        return cmd_end(manager)
    if args.command == "status":
        return cmd_status(manager)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())