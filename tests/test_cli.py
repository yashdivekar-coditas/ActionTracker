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

    def raw_note(self, name: str, data: bytes) -> None:
        (self.notes / name).write_bytes(data)

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
    assert out.strip() == "1 notes read, 0 skipped, 2 new items, 0 merged, 1 need review"

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


def test_malformed_notes_are_skipped_with_distinct_reasons_and_the_rest_still_ingest(ws):
    ws.directory(EVERYONE)
    ws.note("kickoff.md", KICKOFF)
    ws.raw_note("empty.md", b"")
    ws.raw_note("binary.md", b"\x00\x01\x02Date: 2026-09-01\n- [ ] Priya to x\n")
    ws.raw_note("latin1.md", b"Date: 2026-09-01\n- [ ] Priya to caf\xe9\n")
    ws.note("nodate.md", "# Meeting: Standup\n- [ ] Priya to send the quote\n")
    ws.note("baddate.md", "Date: next Tuesday\n- [ ] Priya to send the quote\n")

    code, out, err = ws.ingest()

    assert code == 0
    assert sorted(err.splitlines()) == [
        "skipped baddate.md: no readable Meeting Date",
        "skipped binary.md: binary or undecodable file",
        "skipped empty.md: empty file",
        "skipped latin1.md: binary or undecodable file",
        "skipped nodate.md: no readable Meeting Date",
    ]
    assert out.strip() == "1 notes read, 5 skipped, 2 new items, 0 merged, 0 need review"
    assert len(ws.run("list")[1].splitlines()) == 3  # header + the two kickoff items


def test_non_markdown_files_are_ignored_and_not_reported(ws):
    ws.directory(EVERYONE)
    ws.note("kickoff.md", KICKOFF)
    ws.note("draft.txt", KICKOFF)
    ws.raw_note("photo.png", b"\x89PNG\x00")
    (ws.notes / "folder.md").mkdir()

    code, out, err = ws.ingest()

    assert (code, err) == (0, "")
    assert out.strip() == "1 notes read, 0 skipped, 2 new items, 0 merged, 0 need review"


def test_note_with_bom_and_crlf_ingests_like_its_plain_equivalent(ws):
    ws.directory(EVERYONE)
    ws.raw_note("kickoff.md", b"\xef\xbb\xbf" + KICKOFF.replace("\n", "\r\n").encode("utf-8"))

    code, out, err = ws.ingest()

    assert (code, err) == (0, "")
    assert ws.run("list")[1].splitlines() == [
        "ID  STATUS  DUE         OWNER        TASK",
        "1   open    2026-09-08  Priya Nair   send the revised quote to Acme",
        "2   done    -           Rahul Mehta  set up the staging environment",
    ]


MIXED = """\
---
date: Monday, 14 September 2026
attendees:
  - Priya Nair
  - Rahul Mehta
---
# Design review

* [ ] Priya to send the revised quote
    + [X] Rahul to set up staging
TODO: Priya to book the room
> - [ ] Rahul to quote someone else

```
- [ ] Priya to paste this template
```
<!--
- [ ] Rahul to do the cut item
-->

| Owner | Task | Due |
|-------|------|-----|
| Rahul | Review the PR | 2026-09-18 |
"""


def test_mixed_style_note_yields_every_real_item_and_no_decoys(ws):
    ws.directory(EVERYONE)
    ws.note("review.md", MIXED)

    code, out, err = ws.ingest()

    assert (code, err) == (0, "")
    assert out.strip() == "1 notes read, 0 skipped, 4 new items, 0 merged, 0 need review"
    assert ws.run("list")[1].splitlines() == [
        "ID  STATUS  DUE         OWNER        TASK",
        "1   open    -           Priya Nair   send the revised quote",
        "2   done    -           Rahul Mehta  set up staging",
        "3   open    -           Priya Nair   book the room",
        "4   open    2026-09-18  Rahul Mehta  Review the PR",
    ]

