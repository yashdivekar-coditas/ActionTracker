"""CLI: parses arguments, wires the modules together and formats output."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import List, Optional, Sequence

from actiontrack.ingest import ingest_folder
from actiontrack.model import ActionItem
from actiontrack.people import PeopleError, load_people
from actiontrack.store import Store

EXIT_OK, EXIT_ERROR = 0, 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exit_:  # argparse exits 2 on a usage error and 0 for --help
        return exit_.code or 0
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
    print(
        f"{report.notes_read} notes read, {report.items_new} new items, "
        f"{report.needs_review} need review"
    )
    return EXIT_OK


def _list(args, store: Store, people) -> int:
    today = args.today or date.today()
    items = store.items(
        needs_review=args.needs_review,
        owner=args.owner,
        status=args.status,
        due_before=args.due_before,
        today=today,
    )
    if args.json:
        print(json.dumps([_as_dict(item, today) for item in items], indent=2))
    else:
        print(_table(items, with_review=args.needs_review))
    return EXIT_OK


def _as_dict(item: ActionItem, today: date) -> dict:
    return {
        "id": item.id,
        "task": item.task,
        "status": item.status,
        "overdue": item.status == "open" and item.due is not None and item.due < today,
        "due": item.due.isoformat() if item.due else None,
        "owners": [{"name": o.name, "confirmed": o.confirmed} for o in item.owners],
        "sources": [],  # ticket 06 stores Sources; list them here
        "flags": [{"kind": f.kind, "detail": f.detail} for f in item.flags],
    }


def _date(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid date {text!r}, expected YYYY-MM-DD")


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
        ", ".join(o.name + ("" if o.confirmed else " (unconfirmed)") for o in item.owners) or "-",
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
    list_.add_argument("--owner", help="first name (every match), full name (exact) or 'none' (Unowned)")
    list_.add_argument("--status", choices=["open", "done", "overdue"], help="only items with this status")
    list_.add_argument("--due-before", type=_date, metavar="DATE", help="only items due before DATE (YYYY-MM-DD)")
    list_.add_argument("--today", type=_date, metavar="DATE", help="pin today's date (YYYY-MM-DD)")
    list_.add_argument("--json", action="store_true", help="machine-readable output")
    list_.set_defaults(command=_list)
    return parser


if __name__ == "__main__":
    sys.exit(main())
