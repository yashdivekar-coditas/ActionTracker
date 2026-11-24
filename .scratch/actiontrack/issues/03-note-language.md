# 03: Recognise every Action Item form and ignore Decoys

**What to build:** Notes written in other styles still work. Headers can be a `Date:` line, a bold `**Date:**` line or YAML frontmatter (`date:` and `attendees:` as a list), with Meeting Dates like `9 September 2026`, `Monday, 14 September 2026`, `Sep 9, 2026` or day-first `09/09/2026`. Action Items are found anywhere in the note: `-`, `*` and `+` bullets, nested bullets, `[x]` and `[X]`, lines starting `ACTION:` or `TODO:`, and rows of a markdown table with Owner and Action/Task columns (Due optional). Checkboxes inside blockquotes, fenced code blocks and HTML comments are Decoys and are ignored.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Each header style and Meeting Date format above yields the same Meeting Date and attendees
- [ ] Each item form above yields an Action Item, and `ACTION:`/`TODO:` and table rows are open
- [ ] Checkbox lines inside a blockquote, a fenced code block or an HTML comment (single- or multi-line) produce no Action Item
- [ ] Tested as a table through `parse_note`, plus one CLI test with a mixed-style note

Spec: `.scratch/actiontrack/spec.md`
