"""Ingester: reads a folder of Meeting Notes into the Store."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Mapping, Tuple, Union

from actiontrack.dates import resolve_due
from actiontrack.model import Flag
from actiontrack.notes import Malformed, Meeting, parse_note
from actiontrack.owners import resolve_owners
from actiontrack.store import Store


@dataclass
class Report:
    notes_read: int = 0
    skipped: List[Tuple[str, str]] = field(default_factory=list)  # (file name, reason)
    items_new: int = 0
    needs_review: int = 0


def ingest_folder(folder: Path, store: Store, people: Mapping[str, str]) -> Report:
    report = Report()
    for path in sorted(folder.glob("*.md")):
        if not path.is_file():
            continue
        meeting = _read(path)
        if isinstance(meeting, Malformed):
            report.skipped.append((path.name, meeting.reason))
            continue
        report.notes_read += 1
        for line in meeting.items:
            resolution = resolve_owners(line.owner, meeting.attendees, people)
            due = resolve_due(line.due, meeting.date)
            flags = list(resolution.flags)
            if line.due and due is None:
                flags.append(Flag("unresolved-due", line.due))
            store.add_item(
                task=line.task,
                due=due,
                done=line.done,
                owners=resolution.owners,
                flags=flags,
            )
            report.items_new += 1
            report.needs_review += bool(flags)
    return report


def _read(path: Path) -> Union[Meeting, Malformed]:
    try:
        return parse_note(path.read_bytes().decode("utf-8"))
    except UnicodeDecodeError:
        return Malformed("binary or undecodable file")
    except OSError as exc:
        return Malformed(f"unreadable file ({exc.strerror or exc})")
