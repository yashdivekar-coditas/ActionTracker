# 07: Filter and format `list`

**What to build:** `list` supports `--owner` (a first name matches every person with it, a full name matches exactly, `none` matches Unowned items; case-insensitive), `--status open|done|overdue` (overdue means open with a Due Date before today, derived at read time), `--due-before <date>`, `--needs-review`, and `--today <date>` to pin today. Filters combine. `--json` prints machine-readable items including Owners (with confirmed state), Sources and flags. Invalid dates or status values give a clear usage error with exit code 2.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Each filter and a combination of two filters return exactly the expected ids
- [ ] With `--today` pinned, an item due yesterday is overdue and one due today is not
- [ ] `--json` output parses and contains Owners, Sources, status, due and flags
- [ ] `--due-before notadate` exits 2 with a message

Spec: `.scratch/actiontrack/spec.md`
