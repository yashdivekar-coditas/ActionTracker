"""Note parser: turns the text of one Meeting Note into a Meeting.

Owns the note grammar only. Owner and Due Date phrases are returned raw;
resolving them is the job of other modules.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

_TITLE = re.compile(r"^#\s+(?:Meeting:\s*)?(?P<title>.+?)\s*$")
_DATE = re.compile(r"^Date:\s*(?P<value>.+?)\s*$", re.IGNORECASE)
_ATTENDEES = re.compile(r"^Attendees:\s*(?P<value>.*?)\s*$", re.IGNORECASE)
_CHECKBOX = re.compile(r"^\s*-\s*\[(?P<mark>[ xX])\]\s*(?P<text>.+?)\s*$")
_OWNER_SPLIT = re.compile(r"\s+to\s+")
_DUE_SPLIT = re.compile(r"\s+by\s+(?!.*\s+by\s+)")


@dataclass(frozen=True)
class ItemLine:
    """An Action Item as written: owner and due phrases are still raw text."""

    owner: Optional[str]
    task: str
    due: Optional[str]
    done: bool
    line: int


@dataclass
class Meeting:
    title: str
    date: date
    attendees: List[str] = field(default_factory=list)
    items: List[ItemLine] = field(default_factory=list)


def parse_note(text: str) -> Meeting:
    title = ""
    meeting_date: Optional[date] = None
    attendees: List[str] = []
    items: List[ItemLine] = []

    for number, line in enumerate(text.splitlines(), start=1):
        if not title and (m := _TITLE.match(line)):
            title = m["title"]
        elif meeting_date is None and (m := _DATE.match(line)):
            meeting_date = date.fromisoformat(m["value"])
        elif not attendees and (m := _ATTENDEES.match(line)):
            attendees = [name.strip() for name in m["value"].split(",") if name.strip()]
        elif m := _CHECKBOX.match(line):
            items.append(_item_line(m["text"], done=m["mark"] != " ", line=number))

    return Meeting(title=title, date=meeting_date, attendees=attendees, items=items)


def _item_line(text: str, done: bool, line: int) -> ItemLine:
    owner, task = None, text
    parts = _OWNER_SPLIT.split(text, maxsplit=1)
    if len(parts) == 2:
        owner, task = parts
    due = None
    parts = _DUE_SPLIT.split(task, maxsplit=1)
    if len(parts) == 2:
        task, due = parts
    return ItemLine(owner=owner, task=task, due=due, done=done, line=line)
