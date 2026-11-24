# 08: Human corrections: done, edit, merge

**What to build:** A person settles what the tool couldn't. `done <id>` marks an item Done and echoes it. `edit <id>` with `--owner <full name>` (repeatable for groups), `--due <date>` or `--task <text>` corrects the item and clears the matching flag (`ambiguous-owner`, `unknown-owner`, `unowned`, `unresolved-due`). `merge <id> <into>` folds one item into another, combining Sources and keeping Done if either was Done, and clears `possible-duplicate`. Human decisions win: a later ingest never overwrites an edited field or splits a merge. An unknown id exits 1 with a clear message.

**Blocked by:** 06

**Status:** done

- [x] `done` then a re-ingest of a note listing the item unticked leaves it Done
- [x] `edit --owner "Priya Nair"` on an Ambiguous item leaves one confirmed Owner and no flag, and a re-ingest keeps it
- [x] `edit --due` clears `unresolved-due`, and a re-ingest doesn't revert the date
- [x] `merge` leaves one item with both items' Sources, and a re-ingest doesn't recreate the merged-away item
- [x] Unknown ids exit 1

Spec: `.scratch/actiontrack/spec.md`

## Comments

- Human decisions are stored in two new tables: `edits` (item, field: owner/due/task) and `aliases` (earlier wordings of an item). Ingest's merge skips due-date updates and owner narrowing for fields in `edits`; Done was already sticky. The old DB schema is still not migrated (new tables appear via `CREATE TABLE IF NOT EXISTS`, but `items` only gets `AUTOINCREMENT` in fresh databases).
- `merge` moves the merged-away item's Sources onto the target (so known lines of changed notes resolve to the target) and keeps its wording as an alias, so a reworded copy of either wording merges into the target instead of recreating it. The target's owners, due date and flags are kept; the merged-away item's human edits are not carried over. Other items' `possible-duplicate #gone` flags are retargeted to the target. `AUTOINCREMENT` stops a merged-away id being reused.
- `edit --task` keeps the old wording as an alias. `edit --owner` accepts any non-blank name (not checked against people.json or attendees) and clears `ambiguous-owner`, `unknown-owner` and `unowned`; an `edit` with no option exits 2, an unknown id or merging an item into itself exits 1.
- Edited owners/due are not re-flagged by later ingests, even if a newer note disagrees; the human has to `edit` again.
