# 08: Human corrections: done, edit, merge

**What to build:** A person settles what the tool couldn't. `done <id>` marks an item Done and echoes it. `edit <id>` with `--owner <full name>` (repeatable for groups), `--due <date>` or `--task <text>` corrects the item and clears the matching flag (`ambiguous-owner`, `unknown-owner`, `unowned`, `unresolved-due`). `merge <id> <into>` folds one item into another, combining Sources and keeping Done if either was Done, and clears `possible-duplicate`. Human decisions win: a later ingest never overwrites an edited field or splits a merge. An unknown id exits 1 with a clear message.

**Blocked by:** 06

**Status:** ready-for-agent

- [ ] `done` then a re-ingest of a note listing the item unticked leaves it Done
- [ ] `edit --owner "Priya Nair"` on an Ambiguous item leaves one confirmed Owner and no flag, and a re-ingest keeps it
- [ ] `edit --due` clears `unresolved-due`, and a re-ingest doesn't revert the date
- [ ] `merge` leaves one item with both items' Sources, and a re-ingest doesn't recreate the merged-away item
- [ ] Unknown ids exit 1

Spec: `.scratch/actiontrack/spec.md`
