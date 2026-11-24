"""CLI: parses arguments, wires the modules together and formats output."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from actiontrack.ingest import ingest_folder
from actiontrack.model import ActionItem
from actiontrack.people import PeopleError, load_people
from actiontrack.store import Store

EXIT_OK, EXIT_ERROR = 0, 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        people = load_people(args.people)
    except PeopleError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    with Store(args.db) as store:
        return args.command(args, store, people)


def _ingest(args, store: Store, people) -> int:
    if not args.folder.is_dir():
        print(f"error: {args.folder} is not a folder", file=sys.stderr)
        return EXIT_ERROR
    report = ingest_folder(args.folder, store, people)
    for name, reason in report.skipped:
        print(f"skipped {name}: {reason}", file=sys.stderr)
    print(
        f"{report.notes_read} notes read, {len(report.skipped)} skipped, {report.items_new} new items, "
        f"0 merged, {report.needs_review} need review"  # merging arrives with ticket 06
    )
    return EXIT_OK


def _list(args, store: Store, people) -> int:
    items = store.items(needs_review=args.needs_review)
    print(_table(items, with_review=args.needs_review))
    return EXIT_OK


def _table(items: List[ActionItem], with_review: bool) -> str:
    header = ["ID", "STATUS", "DUE", "OWNER", "TASK"] + (["REVIEW"] if with_review else [])
    rows = [header] + [_row(item, with_review) for item in items]
    widths = [max(len(row[col]) for row in rows) for col in range(len(header))]
    return "\n".join(
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip() for row in rows
    )


def _row(item: ActionItem, with_review: bool) -> List[str]:
    row = [
        str(item.id),
        item.status,
        item.due.isoformat() if item.due else "-",
        ", ".join(owner.name for owner in item.owners) or "-",
        item.task,
    ]
    if with_review:
        row.append(", ".join(str(flag) for flag in item.flags))
    return row


def _parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", type=Path, default=Path(".actiontrack.db"), help="database file")
    common.add_argument("--people", type=Path, default=Path("people.json"), help="people directory (name -> email)")

    parser = argparse.ArgumentParser(prog="actiontrack", description="Track action items from meeting notes.")
    commands = parser.add_subparsers(required=True, metavar="COMMAND")

    ingest = commands.add_parser("ingest", parents=[common], help="read every .md meeting note in a folder")
    ingest.add_argument("folder", type=Path)
    ingest.set_defaults(command=_ingest)

    list_ = commands.add_parser("list", parents=[common], help="show action items")
    list_.add_argument("--needs-review", action="store_true", help="only items flagged for review, with the reason")
    list_.set_defaults(command=_list)
    return parser


if __name__ == "__main__":
    sys.exit(main())
