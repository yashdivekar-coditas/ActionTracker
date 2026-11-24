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


@dataclass
class ActionItem:
    id: int
    task: str
    due: Optional[date]
    status: str
    owners: List[Owner] = field(default_factory=list)
    flags: List[Flag] = field(default_factory=list)
