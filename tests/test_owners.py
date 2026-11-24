from __future__ import annotations

import re

from test_cli import ws  # noqa: F401  (the Workspace fixture)

DIRECTORY = {
    "Priya Nair": "priya.nair@example.com",
    "Priya Shah": "priya.shah@example.com",
    "Anita Desai": "anita.desai@example.com",
    "Rahul Mehta": "rahul.mehta@example.com",
    "Lena Fischer": "lena.fischer@example.com",
}


def note(attendees: str, *items: str) -> str:
    header = "Date: 2026-09-01\n" + (f"Attendees: {attendees}\n" if attendees else "")
    return header + "".join(f"- [ ] {item}\n" for item in items)


def listed(ws, attendees, *items):  # noqa: F811
    """Ingest one note and return (owner cell, task) per listed item."""
    ws.directory(DIRECTORY)
    ws.note("m.md", note(attendees, *items))
    assert ws.ingest()[0] == 0
    return rows_of(ws)


def rows_of(ws):  # noqa: F811
    _, out, _ = ws.run("list")
    return [tuple(re.split(r"\s{2,}", row.split(None, 3)[3])) for row in out.splitlines()[1:]]


def test_first_name_shared_by_two_attendees_is_an_unconfirmed_group_flagged_ambiguous(ws):  # noqa: F811
    ws.directory(DIRECTORY)
    ws.note("m.md", note("Priya Nair, Priya Shah", "Priya to send the quote"))

    ws.ingest()
    _, out, _ = ws.run("list", "--needs-review")

    assert out.splitlines()[1:] == [
        "1   open    -    Priya Nair (unconfirmed), Priya Shah (unconfirmed)"
        "  send the quote  ambiguous-owner: Priya"
    ]


def test_surname_initial_picks_the_right_one_of_two_attendees(ws):  # noqa: F811
    ws.directory(DIRECTORY)
    ws.note("m.md", note("Priya Nair, Priya Shah", "Priya N. to send the quote"))

    ws.ingest()
    _, out, _ = ws.run("list")

    assert out.splitlines()[1:] == ["1   open    -    Priya Nair  send the quote"]


ALL = "Priya Nair, Priya Shah, Anita Desai, Rahul Mehta, Lena Fischer"


def test_groups_helpers_nobody_and_shorthand_yield_the_stated_owners(ws):  # noqa: F811
    rows = listed(
        ws,
        ALL,
        "Anita & Rahul to audit contrast",
        "Anita and Rahul to write the brief",
        "Lena (with Priya N.) to review the PR",
        "Everyone to read the spec",
        "Team to fill in the survey",
        "All to submit timesheets",
        "Someone to book the room",
        "TBD to pick a vendor",
        "Anyone to water the plants",
        "Send the signed contract",
        "@anita: tidy the board",
        "Rahul: fix the build",
    )

    everyone = "Priya Nair, Priya Shah, Anita Desai, Rahul Mehta, Lena Fischer"
    assert rows == [
        ("Anita Desai, Rahul Mehta", "audit contrast"),
        ("Anita Desai, Rahul Mehta", "write the brief"),
        ("Lena Fischer", "review the PR"),
        (everyone, "read the spec"),
        (everyone, "fill in the survey"),
        (everyone, "submit timesheets"),
        ("-", "book the room"),
        ("-", "pick a vendor"),
        ("-", "water the plants"),
        ("-", "Send the signed contract"),
        ("Anita Desai", "tidy the board"),
        ("Rahul Mehta", "fix the build"),
    ]


def test_nobody_words_and_missing_owner_phrases_are_flagged_unowned(ws):  # noqa: F811
    ws.directory(DIRECTORY)
    ws.note("m.md", note(ALL, "Someone to book the room", "Send the signed contract"))

    ws.ingest()
    _, out, _ = ws.run("list", "--needs-review")

    assert [row.split()[-1] for row in out.splitlines()[1:]] == ["unowned", "unowned"]


def test_name_nobody_matches_is_kept_as_written_and_flagged_unknown_owner(ws):  # noqa: F811
    ws.directory(DIRECTORY)
    ws.note("m.md", note(ALL, "Zoltan to fix the build"))

    ws.ingest()
    _, out, _ = ws.run("list", "--needs-review")

    assert out.splitlines()[1].endswith("Zoltan  fix the build  unknown-owner: Zoltan")


def test_note_without_attendees_resolves_a_unique_first_name_from_the_people_directory(ws):  # noqa: F811
    rows = listed(ws, "", "Anita to audit contrast", "Priya to send the quote")

    assert rows == [("Anita Desai", "audit contrast"), ("Priya Nair (unconfirmed), Priya Shah (unconfirmed)", "send the quote")]


def test_note_without_attendees_also_knows_attendees_of_other_notes(ws):  # noqa: F811
    ws.directory({})
    ws.note("a.md", note("Karan Joshi, Meera Iyer", "Karan to ship it"))
    ws.note("b.md", note("", "Meera to review it"))

    ws.ingest()

    assert [owner for owner, _ in rows_of(ws)] == ["Karan Joshi", "Meera Iyer"]


def test_people_directory_is_not_consulted_when_the_note_lists_attendees(ws):  # noqa: F811
    rows = listed(ws, "Priya Nair", "Anita to audit contrast")

    assert rows == [("Anita", "audit contrast")]
