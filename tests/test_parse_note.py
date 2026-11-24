from __future__ import annotations

from datetime import date

from actiontrack.notes import Meeting, parse_note

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
