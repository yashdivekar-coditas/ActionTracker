"""Store: SQLite persistence for Action Items, their Owners and review Flags."""
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Iterable, List, Optional

from actiontrack.model import ActionItem, Flag, Owner, Source

_SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,  -- merged-away ids are never reused
    task   TEXT NOT NULL,
    due    TEXT,
    status TEXT NOT NULL CHECK (status IN ('open', 'done'))
);
CREATE TABLE IF NOT EXISTS item_owners (
    item_id   INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    name      TEXT NOT NULL,
    confirmed INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (item_id, name)
);
CREATE TABLE IF NOT EXISTS flags (
    item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    kind    TEXT NOT NULL,
    detail  TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (item_id, kind)
);
-- `key` identifies the line as written (owner, task, due phrase), so re-reading a note adds nothing twice
CREATE TABLE IF NOT EXISTS sources (
    item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    note    TEXT NOT NULL,
    key     TEXT NOT NULL,
    line    INTEGER NOT NULL,
    date    TEXT NOT NULL,
    title   TEXT NOT NULL,
    PRIMARY KEY (note, key)
);
-- durable record of human decisions, consulted by ingest
CREATE TABLE IF NOT EXISTS edits (
    item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    field   TEXT NOT NULL,
    PRIMARY KEY (item_id, field)
);
CREATE TABLE IF NOT EXISTS aliases (
    item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    task    TEXT NOT NULL,
    PRIMARY KEY (item_id, task)
);
CREATE TABLE IF NOT EXISTS notes (
    name TEXT PRIMARY KEY,
    hash TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: Path):
        self._db = sqlite3.connect(path)
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.executescript(_SCHEMA)

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, exc_type, *_) -> None:
        if exc_type is None:
            self._db.commit()
        self._db.close()

    def add_item(
        self,
        task: str,
        due: Optional[date],
        done: bool,
        owners: Iterable[Owner],
        flags: Iterable[Flag],
        source: Source,
        key: str,
    ) -> int:
        cur = self._db.execute(
            "INSERT INTO items (task, due, status) VALUES (?, ?, ?)",
            (task, due.isoformat() if due else None, "done" if done else "open"),
        )
        item_id = cur.lastrowid
        self._db.executemany(
            "INSERT INTO item_owners (item_id, name, confirmed) VALUES (?, ?, ?)",
            [(item_id, o.name, int(o.confirmed)) for o in owners],
        )
        self._db.executemany(
            "INSERT OR REPLACE INTO flags (item_id, kind, detail) VALUES (?, ?, ?)",
            [(item_id, f.kind, f.detail) for f in flags],
        )
        self.add_source(item_id, source, key)
        return item_id

    def add_source(self, item_id: int, source: Source, key: str) -> None:
        self._db.execute(
            "INSERT INTO sources (item_id, note, key, line, date, title) VALUES (?, ?, ?, ?, ?, ?)",
            (item_id, source.note, key, source.line, source.date.isoformat(), source.title),
        )

    def source_item(self, note: str, key: str) -> Optional[int]:
        """The item a line of a note already belongs to, or None when the line is new."""
        row = self._db.execute("SELECT item_id FROM sources WHERE note = ? AND key = ?", (note, key)).fetchone()
        return row[0] if row else None

    def refresh_source(self, source: Source, key: str) -> None:
        self._db.execute(
            "UPDATE sources SET line = ?, date = ?, title = ? WHERE note = ? AND key = ?",
            (source.line, source.date.isoformat(), source.title, source.note, key),
        )

    def save_item(self, item: ActionItem) -> None:
        """Write back an item's task, due date, status, owners and flags (its Sources are not touched)."""
        self._db.execute(
            "UPDATE items SET task = ?, due = ?, status = ? WHERE id = ?",
            (item.task, item.due.isoformat() if item.due else None, item.status, item.id),
        )
        self._db.execute("DELETE FROM item_owners WHERE item_id = ?", (item.id,))
        self._db.execute("DELETE FROM flags WHERE item_id = ?", (item.id,))
        self._db.executemany(
            "INSERT INTO item_owners (item_id, name, confirmed) VALUES (?, ?, ?)",
            [(item.id, o.name, int(o.confirmed)) for o in item.owners],
        )
        self._db.executemany(
            "INSERT INTO flags (item_id, kind, detail) VALUES (?, ?, ?)",
            [(item.id, f.kind, f.detail) for f in item.flags],
        )

    def record_edit(self, item_id: int, field: str) -> None:
        self._db.execute("INSERT OR IGNORE INTO edits (item_id, field) VALUES (?, ?)", (item_id, field))

    def add_alias(self, item_id: int, task: str) -> None:
        self._db.execute("INSERT OR IGNORE INTO aliases (item_id, task) VALUES (?, ?)", (item_id, task))

    def get(self, item_id: int) -> Optional[ActionItem]:
        return next((i for i in self._all_items(False) if i.id == item_id), None)

    def merge_items(self, gone: ActionItem, into: ActionItem) -> None:
        """Move `gone`'s Sources and wordings onto `into`, delete `gone`, and drop possible-duplicate flags
        between the two (flags other items held against `gone` now point at `into`)."""
        self._db.execute("UPDATE sources SET item_id = ? WHERE item_id = ?", (into.id, gone.id))
        for task in [gone.task] + gone.aliases:
            if task != into.task:
                self.add_alias(into.id, task)
        self._db.execute("DELETE FROM items WHERE id = ?", (gone.id,))
        self._db.execute(
            "DELETE FROM flags WHERE kind = 'possible-duplicate' AND ((item_id = ? AND detail = ?) OR (item_id = ? AND detail = ?))",
            (into.id, f"#{gone.id}", into.id, f"#{into.id}"),
        )
        self._db.execute(
            "UPDATE OR IGNORE flags SET detail = ? WHERE kind = 'possible-duplicate' AND detail = ?",
            (f"#{into.id}", f"#{gone.id}"),
        )

    def note_hash(self, name: str) -> Optional[str]:
        row = self._db.execute("SELECT hash FROM notes WHERE name = ?", (name,)).fetchone()
        return row[0] if row else None

    def set_note_hash(self, name: str, digest: str) -> None:
        self._db.execute("INSERT OR REPLACE INTO notes (name, hash) VALUES (?, ?)", (name, digest))

    def items(
        self,
        needs_review: bool = False,
        owner: Optional[str] = None,
        status: Optional[str] = None,
        due_before: Optional[date] = None,
        today: Optional[date] = None,
    ) -> List[ActionItem]:
        """Items matching every given filter; Overdue (open, due before today) is derived here, never stored."""
        today = today or date.today()
        return [
            item
            for item in self._all_items(needs_review)
            if (not needs_review or item.status == "open")  # Done items need no review
            and (owner is None or _owned_by(item, owner))
            and (status is None or _has_status(item, status, today))
            and (due_before is None or (item.due is not None and item.due < due_before))
        ]

    def _all_items(self, needs_review: bool) -> List[ActionItem]:
        sql = "SELECT id, task, due, status FROM items"
        if needs_review:
            sql += " WHERE id IN (SELECT item_id FROM flags)"
        items = {
            row[0]: ActionItem(row[0], row[1], date.fromisoformat(row[2]) if row[2] else None, row[3])
            for row in self._db.execute(sql + " ORDER BY id")
        }
        for item_id, name, confirmed in self._db.execute(
            "SELECT item_id, name, confirmed FROM item_owners ORDER BY rowid"
        ):
            if item_id in items:
                items[item_id].owners.append(Owner(name, bool(confirmed)))
        for item_id, kind, detail in self._db.execute(
            "SELECT item_id, kind, detail FROM flags ORDER BY kind"
        ):
            if item_id in items:
                items[item_id].flags.append(Flag(kind, detail))
        for item_id, note, line, day, title in self._db.execute(
            "SELECT item_id, note, line, date, title FROM sources ORDER BY date, note, line"
        ):
            if item_id in items:
                items[item_id].sources.append(Source(note, line, date.fromisoformat(day), title))
        for item_id, field in self._db.execute("SELECT item_id, field FROM edits ORDER BY field"):
            if item_id in items:
                items[item_id].edited.append(field)
        for item_id, task in self._db.execute("SELECT item_id, task FROM aliases ORDER BY rowid"):
            if item_id in items:
                items[item_id].aliases.append(task)
        return list(items.values())


def _has_status(item: ActionItem, wanted: str, today: date) -> bool:
    if wanted == "overdue":  # open items past their Due Date; "open" still includes them
        return item.status == "open" and item.due is not None and item.due < today
    return item.status == wanted


def _owned_by(item: ActionItem, wanted: str) -> bool:
    """'none' matches Unowned; otherwise any Owner matching `wanted` (see matches_name)."""
    if wanted.strip().casefold() == "none":
        return not item.owners
    return any(matches_name(o.name, wanted) for o in item.owners)


def matches_name(name: str, wanted: str) -> bool:
    """A first name matches every person with it; a full name matches exactly."""
    wanted = wanted.strip().casefold()
    name = name.casefold()
    return name == wanted if " " in wanted else name.split()[:1] == [wanted]
