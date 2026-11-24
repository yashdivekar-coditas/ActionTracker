from __future__ import annotations

from datetime import date

import pytest

from actiontrack.dates import resolve_due

TUE = date(2026, 9, 1)
FRI = date(2026, 9, 4)
DEC = date(2026, 12, 15)

# (meeting date, phrase, expected), each expected value worked out by hand from a calendar.
CASES = [
    (TUE, "Friday", date(2026, 9, 4)),
    (TUE, "next Friday", date(2026, 9, 4)),
    (TUE, "Tuesday", date(2026, 9, 8)),
    (TUE, "Mon", date(2026, 9, 7)),
    (FRI, "Friday", date(2026, 9, 11)),
    (FRI, "Monday", date(2026, 9, 7)),
    (TUE, "today", date(2026, 9, 1)),
    (TUE, "EOD", date(2026, 9, 1)),
    (FRI, "EOD", date(2026, 9, 4)),
    (TUE, "tomorrow", date(2026, 9, 2)),
    (TUE, "EOD tomorrow", date(2026, 9, 2)),
    (FRI, "EOD tomorrow", date(2026, 9, 5)),
    (TUE, "end of week", date(2026, 9, 4)),
    (FRI, "end of week", date(2026, 9, 4)),
    (TUE, "end of next week", date(2026, 9, 11)),
    (FRI, "end of next week", date(2026, 9, 11)),
    (TUE, "end of month", date(2026, 9, 30)),
    (DEC, "end of month", date(2026, 12, 31)),
    (TUE, "next month", date(2026, 10, 1)),
    (FRI, "next month", date(2026, 10, 4)),
    (DEC, "next month", date(2027, 1, 15)),
    (date(2026, 1, 31), "next month", date(2026, 2, 28)),
    (TUE, "mid-October", date(2026, 10, 15)),
    (FRI, "mid October", date(2026, 10, 15)),
    (DEC, "mid-January", date(2027, 1, 15)),
    (TUE, "in 3 days", date(2026, 9, 4)),
    (FRI, "in 3 days", date(2026, 9, 7)),
    (TUE, "in 2 weeks", date(2026, 9, 15)),
    (FRI, "in 2 weeks", date(2026, 9, 18)),
    (TUE, "2026-10-09", date(2026, 10, 9)),
    (TUE, "10 Sep", date(2026, 9, 10)),
    (FRI, "10 September", date(2026, 9, 10)),
    (TUE, "Oct 3rd", date(2026, 10, 3)),
    (TUE, "Wed 16 Sep", date(2026, 9, 16)),
    (TUE, "Wednesday, September 16th", date(2026, 9, 16)),
    (TUE, "15/09/2026", date(2026, 9, 15)),
    (TUE, "15/10", date(2026, 10, 15)),
    (DEC, "5 Jan", date(2027, 1, 5)),
    (DEC, "Jan 5", date(2027, 1, 5)),
    (DEC, "05/01", date(2027, 1, 5)),
    (TUE, "15 Aug", date(2026, 8, 15)),  # 17 days back: stays in the meeting's year
    (TUE, "15 Jun", date(2027, 6, 15)),  # 78 days back: rolls forward
    (date(2026, 12, 10), "mid-October", date(2027, 10, 15)),  # 56 days back: next year
    (date(2026, 12, 10), "15 Nov", date(2026, 11, 15)),  # 25 days back: this year
    (TUE, "Friday.", date(2026, 9, 4)),
]


@pytest.mark.parametrize("meeting, phrase, expected", CASES)
def test_due_phrase_resolves_against_the_meeting_date(meeting, phrase, expected):
    assert resolve_due(phrase, meeting) == expected


@pytest.mark.parametrize("phrase", ["before cutover", "before the next review", "soon", "30 Feb", "", None])
def test_unresolvable_phrase_gives_no_date(phrase):
    assert resolve_due(phrase, TUE) is None
