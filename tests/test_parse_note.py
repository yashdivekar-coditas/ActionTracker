from __future__ import annotations

from datetime import date

import pytest

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


def test_due_phrase_is_split_off_the_task_including_a_before_phrase_and_dash_separator():
    note = (
        "Date: 2026-09-01\n"
        "- [ ] Sam to snapshot the production DB before cutover\n"
        "- [ ] Priya to send the quote — by end of next week\n"
    )

    first, second = parse_note(note).items

    assert (first.task, first.due) == ("snapshot the production DB", "before cutover")
    assert (second.task, second.due) == ("send the quote", "end of next week")


HEADER_STYLES = {
    "plain": "# Sync\nDate: {d}\nAttendees: Priya Nair, Rahul Mehta\n",
    "bold": "# Sync\n**Date:** {d}\n**Attendees:** Priya Nair, Rahul Mehta\n",
    "bold-colon-outside": "# Sync\n**Date**: {d}\n**Attendees**: Priya Nair, Rahul Mehta\n",
    "frontmatter": "---\ndate: {d}\nattendees:\n  - Priya Nair\n  - Rahul Mehta\n---\n# Sync\n",
    "frontmatter-inline": "---\ndate: \"{d}\"\nattendees: [Priya Nair, Rahul Mehta]\n---\n# Sync\n",
}
DATE_FORMATS = ["2026-09-09", "9 September 2026", "Wednesday, 9 September 2026", "Sep 9, 2026", "09/09/2026", "9th Sept 2026"]


@pytest.mark.parametrize("style", HEADER_STYLES)
@pytest.mark.parametrize("written", DATE_FORMATS)
def test_every_header_style_and_date_format_yields_the_same_meeting_date_and_attendees(style, written):
    meeting = parse_note(HEADER_STYLES[style].format(d=written) + "- [ ] Priya to x\n")

    assert isinstance(meeting, Meeting)
    assert meeting.date == date(2026, 9, 9)
    assert meeting.attendees == ["Priya Nair", "Rahul Mehta"]
    assert [i.line for i in meeting.items] == [len(HEADER_STYLES[style].splitlines()) + 1]


def test_slash_date_is_day_first_and_impossible_dates_are_malformed():
    assert parse_note("Date: 03/04/2026\n").date == date(2026, 4, 3)
    assert parse_note("Date: 13/13/2026\n") == Malformed("no readable Meeting Date")
    assert parse_note("Date: 31 Feb 2026\n") == Malformed("no readable Meeting Date")


ITEM_FORMS = [
    ("- [ ] Priya to send the quote", False),
    ("* [ ] Priya to send the quote", False),
    ("+ [ ] Priya to send the quote", False),
    ("  - [ ] Priya to send the quote", False),
    ("        * [x] Priya to send the quote", True),
    ("- [x] Priya to send the quote", True),
    ("- [X] Priya to send the quote", True),
    ("ACTION: Priya to send the quote", False),
    ("TODO: Priya to send the quote", False),
    ("- TODO: Priya to send the quote", False),
]


@pytest.mark.parametrize("written, done", ITEM_FORMS)
def test_every_item_form_yields_an_action_item(written, done):
    (item,) = parse_note("Date: 2026-09-01\n" + written + "\n").items

    assert (item.owner, item.task, item.done, item.line) == ("Priya", "send the quote", done, 2)


def test_table_rows_with_owner_and_action_or_task_columns_are_open_items():
    note = (
        "Date: 2026-09-01\n\n"
        "| Owner | Action | Due |\n|-------|:------:|-----|\n"
        "| Priya | Send the quote | 2026-09-08 |\n"
        "| Rahul | Set up staging |  |\n\n"
        "| Task | Owner |\n| --- | --- |\n"
        "| Update the roadmap | Anita |\n"
        "\n| Name | Role |\n| --- | --- |\n| Priya | Lead |\n"
    )

    meeting = parse_note(note)

    assert [(i.owner, i.task, i.due, i.done, i.line) for i in meeting.items] == [
        ("Priya", "Send the quote", "2026-09-08", False, 5),
        ("Rahul", "Set up staging", None, False, 6),
        ("Anita", "Update the roadmap", None, False, 10),
    ]


def test_table_without_owner_and_action_columns_is_not_an_item_source():
    assert parse_note("Date: 2026-09-01\n| Name | Role |\n| --- | --- |\n| Priya | Lead |\n").items == []


DECOYS = {
    "blockquote": "> - [ ] Priya to send the quote\n> > - [ ] Priya to send the quote\n",
    "backtick fence": "```\n- [ ] Priya to send the quote\nTODO: Priya to x\n```\n",
    "tilde fence": "~~~md\n- [ ] Priya to send the quote\n~~~\n",
    "single-line comment": "<!-- - [ ] Priya to send the quote -->\n",
    "multi-line comment": "<!--\n- [ ] Priya to send the quote\n-->\n",
    "comment closing mid-line": "<!-- cut\n- [ ] Priya to send the quote\n--> text\n",
    "table in a fence": "```\n| Owner | Action |\n| - | - |\n| Priya | Send the quote |\n```\n",
}


@pytest.mark.parametrize("decoy", DECOYS)
def test_decoys_produce_no_action_item_and_do_not_hide_real_ones(decoy):
    note = "Date: 2026-09-01\n" + DECOYS[decoy] + "- [ ] Rahul to set up staging\n"

    assert [i.owner for i in parse_note(note).items] == ["Rahul"]


def test_header_lines_inside_decoys_are_ignored():
    note = "> Date: 2026-01-01\n```\nDate: 2026-02-02\n```\nDate: 2026-09-01\n"

    assert parse_note(note).date == date(2026, 9, 1)


def test_text_after_an_inline_comment_is_kept():
    (item,) = parse_note("Date: 2026-09-01\n- [ ] Priya to send the quote <!-- tbc -->\n").items

    assert item.task == "send the quote"
