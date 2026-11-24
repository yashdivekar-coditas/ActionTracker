"""CLI: parses arguments, wires the modules together and formats output."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import List, Optional, Sequence

from actiontrack.corrections import CorrectionError, UsageError, edit_item, mark_done, merge_items
from actiontrack.followup import DraftError, DraftSink, compose_all, format_email
from actiontrack.gmail import ClaudeSink
from actiontrack.ingest import ingest_folder
from actiontrack.model import ActionItem, Owner
from actiontrack.people import PeopleError, load_people
from actiontrack.store import Store

EXIT_OK, EXIT_ERROR, EXIT_USAGE = 0, 1, 2


def main(argv: Optional[Sequence[str]] = None, sink: Optional[DraftSink] = None) -> int:
    """`sink` receives Follow-up Drafts; tests pass a recording one."""
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
        args.sink = sink or ClaudeSink()
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
        f"{report.items_merged} merged, {report.needs_review} need review"
        + (f", {report.notes_unchanged} unchanged" if report.notes_unchanged else "")
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


def _correct(action):
    """Wrap a correction command: print the item it left behind, or the error (exit 1)."""

    def command(args, store: Store, people) -> int:
        try:
            item = action(args, store, people)
        except UsageError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return EXIT_USAGE
        except CorrectionError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return EXIT_ERROR
        print(f"#{item.id} {item.status}, due {item.due or '-'}, " + ", ".join(_owner_cell(o) for o in item.owners) + f": {item.task}")
        return EXIT_OK

    return command


def _followup(args, store: Store, people) -> int:
    today = args.today or date.today()
    emails, skipped = compose_all(store.items(status="open", today=today), people, today, args.owner)
    for name in skipped:
        print(f"skipped {name}: no email address in the people directory", file=sys.stderr)
    if not emails:
        print("no follow-ups to create")
        return EXIT_OK
    for email in emails:
        print(format_email(email))
        print("-" * 40)
    if args.dry_run:
        return EXIT_OK
    if not args.yes:
        try:
            answer = input(f"Create {len(emails)} drafts? [y/N] ")
        except EOFError:
            answer = ""
        if answer.strip().casefold() not in ("y", "yes"):
            print("nothing created")
            return EXIT_OK
    try:
        for email in emails:
            args.sink.create_draft(email)
    except DraftError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    print(f"Created {len(emails)} drafts.")
    return EXIT_OK


def _as_dict(item: ActionItem, today: date) -> dict:
    return {
        "id": item.id,
        "task": item.task,
        "status": item.status,
        "overdue": item.status == "open" and item.due is not None and item.due < today,
        "due": item.due.isoformat() if item.due else None,
        "owners": [{"name": o.name, "confirmed": o.confirmed} for o in item.owners],
        "sources": [
            {"note": s.note, "line": s.line, "date": s.date.isoformat(), "title": s.title}
            for s in item.sources
        ],
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


def _owner_cell(owner: Owner) -> str:
    return owner.name if owner.confirmed else f"{owner.name} (unconfirmed)"


def _row(item: ActionItem, with_review: bool) -> List[str]:
    row = [
        str(item.id),
        item.status,
        item.due.isoformat() if item.due else "-",
        ", ".join(_owner_cell(owner) for owner in item.owners) or "-",
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

    done = commands.add_parser("done", parents=[common], help="mark an item Done")
    done.add_argument("id", type=int)
    done.set_defaults(command=_correct(lambda args, store, people: mark_done(store, args.id)))

    edit = commands.add_parser("edit", parents=[common], help="correct an item's owner, due date or task")
    edit.add_argument("id", type=int)
    edit.add_argument("--owner", action="append", help="full name; repeat for an Owner Group")
    edit.add_argument("--due", type=_date, metavar="DATE", help="YYYY-MM-DD")
    edit.add_argument("--task", help="replacement task text")
    edit.set_defaults(command=_correct(lambda args, store, people: edit_item(store, args.id, args.owner or (), args.due, args.task, people)))

    merge = commands.add_parser("merge", parents=[common], help="fold item ID into another item")
    merge.add_argument("id", type=int)
    merge.add_argument("into", type=int)
    merge.set_defaults(command=_correct(lambda args, store, people: merge_items(store, args.id, args.into)))

    followup = commands.add_parser("followup", parents=[common], help="compose follow-up emails and save them as Gmail drafts")
    followup.add_argument("owner", nargs="?", help="only this owner (first name or full name)")
    followup.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    followup.add_argument("--dry-run", action="store_true", help="print the emails and stop")
    followup.add_argument("--today", type=_date, metavar="DATE", help="pin today's date (YYYY-MM-DD)")
    followup.set_defaults(command=_followup)
    return parser


if __name__ == "__main__":
    sys.exit(main())
