"""Duplicate matcher (ADR-0002): is a new task wording the same Action Item as an existing one?"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable, Optional, Tuple

from actiontrack.model import ActionItem

# Similarity of normalized task text, 0..1. At or above HIGH two items merge automatically; from LOW up
# to (not including) HIGH they stay separate and the newer is flagged as a possible duplicate.
HIGH_SIMILARITY = 0.85
LOW_SIMILARITY = 0.6

# Words that carry no meaning for matching; compared case-insensitively.
FILLER_WORDS = frozenset({"a", "an", "the", "to", "please", "just", "also", "then", "and"})


def normalize(task: str) -> str:
    """Lowercase, punctuation and filler words removed."""
    words = re.sub(r"[\W_]+", " ", task.casefold()).split()
    return " ".join(word for word in words if word not in FILLER_WORDS)


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def best_match(
    task: str, owner_names: Iterable[str], items: Iterable[ActionItem]
) -> Optional[Tuple[ActionItem, float]]:
    """The most similar item sharing an Owner (or an Ambiguous candidate) with the new line, with its score.
    Unowned items only match other Unowned ones."""
    owners = set(owner_names)
    best: Optional[Tuple[ActionItem, float]] = None
    for item in items:
        theirs = {o.name for o in item.owners}
        if (owners & theirs) or not (owners or theirs):
            score = max(similarity(task, wording) for wording in [item.task] + item.aliases)
            if best is None or score > best[1]:
                best = (item, score)
    return best
