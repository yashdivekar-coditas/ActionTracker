# 06: Merge Duplicates across meetings and make re-ingest idempotent

**What to build:** As described in ADR-0002, notes are processed in Meeting Date order. A later item with the same Owners (or a candidate of an Ambiguous group) and a near-identical normalized task merges into the earlier item. Its Source is added, its Due Date wins when present, and a `[x]` makes the item Done; a Done item never reopens. A later single-Person repeat narrows an Ambiguous group to that Person and clears its flag. Items above the low similarity threshold but below the high one stay separate and are flagged `possible-duplicate` pointing at the other id. Re-ingesting changes nothing, notes whose content hash is unchanged are skipped, and item ids stay stable. A changed note has its new lines merged in.

**Blocked by:** 04, 05

**Status:** done

- [x] A task reworded across three meetings (articles and punctuation differ, initial added) ends as one item with three Sources and the latest Due Date
- [x] An item ticked in a middle meeting stays Done when a later meeting lists it unticked
- [x] Two clearly different tasks by the same Owner never merge, and a borderline pair is flagged `possible-duplicate`
- [x] An Ambiguous "Priya" item followed by a "Priya N." repeat becomes a single confirmed Priya Nair item
- [x] Running `ingest` twice gives byte-identical `list --json` output, and the second run reports notes as unchanged
- [x] Adding a new note to the folder and re-ingesting adds only its items

Spec: `.scratch/actiontrack/spec.md`

## Comments

- Thresholds are `HIGH_SIMILARITY = 0.85` and `LOW_SIMILARITY = 0.6` in `duplicates.py` (difflib ratio on normalized text, filler words in `FILLER_WORDS`); chosen from hand-made examples, not tuned on `notes/`.
- Sources: `ActionItem.sources` holds `Source(note, line, date, title)` (note = file name in the folder). `str(source)` is the Follow-up label, "Title, 2026-09-08" (the file name when the note has no title); `list --json` shows the structured fields. Ticket 09's tests were updated to expect "from <label>".
- A line is keyed by (note, owner phrase, task, due phrase). Re-reading a changed note skips known lines (only refreshing their line number and honouring a new tick); an edited line is a new line that merges by similarity into the same item. Lines removed from a note leave their item (spec: out of scope).
- A note added later with an earlier Meeting Date still merges, but does not override a Due Date from a newer Source.
- Matching needs one shared Owner name (or an Ambiguous candidate); two Unowned items may match each other. A merge keeps the first wording, and an Ambiguous group only narrows (never widens). A possible-duplicate flag carries `#<id>` and is placed on the newer item.
- Summary line gains `, N unchanged` only when N > 0; "notes read" counts every readable note, `need review` counts all flagged items in the store.
- `edit --owner` narrowing and `merge` (ticket 08) are not built; the old DB schema is not migrated.
