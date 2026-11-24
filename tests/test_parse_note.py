from __future__ import annotations

from datetime import date

from actiontrack.notes import Malformed, Meeting, parse_note

CLEAN_NOTE = """\
# Meeting: Quote portal kickoff
Date: 2026-09-01
Attendees: Priya Nair, Rahul Mehta

## Discussion
Acme is waiting on a revised quote.

## Action items
- [ ] Priya to send the revised quote to Acme by 2026-09-08
- [x] Rahul to set up the staging environment
"""


def test_clean_note_yields_meeting_date_attendees_and_action_items():
    meeting = parse_note(CLEAN_NOTE)

    assert isinstance(meeting, Meeting)
    assert meeting.title == "Quote portal kickoff"
    assert meeting.date == date(2026, 9, 1)
    assert meeting.attendees == ["Priya Nair", "Rahul Mehta"]
    assert [(i.owner, i.task, i.due, i.done) for i in meeting.items] == [
        ("Priya", "send the revised quote to Acme", "2026-09-08", False),
        ("Rahul", "set up the staging environment", None, True),
    ]


def test_line_without_an_owner_phrase_has_no_owner():
    note = "Date: 2026-09-01\n- [ ] Send the signed contract to Acme by 2026-09-04\n"

    (item,) = parse_note(note).items

    assert (item.owner, item.task, item.due) == (None, "Send the signed contract to Acme", "2026-09-04")


def test_owner_phrase_forms():
    note = "Date: 2026-09-01\n" + "".join(f"- [ ] {line}\n" for line in [
        "Priya N. to send the quote",
        "Anita & Rahul to audit contrast",
        "Anita and Rahul to write the brief",
        "Lena (with Priya) to review the PR",
        "@anita: tidy the board",
        "Rahul: fix the build",
        "Everyone to read the spec",
    ])

    assert [(i.owner, i.task) for i in parse_note(note).items] == [
        ("Priya N.", "send the quote"),
        ("Anita & Rahul", "audit contrast"),
        ("Anita and Rahul", "write the brief"),
        ("Lena (with Priya)", "review the PR"),
        ("anita", "tidy the board"),
        ("Rahul", "fix the build"),
        ("Everyone", "read the spec"),
    ]


def test_note_that_cannot_be_read_as_a_meeting_is_malformed_with_a_reason():
    assert parse_note("") == Malformed("empty file")
    assert parse_note("  \n\n") == Malformed("empty file")
    assert parse_note("Date: 2026-09-01\x00\n") == Malformed("binary or undecodable file")
    assert parse_note("# Standup\n- [ ] Priya to x\n") == Malformed("no readable Meeting Date")
    assert parse_note("Date: 2026-13-45\n") == Malformed("no readable Meeting Date")


def test_bom_crlf_and_typographic_punctuation_parse_like_plain_text():
    note = "\ufeff# Meeting: Kick\u2011off\r\nDate: 2026-09-01\r\nAttendees: Priya Nair\r\n- [ ] Priya to send the \u201cquote\u201d \u2013 now by 2026-09-08\r\n"

    meeting = parse_note(note)

    assert meeting.date == date(2026, 9, 1)
    assert meeting.attendees == ["Priya Nair"]
    assert [(i.owner, i.task, i.due) for i in meeting.items] == [
        ("Priya", "send the \u201cquote\u201d \u2013 now", "2026-09-08")
    ]