FILTERS = """\
# Meeting: Planning
Date: 2026-09-01
Attendees: Priya Nair, Rahul Mehta

- [ ] Priya Nair to send the quote by 2026-09-08
- [x] Rahul Mehta to set up staging by 2026-09-02
- [ ] Rahul Mehta to review the PR by 2026-09-10
- [ ] Priya Shah to book the venue by 2026-09-09
- [ ] Draft the agenda
- [ ] Rahul Mehta to fix the build
"""


@pytest.fixture
def filtered(ws):
    ws.directory({"Priya Nair": "pn@example.com", "Rahul Mehta": "rm@example.com"})
    ws.note("planning.md", FILTERS)
    ws.ingest()
    return ws


def listed(ws, *args):
    code, out, _ = ws.run("list", "--today", "2026-09-09", *args)
    assert code == 0
    return [int(line.split()[0]) for line in out.splitlines()[1:]]


@pytest.mark.parametrize(
    "args, expected",
    [
        (["--owner", "Priya"], [1, 4]),
        (["--owner", "priya nair"], [1]),
        (["--owner", "none"], [5]),
        (["--status", "open"], [1, 3, 4, 5, 6]),
        (["--status", "done"], [2]),
        (["--status", "overdue"], [1]),  # due 09-09 is not overdue on 09-09
        (["--due-before", "2026-09-10"], [1, 2, 4]),
        (["--needs-review"], [4, 5]),  # 5 is Unowned, flagged since ticket 05
        (["--owner", "Rahul", "--status", "open"], [3, 6]),
        (["--owner", "Priya", "--due-before", "2026-09-09"], [1]),
    ],
)
def test_list_filters_return_exactly_the_expected_items(filtered, args, expected):
    assert listed(filtered, *args) == expected


def test_item_due_yesterday_is_overdue_and_due_today_is_not(filtered):
    assert listed(filtered, "--status", "overdue") == [1]
    code, out, _ = filtered.run("list", "--today", "2026-09-10", "--status", "overdue")
    assert [int(line.split()[0]) for line in out.splitlines()[1:]] == [1, 4]


def test_json_lists_owners_sources_status_due_and_flags(filtered):
    code, out, _ = filtered.run("list", "--json", "--today", "2026-09-09", "--needs-review")

    assert code == 0
    assert json.loads(out) == [
        {
            "id": 4,
            "task": "book the venue",
            "status": "open",
            "overdue": False,
            "due": "2026-09-09",
            "owners": [{"name": "Priya Shah", "confirmed": True}],
            "sources": [{"note": "planning.md", "line": 8, "date": "2026-09-01", "title": "Planning"}],
            "flags": [{"kind": "unknown-owner", "detail": "Priya Shah"}],
        },
        {
            "id": 5,
            "task": "Draft the agenda",
            "status": "open",
            "overdue": False,
            "due": None,
            "owners": [],
            "sources": [{"note": "planning.md", "line": 9, "date": "2026-09-01", "title": "Planning"}],
            "flags": [{"kind": "unowned", "detail": ""}],
        },
    ]


@pytest.mark.parametrize(
    "args", [["--due-before", "notadate"], ["--today", "31/02/2026"], ["--status", "late"]]
)
def test_invalid_filter_values_are_a_usage_error(filtered, args):
    code, _, err = filtered.run("list", *args)

    assert code == 2
    assert "usage" in err


def test_unresolved_due_phrase_leaves_no_due_date_and_is_flagged_with_the_phrase(ws):
    ws.directory(EVERYONE)
    ws.note(
        "cutover.md",
        "Date: 2026-09-01\nAttendees: Priya Nair, Rahul Mehta\n"
        "- [ ] Rahul to snapshot the production DB before cutover\n"
        "- [ ] Priya to draft the test plan by end of next week\n",
    )

    assert ws.ingest()[1].strip() == "1 notes read, 0 skipped, 2 new items, 0 merged, 1 need review"
    _, out, _ = ws.run("list", "--needs-review")

    assert out.splitlines() == [
        "ID  STATUS  DUE  OWNER        TASK                        REVIEW",
        "1   open    -    Rahul Mehta  snapshot the production DB  unresolved-due: before cutover",
    ]
    _, out, _ = ws.run("list")
    assert "2026-09-11  Priya Nair   draft the test plan" in out
