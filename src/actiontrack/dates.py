"""Date resolver: turns a raw due phrase into a real date, relative to the Meeting Date."""
from __future__ import annotations

import calendar
import re
from datetime import date, timedelta
from typing import Optional

_MONTH = r"(?P<month>jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_WEEKDAY = r"(?:mon(?:day)?|tue(?:s(?:day)?)?|wed(?:nesday)?|thu(?:r(?:s(?:day)?)?)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?)"
_ORDINAL = r"(?:st|nd|rd|th)?"
_PREFIX = rf"(?:{_WEEKDAY},?\s+)?"

_MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")
_WEEKDAY_ONLY = re.compile(rf"(?:next\s+)?(?P<day>{_WEEKDAY})")
_IN_N = re.compile(r"in\s+(?P<n>\d+)\s+(?P<unit>day|week)s?")
_MID = re.compile(rf"mid[-\s]{_MONTH}")
_END_OF = re.compile(r"end\s+of\s+(?:the\s+)?(?P<which>this\s+|next\s+)?(?P<unit>week|month)")
_DAY_MONTH = re.compile(rf"{_PREFIX}(?P<day>\d{{1,2}}){_ORDINAL}\s+(?:of\s+)?{_MONTH},?(?:\s+(?P<year>\d{{4}}))?")
_MONTH_DAY = re.compile(rf"{_PREFIX}{_MONTH}\s+(?P<day>\d{{1,2}}){_ORDINAL}(?:,?\s+(?P<year>\d{{4}}))?")
_SLASH = re.compile(r"(?P<day>\d{1,2})/(?P<month>\d{1,2})(?:/(?P<year>\d{4}))?")

# A yearless date further back than this is taken to mean next year.
_ROLL_AFTER = timedelta(days=61)


def resolve_due(phrase: Optional[str], meeting_date: date) -> Optional[date]:
    if not phrase:
        return None
    text = re.sub(r"\s+", " ", phrase.strip().lower()).rstrip(".,;!")
    if not text:
        return None
    text = re.sub(r"^(?:on\s+)?(?:eod|end of day)\b\s*(?:on\s+)?", "", text)  # "EOD Friday" is "Friday"
    try:
        return _resolve(text, meeting_date)
    except ValueError:  # 30 Feb and friends
        return None


def _resolve(text: str, meeting: date) -> Optional[date]:
    if text in ("", "today"):
        return meeting
    if text == "tomorrow":
        return meeting + timedelta(days=1)
    if text == "next month":
        return _add_months(meeting, 1)
    if _ISO.fullmatch(text):
        return date.fromisoformat(text)
    if m := _WEEKDAY_ONLY.fullmatch(text):
        ahead = (_WEEKDAYS.index(m["day"][:3]) - meeting.weekday()) % 7
        return meeting + timedelta(days=ahead or 7)
    if m := _IN_N.fullmatch(text):
        return meeting + timedelta(days=int(m["n"]) * (7 if m["unit"] == "week" else 1))
    if m := _END_OF.fullmatch(text):
        return _end_of(m["unit"], (m["which"] or "").strip(), meeting)
    if m := _MID.fullmatch(text):
        return _yearless(_month_number(m["month"]), 15, meeting)
    if m := _DAY_MONTH.fullmatch(text) or _MONTH_DAY.fullmatch(text):
        return _dated(_month_number(m["month"]), int(m["day"]), m["year"], meeting)
    if m := _SLASH.fullmatch(text):  # day-first
        return _dated(int(m["month"]), int(m["day"]), m["year"], meeting)
    return None


def _end_of(unit: str, which: str, meeting: date) -> date:
    if unit == "week":
        # shortcut: the Friday on or after the meeting; a weekend meeting looks to the coming Friday.
        friday = meeting + timedelta(days=(4 - meeting.weekday()) % 7)
        return friday + timedelta(days=7 if which == "next" else 0)
    target = _add_months(meeting.replace(day=1), 1 if which == "next" else 0)
    return target.replace(day=calendar.monthrange(target.year, target.month)[1])


def _add_months(day: date, months: int) -> date:
    year, month = divmod(day.year * 12 + day.month - 1 + months, 12)
    return date(year, month + 1, min(day.day, calendar.monthrange(year, month + 1)[1]))


def _month_number(name: str) -> int:
    return _MONTHS.index(name[:3]) + 1


def _dated(month: int, day: int, year: Optional[str], meeting: date) -> date:
    return date(int(year), month, day) if year else _yearless(month, day, meeting)


def _yearless(month: int, day: int, meeting: date) -> date:
    found = date(meeting.year, month, day)
    return found.replace(year=found.year + 1) if found < meeting - _ROLL_AFTER else found
