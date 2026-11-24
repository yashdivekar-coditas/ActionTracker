# 03: Recognise every Action Item form and ignore Decoys

**What to build:** Notes written in other styles still work. Headers can be a `Date:` line, a bold `**Date:**` line or YAML frontmatter (`date:` and `attendees:` as a list), with Meeting Dates like `9 September 2026`, `Monday, 14 September 2026`, `Sep 9, 2026` or day-first `09/09/2026`. Action Items are found anywhere in the note: `-`, `*` and `+` bullets, nested bullets, `[x]` and `[X]`, lines starting `ACTION:` or `TODO:`, and rows of a markdown table with Owner and Action/Task columns (Due optional). Checkboxes inside blockquotes, fenced code blocks and HTML comments are Decoys and are ignored.

**Blocked by:** 01

**Status:** done

- [x] Each header style and Meeting Date format above yields the same Meeting Date and attendees
- [x] Each item form above yields an Action Item, and `ACTION:`/`TODO:` and table rows are open
- [x] Checkbox lines inside a blockquote, a fenced code block or an HTML comment (single- or multi-line) produce no Action Item
- [x] Tested as a table through `parse_note`, plus one CLI test with a mixed-style note

Spec: `.scratch/actiontrack/spec.md`

## Comments

- Table rows take owner, task and due straight from their cells; the owner cell is passed on raw (group/nobody phrases and `Owner & Owner` belong to 05, due resolution to 04). A due phrase inside a table task is not split out when there is no Due column.
- Decoy stripping is line-based: a comment or fence opened inside a blockquote is not tracked, and a table header row repeated inside one table is read as a data row.
- `ACTION:`/`TODO:` are matched upper-case only, as the ticket spells them.
- Frontmatter is a small `key: value` / `- item` reader, not full YAML (no multi-line scalars, no nested maps).
