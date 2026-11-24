"""Ingester: reads a folder of Meeting Notes into the Store."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from actiontrack.dates import resolve_due
from actiontrack.notes import parse_note
from actiontrack.owners import resolve_owners
from actiontrack.store import Store


@dataclass
class Report:
    notes_read: int = 0
    items_new: int = 0
    needs_review: int = 0


def ingest_folder(folder: Path, store: Store, people: Mapping[str, str]) -> Report:
    report = Report()
    meetings = [parse_note(path.read_text(encoding="utf-8")) for path in sorted(folder.glob("*.md"))]
    known = [name for meeting in meetings for name in meeting.attendees]
    for meeting in meetings:
        report.notes_read += 1
        for line in meeting.items:
            resolution = resolve_owners(line.owner, meeting.attendees, people, known)
            store.add_item(
                task=line.task,
                due=resolve_due(line.due, meeting.date),
                done=line.done,
                owners=resolution.owners,
                flags=resolution.flags,
            )
            report.items_new += 1
            report.needs_review += bool(resolution.flags)
    return report
