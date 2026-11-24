"""Follow-up composer and Draft sinks: one plain-text email per Owner, saved as Drafts (never sent)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, List, Mapping, Optional, Tuple

from actiontrack.model import ActionItem
from actiontrack.store import matches_name

CONFIRM_HEADING = "Can you confirm whether this is yours?"


class DraftError(Exception):
    """A sink could not save a Draft; the CLI reports it and exits 1."""


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    body: str  # plain text only: Gmail's create_draft rejects markdown (no #, **, tables)


class DraftSink:
    """Where composed Follow-ups go. The Claude/Gmail adapter (ticket 10) implements this."""

    def create_draft(self, email: Email) -> str:
        raise NotImplementedError


class PrintSink(DraftSink):
    """Saves nothing; stands in until the Claude adapter exists."""

    def create_draft(self, email: Email) -> str:
        print(f"(printed only, not saved) draft for {email.to}")
        return "printed"


def format_email(email: Email) -> str:
    return f"To: {email.to}\nSubject: {email.subject}\n\n{email.body}"


def _sources(item: ActionItem) -> List[str]:
    """Source meetings of an item. Ticket 06 stores Sources; return their labels here."""
    return [str(source) for source in getattr(item, "sources", [])]


def _line(item: ActionItem) -> str:
    due = f"due {item.due.isoformat()}" if item.due else "no due date"
    sources = _sources(item)
    detail = f"{due}; from {', '.join(sources)}" if sources else due
    return f"- {item.task} ({detail})"


def compose(owner: str, to: str, items: Iterable[ActionItem], today: date) -> Optional[Email]:
    """The Follow-up for one Owner, or None when none of their items is Open."""
    overdue, open_, confirm = [], [], []
    for item in items:
        if item.status != "open":
            continue
        mine = [o for o in item.owners if o.name == owner]
        if not mine:
            continue
        if not mine[0].confirmed:
            confirm.append(item)
        elif item.due is not None and item.due < today:
            overdue.append(item)
        else:
            open_.append(item)
    counts = [(len(overdue), "overdue"), (len(open_), "open"), (len(confirm), "to confirm")]
    if not any(n for n, _ in counts):
        return None
    sections = [
        (f"Overdue ({len(overdue)})", overdue),
        (f"Open ({len(open_)})", open_),
        (CONFIRM_HEADING, confirm),
    ]
    parts = [f"Hi {owner.split()[0]},", "Here is where your action items stand."]
    parts += ["\n".join([title] + [_line(i) for i in group]) for title, group in sections if group]
    parts.append("Thanks")
    subject = "Follow-up: " + ", ".join(f"{n} {label}" for n, label in counts if n)
    return Email(to=to, subject=subject, body="\n\n".join(parts) + "\n")


def compose_all(
    items: List[ActionItem], people: Mapping[str, str], today: date, only: Optional[str] = None
) -> Tuple[List[Email], List[str]]:
    """(emails, owners skipped for lack of an email address), both ordered by owner name."""
    names = sorted({o.name for i in items if i.status == "open" for o in i.owners})
    emails, skipped = [], []
    for name in names:
        if only is not None and not matches_name(name, only):
            continue
        email = compose(name, people.get(name, ""), items, today)
        if email is None:
            continue
        if name in people:
            emails.append(email)
        else:
            skipped.append(name)
    return emails, skipped
