"""Owner resolver: turns a raw owner phrase into Owners, using the meeting's attendees and the people directory."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Mapping, Optional

from actiontrack.model import Flag, Owner


@dataclass(frozen=True)
class Resolution:
    owners: List[Owner] = field(default_factory=list)
    flags: List[Flag] = field(default_factory=list)


def resolve_owners(
    phrase: Optional[str], attendees: Iterable[str], people: Mapping[str, str]
) -> Resolution:
    if not phrase:
        return Resolution()
    name = _unique_name_match(phrase, attendees) or _unique_name_match(phrase, people) or phrase.strip()
    flags = [] if name in people else [Flag("unknown-owner", name)]
    return Resolution(owners=[Owner(name)], flags=flags)


def _unique_name_match(phrase: str, names: Iterable[str]) -> Optional[str]:
    wanted = phrase.strip().casefold()
    matches = [n for n in names if wanted == n.casefold() or n.casefold().split()[:1] == [wanted]]
    return matches[0] if len(matches) == 1 else None
