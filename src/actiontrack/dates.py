"""Date resolver: turns a raw due phrase into a real date, relative to the Meeting Date."""
from __future__ import annotations

from datetime import date
from typing import Optional


def resolve_due(phrase: Optional[str], meeting_date: date) -> Optional[date]:
    if not phrase:
        return None
    try:
        return date.fromisoformat(phrase.strip())
    except ValueError:
        return None
