# 04: Resolve Due Dates from natural phrasing

**What to build:** Due phrases become real dates relative to the Meeting Date: weekday names (with an optional "next"; the first such day strictly after the meeting), today, EOD, tomorrow, EOD tomorrow, end of week, end of next week, end of month, next month, mid-<month>, "in N days", "in N weeks", ISO dates, day-month and month-day names with an optional weekday and ordinal, and day-first slash dates. A yearless date that would land more than about two months before the meeting rolls into the next year. The due phrase is removed from the stored task text. A phrase that can't be resolved leaves no Due Date and flags the item `unresolved-due`, keeping the original phrase.

**Blocked by:** 01

**Status:** done

- [x] Every phrasing listed above resolves to the hand-computed date for at least two different Meeting Dates, including a Friday meeting saying "by Friday"
- [x] A December meeting saying "by 5 Jan" resolves to January of the following year
- [x] The stored task no longer contains the due phrase
- [x] "before cutover" gives no Due Date, and the item appears in `list --needs-review` as `unresolved-due` with the phrase

Spec: `.scratch/actiontrack/spec.md`

## Comments

- "next month" is resolved to the same day of the next month (clamped to its length), "end of week" to the Friday on or after the meeting (a weekend meeting looks to the coming Friday), "mid-<month>" to the 15th; the ticket left these open.
- "before ..." phrases are never resolved (kept whole as the `unresolved-due` detail). Any " before " in a task line is therefore treated as a due phrase; a false positive only costs a review flag.
- Deferred: "due <date>" wording ("results due 15 October") and table Due columns are not extracted as due phrases (note grammar, ticket 03). Weekday/date mismatches ("Wed 16 Sep" when it is not Wednesday) trust the date.
