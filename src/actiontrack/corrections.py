"""Human corrections (ADR-0002/0003): done, edit and merge. Each is recorded in the Store so ingest never undoes it."""
from __future__ import annotations

from datetime import date
from typing import Mapping, Optional, Sequence

from actiontrack.model import AMBIGUOUS_OWNER, UNKNOWN_OWNER, UNOWNED, UNRESOLVED_DUE, ActionItem, Flag, Owner
from actiontrack.store import Store

# the review flags each corrected field settles
_CLEARS = {"owner": {AMBIGUOUS_OWNER, UNKNOWN_OWNER, UNOWNED}, "due": {UNRESOLVED_DUE}}


class CorrectionError(Exception):
    """An id that does not exist or a correction that makes no sense; the CLI exits 1 with the message."""


class UsageError(CorrectionError):
    """Nothing to correct was asked for; the CLI exits 2."""


def _get(store: Store, item_id: int) -> ActionItem:
    item = store.get(item_id)
    if item is None:
        raise CorrectionError(f"no item with id {item_id}")
    return item


def mark_done(store: Store, item_id: int) -> ActionItem:
    item = _get(store, item_id)
    item.status = "done"
    store.save_item(item)
    return item


def edit_item(
    store: Store,
    item_id: int,
    owners: Sequence[str] = (),
    due: Optional[date] = None,
    task: Optional[str] = None,
    people: Mapping[str, str] = {},
) -> ActionItem:
    item = _get(store, item_id)
    if not (owners or due or task is not None):
        raise UsageError("edit needs --owner, --due or --task")
    names = [n.strip() for n in owners]
    if any(not n for n in names) or (task is not None and not task.strip()):
        raise CorrectionError("owner and task must not be empty")
    if names:
        item.owners = [Owner(n, True) for n in dict.fromkeys(names)]
    if due is not None:
        item.due = due
    if task is not None and task.strip() != item.task:
        store.add_alias(item.id, item.task)  # the old wording keeps matching later notes
        item.task = task.strip()
    changed = [f for f, v in (("owner", names), ("due", due), ("task", task)) if v not in ((), None)]
    for field in changed:
        store.record_edit(item.id, field)
        item.flags = [f for f in item.flags if f.kind not in _CLEARS.get(field, ())]
    unknown = [n for n in dict.fromkeys(names) if n not in people]
    if unknown:  # a corrected Owner still has to be someone in the people directory
        item.flags = sorted(item.flags + [Flag(UNKNOWN_OWNER, ", ".join(unknown))], key=lambda f: f.kind)
    store.save_item(item)
    return item


def merge_items(store: Store, gone_id: int, into_id: int) -> ActionItem:
    """Fold `gone_id` into `into_id`: Sources combine, Done if either was, possible-duplicate flags clear."""
    if gone_id == into_id:
        raise CorrectionError("cannot merge an item into itself")
    gone, into = _get(store, gone_id), _get(store, into_id)
    if "done" in (gone.status, into.status):
        into.status = "done"
    store.save_item(into)
    store.merge_items(gone, into)
    return _get(store, into_id)
