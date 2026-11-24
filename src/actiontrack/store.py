"""Store: SQLite persistence for Action Items, their Owners and review Flags."""
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Iterable, List, Optional

from actiontrack.model import ActionItem, Flag, Owner

_SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id     INTEGER PRIMARY KEY,
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
        return item_id

    def items(self, needs_review: bool = False) -> List[ActionItem]:
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
        return list(items.values())
