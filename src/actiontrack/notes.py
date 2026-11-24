"""Note parser: turns the text of one Meeting Note into a Meeting.

Owns the note grammar only. Owner and Due Date phrases are returned raw;
resolving them is the job of other modules.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Tuple, Union

_TITLE = re.compile(r"^#\s+(?:Meeting:\s*)?(?P<title>.+?)\s*$")
_DATE = re.compile(r"^Date:\s*(?P<value>.+?)\s*$", re.IGNORECASE)
_ATTENDEES = re.compile(r"^Attendees:\s*(?P<value>.*?)\s*$", re.IGNORECASE)
_CHECKBOX = re.compile(r"^\s*-\s*\[(?P<mark>[ xX])\]\s*(?P<text>.+?)\s*$")
_OWNER_SPLIT = re.compile(r"\s+to\s+")
# The last " by " or " before " starts the due phrase, so "sorted by date by Friday" keeps its task
# intact. "by" is dropped; "before" stays in the phrase, which the date resolver then leaves unresolved.
_DUE_SPLIT = re.compile(r"\s+(?:by\s+|(?=before\s))(?!.*\s+(?:by|before)\s)")
# An owner phrase reads like a name: capitalised words or initials ("Priya", "Priya N.").
_NAME_LIKE = re.compile(r"^[A-Z][\w'.-]*(?:\s+[A-Z][\w'.-]*)*$")


@dataclass(frozen=True)
class ItemLine:
    """An Action Item as written: owner and due phrases are still raw text."""

    owner: Optional[str]
    task: str
    due: Optional[str]
    done: bool
    line: int


@dataclass(frozen=True)
class Malformed:
    """A note that cannot be read as a Meeting: it is skipped and reported, never partly ingested."""

    reason: str


@dataclass
class Meeting:
    title: str
    date: date
    attendees: List[str] = field(default_factory=list)
    items: List[ItemLine] = field(default_factory=list)


def parse_note(text: str) -> Union[Meeting, Malformed]:
    text = text.lstrip("\ufeff")  # byte-order mark; splitlines() already copes with CRLF
    if not text.strip():
        return Malformed("empty file")
    if "\x00" in text:
        return Malformed("binary or undecodable file")
    title = ""
    meeting_date: Optional[date] = None
    attendees: List[str] = []
    items: List[ItemLine] = []

    for number, text_line in enumerate(text.splitlines(), start=1):
        if not title and (match := _TITLE.match(text_line)):
            title = match["title"]
        elif meeting_date is None and (match := _DATE.match(text_line)):
            meeting_date = _iso_date(match["value"])
        elif not attendees and (match := _ATTENDEES.match(text_line)):
            attendees = [name.strip() for name in match["value"].split(",") if name.strip()]
        elif match := _CHECKBOX.match(text_line):
            items.append(_item_line(match["text"], done=match["mark"] != " ", line=number))

    if meeting_date is None:
        return Malformed("no readable Meeting Date")
    return Meeting(title=title, date=meeting_date, attendees=attendees, items=items)


def _iso_date(value: str) -> Optional[date]:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None  # a later Date: line may still be readable


def _item_line(text: str, done: bool, line: int) -> ItemLine:
    owner, task = _split_once(_OWNER_SPLIT, text)
    if owner is None or not _NAME_LIKE.match(owner):
        owner, task = None, text
    before_due, due = _split_once(_DUE_SPLIT, task)
    if before_due is None:
        due = None
    else:
        task = before_due.rstrip(" \t,;:-\u2013\u2014")
    return ItemLine(owner=owner, task=task, due=due, done=done, line=line)


def _split_once(pattern: re.Pattern, text: str) -> Tuple[Optional[str], str]:
    """(head, tail) around the first match of pattern, or (None, text) when it doesn't match."""
    parts = pattern.split(text, maxsplit=1)
    return (parts[0], parts[1]) if len(parts) == 2 else (None, text)
