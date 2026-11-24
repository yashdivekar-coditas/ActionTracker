"""Owner resolver: turns a raw owner phrase into Owners (ADR-0003), using the meeting's attendees and the people directory."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional

from actiontrack.model import Flag, Owner

# Fixed word lists, in one place. Compared case-insensitively.
GROUP_WORDS = frozenset({"everyone", "team", "all"})
NOBODY_WORDS = frozenset({"someone", "tbd", "tba", "anyone"})

_HELPERS = re.compile(r"\s*\([^)]*\)")  # "Lena (with Priya)": the helper is not an owner
_JOINERS = re.compile(r"\s*&\s*|\s+and\s+", re.IGNORECASE)


@dataclass(frozen=True)
class Resolution:
    owners: List[Owner] = field(default_factory=list)
    flags: List[Flag] = field(default_factory=list)


def resolve_owners(
    phrase: Optional[str],
    attendees: Iterable[str],
    people: Mapping[str, str],
    known: Iterable[str] = (),
) -> Resolution:
    """`known` is everyone seen in any note; it is consulted only when this note lists no attendees."""
    attendees = list(attendees)
    candidates = attendees or list(dict.fromkeys([*people, *known]))
    owners: Dict[str, Owner] = {}
    flags: List[Flag] = []
    for part in _JOINERS.split(_HELPERS.sub("", phrase or "")):
        word = part.strip().casefold()
        if not word or word in NOBODY_WORDS:
            continue
        if word in GROUP_WORDS:
            matches = attendees
        else:
            matches = _matching(part.strip(), candidates)
            if not matches:  # nobody matches: keep the name as written
                matches = [part.strip()]
            elif len(matches) > 1:
                flags.append(Flag("ambiguous-owner", part.strip()))
        confirmed = len(matches) == 1 or word in GROUP_WORDS
        for name in matches:
            owners.setdefault(name, Owner(name, confirmed))
    if not owners:
        flags.append(Flag("unowned"))
    unknown = [name for name in owners if name not in people]
    if unknown:
        flags.append(Flag("unknown-owner", ", ".join(unknown)))
    return Resolution(owners=list(owners.values()), flags=flags)


def _matching(phrase: str, names: Iterable[str]) -> List[str]:
    """Names whose first name equals the phrase's first word and whose later words start with the rest
    ("Priya" -> every Priya, "Priya N." -> Priya Nair)."""
    wanted = phrase.casefold().replace(".", "").split()
    return [
        name
        for name in names
        if (have := name.casefold().split())[:1] == wanted[:1]
        and len(wanted) <= len(have)
        and all(w and h.startswith(w) for w, h in zip(wanted[1:], have[1:]))
    ]
