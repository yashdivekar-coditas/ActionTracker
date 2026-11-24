# 04: Resolve Due Dates from natural phrasing

**What to build:** Due phrases become real dates relative to the Meeting Date: weekday names (with an optional "next"; the first such day strictly after the meeting), today, EOD, tomorrow, EOD tomorrow, end of week, end of next week, end of month, next month, mid-<month>, "in N days", "in N weeks", ISO dates, day-month and month-day names with an optional weekday and ordinal, and day-first slash dates. A yearless date that would land more than about two months before the meeting rolls into the next year. The due phrase is removed from the stored task text. A phrase that can't be resolved leaves no Due Date and flags the item `unresolved-due`, keeping the original phrase.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Every phrasing listed above resolves to the hand-computed date for at least two different Meeting Dates, including a Friday meeting saying "by Friday"
- [ ] A December meeting saying "by 5 Jan" resolves to January of the following year
- [ ] The stored task no longer contains the due phrase
- [ ] "before cutover" gives no Due Date, and the item appears in `list --needs-review` as `unresolved-due` with the phrase

Spec: `.scratch/actiontrack/spec.md`
