from __future__ import annotations

import json
from pathlib import Path

import pytest

from actiontrack.cli import main

KICKOFF = """\
# Meeting: Quote portal kickoff
Date: 2026-09-01
Attendees: Priya Nair, Rahul Mehta

## Action items
- [ ] Priya to send the revised quote to Acme by 2026-09-08
- [x] Rahul to set up the staging environment
"""

EVERYONE = {"Priya Nair": "priya@example.com", "Rahul Mehta": "rahul@example.com"}


class Workspace:
    """A notes folder, people directory and database in a temp dir, driven through the CLI."""

    def __init__(self, root: Path, capsys):
        self.notes = root / "notes"
        self.notes.mkdir()
        self.people = root / "people.json"
        self.db = root / "actiontrack.db"
        self._capsys = capsys

    def note(self, name: str, text: str) -> None:
        (self.notes / name).write_text(text, encoding="utf-8")

    def directory(self, people: dict) -> None:
        self.people.write_text(json.dumps(people), encoding="utf-8")

    def run(self, *args: str) -> tuple:
        self._capsys.readouterr()
        code = main([*args, "--db", str(self.db), "--people", str(self.people)])
        out, err = self._capsys.readouterr()
        return code, out, err

    def ingest(self) -> tuple:
        return self.run("ingest", str(self.notes))


@pytest.fixture
def ws(tmp_path, capsys):
    return Workspace(tmp_path, capsys)


def test_ingest_then_list_shows_each_action_item_with_its_owner_and_due_date(ws):
    ws.directory(EVERYONE)
    ws.note("kickoff.md", KICKOFF)

    assert ws.ingest()[0] == 0
    code, out, _ = ws.run("list")

    assert code == 0
    assert out.splitlines() == [
        "ID  STATUS  DUE         OWNER        TASK",
        "1   open    2026-09-08  Priya Nair   send the revised quote to Acme",
        "2   done    -           Rahul Mehta  set up the staging environment",
    ]


def test_owner_missing_from_people_directory_is_flagged_for_review(ws):
    ws.directory({"Priya Nair": "priya@example.com"})
    ws.note("kickoff.md", KICKOFF)

    code, out, _ = ws.ingest()
    assert code == 0
    assert out.strip() == "1 notes read, 2 new items, 1 need review"

    code, out, _ = ws.run("list", "--needs-review")
    assert code == 0
    assert out.splitlines() == [
        "ID  STATUS  DUE  OWNER        TASK                            REVIEW",
        "2   done    -    Rahul Mehta  set up the staging environment  unknown-owner: Rahul Mehta",
    ]


def test_unreadable_people_directory_is_a_clear_error(ws):
    ws.people.write_text('["not", "a", "mapping"]', encoding="utf-8")
    ws.note("kickoff.md", KICKOFF)

    code, _, err = ws.ingest()

    assert code == 1
    assert "must map full names to email addresses" in err
