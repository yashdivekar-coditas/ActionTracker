"""Domain types shared across modules (see GLOSSARY.md)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass(frozen=True)
class Owner:
    name: str
    confirmed: bool = True


@dataclass(frozen=True)
class Flag:
    """Why an Action Item Needs Review."""

    kind: str
    detail: str = ""

    def __str__(self) -> str:
        return f"{self.kind}: {self.detail}" if self.detail else self.kind


@dataclass(frozen=True)
class Source:
    """A Meeting Note an Action Item was seen in; `note` is the file name inside the ingested folder."""

    note: str
    line: int
    date: date
    title: str = ""

    def __str__(self) -> str:  # the label Follow-ups show, e.g. "Quote portal weekly, 2026-09-08"
        return f"{self.title or self.note}, {self.date.isoformat()}"


@dataclass
class ActionItem:
    id: int
    task: str
    due: Optional[date]
    status: str
    owners: List[Owner] = field(default_factory=list)
    flags: List[Flag] = field(default_factory=list)
    sources: List[Source] = field(default_factory=list)
    edited: List[str] = field(default_factory=list)  # fields a human set (owner, due, task); ingest leaves them alone
    aliases: List[str] = field(default_factory=list)  # earlier wordings (merged-away or pre-edit) that still match this item

    def is_overdue(self, today: date) -> bool:
        """Overdue is derived, never stored: Open and due before today."""
        return self.status == "open" and self.due is not None and self.due < today
