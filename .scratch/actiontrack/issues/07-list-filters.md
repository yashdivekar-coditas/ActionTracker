# 07: Filter and format `list`

**What to build:** `list` supports `--owner` (a first name matches every person with it, a full name matches exactly, `none` matches Unowned items; case-insensitive), `--status open|done|overdue` (overdue means open with a Due Date before today, derived at read time), `--due-before <date>`, `--needs-review`, and `--today <date>` to pin today. Filters combine. `--json` prints machine-readable items including Owners (with confirmed state), Sources and flags. Invalid dates or status values give a clear usage error with exit code 2.

**Blocked by:** 01

**Status:** done

- [x] Each filter and a combination of two filters return exactly the expected ids
- [x] With `--today` pinned, an item due yesterday is overdue and one due today is not
- [x] `--json` output parses and contains Owners, Sources, status, due and flags
- [x] `--due-before notadate` exits 2 with a message

Spec: `.scratch/actiontrack/spec.md`

## Comments

- `--json` has `"sources": []` until ticket 06 stores Sources; fill it in `_as_dict` in `cli.py`.
- Table STATUS column shows the stored status (open/done); overdue is a `--json` boolean and a filter, not a table value.
- Unconfirmed owners are marked "(unconfirmed)" in the table; no ticket yet produces them (05), so only the JSON `confirmed` flag is tested.
- `main` now returns argparse's exit code (2 for usage errors) instead of raising SystemExit.
