# 06: Merge Duplicates across meetings and make re-ingest idempotent

**What to build:** As described in ADR-0002, notes are processed in Meeting Date order. A later item with the same Owners (or a candidate of an Ambiguous group) and a near-identical normalized task merges into the earlier item. Its Source is added, its Due Date wins when present, and a `[x]` makes the item Done; a Done item never reopens. A later single-Person repeat narrows an Ambiguous group to that Person and clears its flag. Items above the low similarity threshold but below the high one stay separate and are flagged `possible-duplicate` pointing at the other id. Re-ingesting changes nothing, notes whose content hash is unchanged are skipped, and item ids stay stable. A changed note has its new lines merged in.

**Blocked by:** 04, 05

**Status:** ready-for-agent

- [ ] A task reworded across three meetings (articles and punctuation differ, initial added) ends as one item with three Sources and the latest Due Date
- [ ] An item ticked in a middle meeting stays Done when a later meeting lists it unticked
- [ ] Two clearly different tasks by the same Owner never merge, and a borderline pair is flagged `possible-duplicate`
- [ ] An Ambiguous "Priya" item followed by a "Priya N." repeat becomes a single confirmed Priya Nair item
- [ ] Running `ingest` twice gives byte-identical `list --json` output, and the second run reports notes as unchanged
- [ ] Adding a new note to the folder and re-ingesting adds only its items

Spec: `.scratch/actiontrack/spec.md`
