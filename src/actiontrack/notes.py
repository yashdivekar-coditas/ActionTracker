"""Note parser: turns the text of one Meeting Note into a Meeting.

Owns the note grammar only. Owner and Due Date phrases are returned raw;
resolving them is the job of other modules.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Tuple, Union

from actiontrack.dates import parse_date, resolve_due

_TITLE = re.compile(r"^#\s+(?:Meeting:\s*)?(?P<title>.+?)\s*$")
# `Date:`, `**Date:**` and `**Date**:` headers.
_DATE = re.compile(r"^\s*(?:\*\*)?Date(?::\*\*|\*\*:|:)\s*(?P<value>.+?)\s*$", re.IGNORECASE)
_ATTENDEES = re.compile(r"^\s*(?:\*\*)?Attendees(?::\*\*|\*\*:|:)\s*(?P<value>.*?)\s*$", re.IGNORECASE)
_CHECKBOX = re.compile(r"^\s*[-*+]\s*\[(?P<mark>[ xX])\]\s*(?P<text>.+?)\s*$")
_ACTION_LINE = re.compile(r"^\s*(?:[-*+]\s+)?(?:ACTION|TODO):\s*(?P<text>.+?)\s*$")
_FENCE = re.compile(r"^\s*(?:```|~~~)")
_COMMENT = re.compile(r"<!--.*?-->")
_SEPARATOR_CELL = re.compile(r"^:?-+:?$")
_OWNER_SPLIT = re.compile(r"\s+to\s+")
# The last " by " or " before " starts the due phrase, so "sorted by date by Friday" keeps its task
# intact. "by" is dropped; "before" stays in the phrase, which the date resolver then leaves unresolved.
_DUE_SPLIT = re.compile(r"\s+(?:by\s+|(?=before\s))(?!.*\s+(?:by|before)\s)")
# Markers that start a due phrase only when what follows resolves to a date: "schedule it for Saturday 10 Oct",
# but "send the invoice for finance" keeps "for finance". "results due" and "due by/on" are tried as one marker.
_DUE_MARKER = re.compile(r"\s+(?:results\s+)?(?:due(?:\s+(?:by|on))?|for|on)\s+", re.IGNORECASE)
_TRAILING_WORDS = 5  # longest bare due phrase tried at the end of a task ("end of next week")
# shortcut: resolvability is checked against a fixed leap-year date, so a yearless 29 Feb counts as a date; revisit if that bites.
_PROBE = date(2024, 1, 1)
# An owner phrase reads like names: capitalised words or initials ("Priya", "Priya N."), joined by
# "&" or "and", with an optional "(with ...)" helper: "Anita & Rahul", "Lena (with Priya)".
_NAME = r"[A-Z][\w'.-]*(?:\s+[A-Z][\w'.-]*)*"
_NAME_LIKE = re.compile(rf"^{_NAME}(?:\s+(?:&|and)\s+{_NAME})*(?:\s*\(with\s+[^)]+\))?$")
# "Anita: task" and "@anita: task"
_COLON_OWNER = re.compile(rf"^(?:@(?P<handle>\w+)|(?P<name>{_NAME})):\s+(?P<task>.+)$")


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
    lines = _strip_decoys(text.splitlines())
    front, body_start = _frontmatter(lines)
    title = front.get("title", "")
    meeting_date: Optional[date] = _parse_date(front["date"]) if "date" in front else None
    attendees: List[str] = front.get("attendees", [])
    items: List[ItemLine] = []
    columns: Optional[dict] = None  # column positions of the table being read, if it holds items

    for number, text_line in enumerate(lines, start=1):
        if number <= body_start:
            continue
        if text_line.lstrip().startswith("|"):
            cells = _cells(text_line)
            if columns is None:
                columns = _table_columns(cells)
            elif not all(_SEPARATOR_CELL.match(cell) for cell in cells if cell) and (item := _table_item(cells, columns, number)):
                items.append(item)
            continue
        columns = None
        if not title and (match := _TITLE.match(text_line)):
            title = match["title"]
        elif meeting_date is None and (match := _DATE.match(text_line)):
            meeting_date = _parse_date(match["value"])
        elif not attendees and (match := _ATTENDEES.match(text_line)):
            attendees = _names(match["value"])
        elif match := _CHECKBOX.match(text_line):
            items.append(_item_line(match["text"], done=match["mark"] != " ", line=number))
        elif match := _ACTION_LINE.match(text_line):
            items.append(_item_line(match["text"], done=False, line=number))

    if meeting_date is None:
        return Malformed("no readable Meeting Date")
    return Meeting(title=title, date=meeting_date, attendees=attendees, items=items)


def _strip_decoys(lines: List[str]) -> List[str]:
    """Blank out blockquotes, fenced code and HTML comments, keeping line numbers stable."""
    out: List[str] = []
    fence = comment = False
    for line in lines:
        if fence:
            fence = not _FENCE.match(line)
            out.append("")
            continue
        if comment:
            end = line.find("-->")
            comment = end < 0
            line = "" if comment else line[end + 3:]
        elif _FENCE.match(line):
            fence = True
            out.append("")
            continue
        line = _COMMENT.sub("", line)
        if "<!--" in line:
            line, comment = line[: line.index("<!--")], True
        out.append("" if line.lstrip().startswith(">") else line)
    return out


def _frontmatter(lines: List[str]) -> Tuple[dict, int]:
    """(fields, number of lines used): YAML frontmatter with `date`, `title` and `attendees` (inline or list)."""
    if not lines or lines[0].strip() != "---":
        return {}, 0
    end = next((n for n in range(1, len(lines)) if lines[n].strip() in ("---", "...")), None)
    if end is None:
        return {}, 0
    fields: dict = {}
    key = ""
    for line in lines[1:end]:
        if match := re.match(r"^(\w+):\s*(.*?)\s*$", line):
            key, value = match[1].lower(), match[2].strip("\"'")
            if key == "attendees":
                fields[key] = _names(value.strip("[]"))
            elif value:
                fields[key] = value
        elif key == "attendees" and (match := re.match(r"^\s*-\s+(.+?)\s*$", line)):
            fields[key].append(match[1].strip("\"'"))
    return fields, end + 1


def _names(value: str) -> List[str]:
    return [name.strip().strip("\"'") for name in value.split(",") if name.strip()]


def _parse_date(value: str) -> Optional[date]:
    return parse_date(value.strip().strip("\"'"))


def _cells(line: str) -> List[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _table_columns(cells: List[str]) -> Optional[dict]:
    """Column positions of a header row naming an Owner and an Action/Task column (Due optional)."""
    names = [cell.lower() for cell in cells]
    find = lambda *words: next((n for n, name in enumerate(names) if name.startswith(words)), None)
    owner, task, due = find("owner"), find("action", "task"), find("due")
    return None if owner is None or task is None else {"owner": owner, "task": task, "due": due}


def _table_item(cells: List[str], columns: Optional[dict], line: int) -> Optional[ItemLine]:
    if columns is None:
        return None
    cell = lambda key: cells[columns[key]] if columns[key] is not None and columns[key] < len(cells) else ""
    if not cell("task"):
        return None
    return ItemLine(owner=cell("owner") or None, task=cell("task"), due=cell("due") or None, done=False, line=line)


def _item_line(text: str, done: bool, line: int) -> ItemLine:
    if match := _COLON_OWNER.match(text):
        owner, task = match["handle"] or match["name"], match["task"]
    else:
        owner, task = _split_once(_OWNER_SPLIT, text)
        if owner is None or not _NAME_LIKE.match(owner):
            owner, task = None, text
    task, due = _split_due(task)
    return ItemLine(owner=owner, task=task, due=due, done=done, line=line)


def _split_due(task: str) -> Tuple[str, Optional[str]]:
    """(task, raw due phrase). A marker that resolves wins; then by/before, whose phrase is kept even when
    unresolved (it gets flagged); then a bare date phrase ending the task ("fix build, EOD")."""
    for marker in _DUE_MARKER.finditer(task):
        if resolve_due(task[marker.end():], _PROBE):
            return _trim(task[: marker.start()]), task[marker.end():]
    head, due = _split_once(_DUE_SPLIT, task)
    if head is not None:
        return _trim(head), due
    words = task.split()
    for size in range(min(_TRAILING_WORDS, len(words) - 1), 0, -1):
        phrase = " ".join(words[-size:])
        if resolve_due(phrase, _PROBE):
            return _trim(" ".join(words[:-size])), phrase
    return task, None


def _trim(task: str) -> str:
    return task.rstrip(" \t,;:-\u2013\u2014")


def _split_once(pattern: re.Pattern, text: str) -> Tuple[Optional[str], str]:
    """(head, tail) around the first match of pattern, or (None, text) when it doesn't match."""
    parts = pattern.split(text, maxsplit=1)
    return (parts[0], parts[1]) if len(parts) == 2 else (None, text)
