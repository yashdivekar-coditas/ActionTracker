"""Ingester: reads a folder of Meeting Notes into the Store."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Mapping, Tuple, Union

from actiontrack.dates import resolve_due
from actiontrack.duplicates import HIGH_SIMILARITY, LOW_SIMILARITY, best_match
from actiontrack.model import Flag, Owner, Source
from actiontrack.notes import Malformed, Meeting, parse_note
from actiontrack.owners import resolve_owners
from actiontrack.store import Store


@dataclass
class Report:
    notes_read: int = 0
    notes_unchanged: int = 0
    skipped: List[Tuple[str, str]] = field(default_factory=list)  # (file name, reason)
    items_new: int = 0
    items_merged: int = 0
    needs_review: int = 0


def ingest_folder(folder: Path, store: Store, people: Mapping[str, str]) -> Report:
    report = Report()
    notes = []  # (file name, content hash, Meeting)
    for path in sorted(folder.glob("*.md")):
        if not path.is_file():
            continue
        meeting, digest = _read(path)
        if isinstance(meeting, Malformed):
            report.skipped.append((path.name, meeting.reason))
        else:
            notes.append((path.name, digest, meeting))
    known = [name for _, _, meeting in notes for name in meeting.attendees]
    notes.sort(key=lambda note: (note[2].date, note[0]))  # "latest" means latest Meeting Date
    for name, digest, meeting in notes:
        report.notes_read += 1
        if store.note_hash(name) == digest:
            report.notes_unchanged += 1
            continue
        for line in meeting.items:
            _ingest_line(store, people, known, name, meeting, line, report)
        store.set_note_hash(name, digest)
    report.needs_review = len(store.items(needs_review=True))
    return report


def _ingest_line(store, people, known, name, meeting, line, report) -> None:
    key = f"{line.owner or ''}\t{line.task}\t{line.due or ''}"
    source = Source(name, line.line, meeting.date, meeting.title)
    seen = store.source_item(name, key)
    if seen is not None:  # a line of a changed note that was already read: only its tick can matter
        store.refresh_source(source, key)
        if line.done:
            _mark_done(store, seen)
        return
    resolution = resolve_owners(line.owner, meeting.attendees, people, known)
    due = resolve_due(line.due, meeting.date)
    flags = list(resolution.flags)
    if line.due and due is None:
        flags.append(Flag("unresolved-due", line.due))
    match = best_match(line.task, (o.name for o in resolution.owners), store.items())
    if match and match[1] >= HIGH_SIMILARITY:
        item = match[0]
        _merge(item, resolution.owners, line, due, meeting.date, people)
        store.save_item(item)
        store.add_source(item.id, source, key)
        report.items_merged += 1
        return
    if match and match[1] >= LOW_SIMILARITY:
        flags.append(Flag("possible-duplicate", f"#{match[0].id}"))
    store.add_item(line.task, due, line.done, resolution.owners, flags, source, key)
    report.items_new += 1


def _mark_done(store: Store, item_id: int) -> None:
    item = next(i for i in store.items() if i.id == item_id)
    item.status = "done"
    store.save_item(item)


def _merge(item, owners, line, due, meeting_date, people) -> None:
    """Fold a later wording of the same Action Item into `item`: Done is sticky, the newest Due Date wins,
    and an Ambiguous group narrows to the Person the repeat names."""
    if line.done:
        item.status = "done"
    # a note read late (an older meeting added afterwards) must not override a newer Due Date
    if due is not None and all(meeting_date >= s.date for s in item.sources):
        item.due = due
        item.flags = [f for f in item.flags if f.kind != "unresolved-due"]
    elif line.due and due is None and item.due is None:
        item.flags = [f for f in item.flags if f.kind != "unresolved-due"] + [Flag("unresolved-due", line.due)]
    unconfirmed = {o.name for o in item.owners if not o.confirmed}
    named = {o.name for o in owners if o.confirmed} & unconfirmed
    if named:
        item.owners = [Owner(o.name, True) if o.name in named else o for o in item.owners if o.confirmed or o.name in named]
        if not any(not o.confirmed for o in item.owners):
            item.flags = [f for f in item.flags if f.kind != "ambiguous-owner"]
        unknown = [o.name for o in item.owners if o.name not in people]
        item.flags = [f for f in item.flags if f.kind != "unknown-owner"]
        if unknown:
            item.flags.append(Flag("unknown-owner", ", ".join(unknown)))
        item.flags.sort(key=lambda f: f.kind)


def _read(path: Path) -> Tuple[Union[Meeting, Malformed], str]:
    """The parsed note and the SHA-256 of its bytes."""
    try:
        data = path.read_bytes()
        return parse_note(data.decode("utf-8")), hashlib.sha256(data).hexdigest()
    except UnicodeDecodeError:
        return Malformed("binary or undecodable file"), ""
    except OSError as exc:
        return Malformed(f"unreadable file ({exc.strerror or exc})"), ""
