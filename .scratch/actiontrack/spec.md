Status: ready-for-agent

# actiontrack

Vocabulary is defined in `GLOSSARY.md`; decisions already taken are in `docs/adr/` (0001 Gmail drafts via `claude -p`, 0002 Duplicates, 0003 Owner Groups).

## Problem Statement

A team writes its meeting notes as markdown files. Each note ends up with a handful of Action Items ("Priya to send the revised quote by Friday"), but nobody tracks them after the meeting. The same item gets copied into the next week's notes, reworded, ticked off in one note and still open in another. Due dates are written as "by Friday" or "end of next week", which mean nothing once the note is a month old. Two people share a first name, so "Rahul to review the PR" could mean either of them. Some notes are broken: empty, binary, or missing their date. The result is that Action Items get lost, and follow-up emails are written late or not at all.

The team needs a tool that reads whatever notes they already have, without asking them to change how they write. It should track every Action Item with a real due date and owner, and prepare follow-up emails for a human to check and send. Whenever the tool is not sure about something, it should say so instead of guessing.

## Solution

`actiontrack` is a command-line tool that works on any folder of markdown Meeting Notes:

- **`ingest <folder>`** reads every note and extracts Action Items with Owners, a Due Date resolved against the Meeting Date, task text, Sources and status. It merges Duplicates across meetings and stores the result locally. It skips Malformed Notes with a reason and never crashes. Anything it is unsure about is flagged as Needs Review instead of being guessed.
- **`list`** shows items, filtered by owner, status (open, done, overdue), due date or review flag.
- **`done <id>`** marks an item Done, and later notes can never reopen it.
- **`edit <id>`** and **`merge <id> <into>`** let a human correct the owner, due date or task, or join two items the tool would not merge on its own. Each correction clears the matching flag and survives later ingests.
- **`followup [owner]`** composes one Follow-up per Owner covering their Open and Overdue items. It shows a preview and, after confirmation, saves each one as a Gmail Draft through the Gmail MCP connector. It never sends.

The tool's knowledge of notes is general. It understands common markdown conventions, many date phrasings and several ways of naming an owner. Nothing in it is tied to the sample notes.

## User Stories

### Ingesting notes

1. As a team lead, I want to point the tool at a folder of meeting notes, so that I get every Action Item without copying them by hand.
2. As a team lead, I want the tool to read notes written in different header styles (a `Date:` line, a bold `**Date:**` line, or YAML frontmatter), so that nobody has to reformat old notes.
3. As a team lead, I want Meeting Dates written as `2026-09-01`, `9 September 2026`, `Monday, 14 September 2026`, `Sep 9, 2026` or `09/09/2026` (day-first) to be understood, so that the team's different habits all work.
4. As a team lead, I want checkbox items found anywhere in the note, not only under an "Action items" heading, so that items written mid-discussion are not lost.
5. As a team lead, I want `-`, `*` and `+` bullets, nested bullets, and `[ ]`, `[x]` and `[X]` boxes all recognised, so that different editors' output works.
6. As a team lead, I want lines starting with `ACTION:` or `TODO:` treated as open Action Items, so that people who don't use checkboxes are covered.
7. As a team lead, I want rows of a markdown table with Owner and Action (or Task) columns, and an optional Due column, treated as Action Items, so that tabular summaries count.
8. As a team lead, I want checkboxes inside quoted text, fenced code blocks and HTML comments ignored, so that pasted templates and cut items are not tracked as real Decoys.
9. As a team lead, I want notes with Windows line endings, a byte-order mark or typographic dashes and quotes parsed normally, so that files from any editor work.
10. As a team lead, I want only `.md` files read, so that drafts and other files in the folder are ignored.
11. As a team lead, I want empty files, binary files and notes with no readable Meeting Date skipped and listed with a reason, so that I can fix them, and one bad file never stops the rest.
12. As a team lead, I want the ingest to end with a summary (notes read, notes skipped, items new, items merged, items needing review), so that I know what happened at a glance.
13. As a team lead, I want running `ingest` again on the same folder to change nothing, so that I can run it whenever I like.
14. As a team lead, I want unchanged notes skipped quickly on re-ingest, so that a growing archive of hundreds of notes stays fast.
15. As a team lead, I want new notes added to the folder picked up by the next `ingest`, so that tracking keeps up week by week.
16. As a team lead, I want notes processed in Meeting Date order regardless of file name, so that "latest" always means the most recent meeting.

### Owners

17. As a team lead, I want "Priya to send the quote" resolved to the one attendee called Priya, so that items have a full-name owner.
18. As a team lead, I want "Priya N." resolved by the surname initial when two Priyas attended, so that a short form still finds the right person.
19. As a team lead, I want an owner name that matches two attendees kept as an Ambiguous Owner listing both, and flagged for review, so that the tool never assigns work to the wrong person.
20. As a team lead, I want a note with no attendee list to resolve names against everyone the tool knows (people.json plus attendees of other notes), so that owners are still found.
21. As a team lead, I want "Anita & Rahul" and "Anita and Rahul" stored as one item owned by both, so that both are accountable.
22. As a team lead, I want "Lena (with Priya)" owned by Lena only, so that helpers are not treated as owners.
23. As a team lead, I want "Everyone" or "Team" to mean that meeting's attendees, so that group commitments reach each person.
24. As a team lead, I want "Someone", "TBD" and items with no owner phrase stored as Unowned and flagged, so that they are visible but not emailed to nobody.
25. As a team lead, I want `@anita: audit contrast` and `Anita: audit contrast` read as owner Anita, so that common shorthand works.
26. As a team lead, I want an owner who is not in people.json flagged for review, so that I can add their email before follow-ups go out.

### Due Dates

27. As a team lead, I want "by Friday" resolved to the first Friday after the Meeting Date, so that relative dates become real dates.
28. As a team lead, I want "tomorrow", "EOD", "today", "end of week", "end of next week", "end of month", "next month", "mid-October", "in 3 days" and "in 2 weeks" resolved against the Meeting Date, so that common phrasings all work.
29. As a team lead, I want "10 Sep", "Oct 3rd", "Wed 16 Sep" and "2026-10-09" resolved to that date, with the year taken from the meeting and rolled into the next year when the date would otherwise be months in the past, so that December meetings with January deadlines work.
30. As a team lead, I want a due phrase the tool can't resolve ("before cutover", "before the next review") to leave the item with no Due Date, flagged for review with the phrase kept, so that I can set it by hand.
31. As a team lead, I want the due phrase removed from the stored task text, so that tasks read cleanly and match across meetings.

### Duplicates

32. As a team lead, I want an item repeated in a later meeting with slightly different wording merged into the existing item, so that one commitment is one item.
33. As a team lead, I want a merged item to keep every Source note, so that I can see its history.
34. As a team lead, I want the latest meeting's Due Date to win when a repeat gives a new one, so that slipped deadlines are tracked.
35. As a team lead, I want an item ticked `[x]` in any later note to become Done, so that progress recorded in meetings is reflected.
36. As a team lead, I want a Done item never reopened by a later unticked copy, so that finished work stays finished.
37. As a team lead, I want an Ambiguous Owner item merged into a later repeat that names one of its candidates, narrowing it to that person, so that ambiguity resolves itself when the notes do.
38. As a team lead, I want items that look only somewhat alike kept separate and flagged "possible duplicate of #N", so that the tool never wrongly joins two different tasks.
39. As a team lead, I want item ids to stay the same across ingests, so that ids I've written down keep working.

### Listing

40. As a team member, I want `list` to show id, status, owners, task, Due Date and Source meetings, so that I can scan everything at once.
41. As a team member, I want `--owner Priya` to match every Priya and `--owner "Priya Nair"` only her, so that I can search broadly or exactly.
42. As a team lead, I want `--owner none` to show Unowned items, so that I can find work nobody has taken.
43. As a team member, I want `--status open|done|overdue`, where overdue means open with a Due Date before today, so that I can focus on what's late.
44. As a team member, I want `--due-before <date>` to show items due before that date, so that I can plan the week.
45. As a team lead, I want `--needs-review` to show every flagged item with its reason, so that I can work through the review queue.
46. As a team member, I want unconfirmed owners marked in the output, so that I can tell an Ambiguous Owner from a confirmed one.
47. As a scripter, I want `--json` output, so that I can feed items into other tools.
48. As a tester, I want `--today <date>` to fix what counts as today, so that overdue results are repeatable.

### Human corrections

49. As a team lead, I want `done <id>` to mark an item Done and say which item it was, so that I'm sure I closed the right one.
50. As a team lead, I want `edit <id> --owner "Priya Nair"` to set the owner and clear the ambiguous or unknown-owner flag, so that I can settle who owns it.
51. As a team lead, I want `edit <id> --due 2026-10-20` to set the Due Date and clear the unresolved-date flag, so that I can fix dates the tool couldn't read.
52. As a team lead, I want `edit <id> --task "…"` to fix a garbled task, so that follow-up emails read well.
53. As a team lead, I want `merge <id> <into>` to join a possible duplicate into the original, combining Sources and keeping Done if either is Done, so that I decide the borderline cases.
54. As a team lead, I want my edits and merges kept when I ingest again, so that the notes never overwrite a human decision.
55. As a team lead, I want unknown ids and invalid dates to produce a clear error and a non-zero exit, so that typos don't fail silently.

### Follow-ups

56. As a team lead, I want `followup <owner>` to compose one email for that person listing their Overdue items first, then Open items, each with its Due Date and source meeting, so that the email is ready to review.
57. As a team lead, I want `followup` with no owner to compose one email per Owner who has Open or Overdue items, so that a weekly round of follow-ups is one command.
58. As a team lead, I want items with an Ambiguous Owner included in each candidate's email under "Can you confirm whether this is yours?", so that the right person claims it.
59. As a team lead, I want Owner Group items included in every member's email, so that each accountable person is reminded.
60. As a team lead, I want a preview of every email and a "Create N drafts? [y/N]" prompt before anything reaches Gmail, so that I check them first; `--yes` skips the prompt for scripted use.
61. As a team lead, I want `--dry-run` to print the emails and touch nothing, so that I can check them safely.
62. As a team lead, I want each email saved as a Gmail Draft and never sent, so that a human always presses send.
63. As a team lead, I want owners without an email in people.json skipped and reported, so that I know whose address to add.
64. As a team lead, I want a clear error if the Gmail step fails (no `claude` binary, connector not authorised), so that I don't think drafts exist when they don't.
65. As a team lead, I want a person with nothing open to get no email, so that nobody is pinged for nothing.

## Implementation Decisions

- **Language and storage**: Python 3.9+, standard library only, with SQLite in a single local database file (default `.actiontrack.db`; `--db` overrides it). Packaged with a console entry point `actiontrack`.
- **Modules** (deep modules behind small interfaces):
  - **Note parser**: `parse_note(text) -> Meeting | Malformed`. A Meeting holds Meeting Date, title, attendees and Action Item candidates (raw owner phrase, task text, raw due phrase, ticked flag, line number). It owns all note grammar: header styles, item forms and Decoy stripping (blockquotes, fenced code, HTML comments). It does no owner or date resolution.
  - **Date resolver**: `resolve_due(phrase, meeting_date) -> date | None`. A general grammar: ISO dates; day-month and month-day names with optional weekday and ordinal; slash dates (day-first); weekday names with an optional "next"; today, EOD, tomorrow and "EOD tomorrow"; end of (this/next) week; end of (this/next) month; mid-<month>; "in N days/weeks". A weekday means the first such day strictly after the Meeting Date. A yearless date more than about 2 months before the meeting rolls into the next year.
  - **Owner resolver**: turns a raw owner phrase plus the meeting's attendees plus the Person directory into Owners (each confirmed or unconfirmed) and flags. Group words (everyone, team, all) and nobody words (someone, TBD, TBA, anyone) are fixed lists in one place.
  - **Store**: SQLite persistence. Tables: items (id, task, normalized task, due, status, created/updated), item_owners (item, person name, confirmed), sources (item, note path, line, Meeting Date, ticked), notes (path, content hash, Meeting Date, title, status), flags (item, kind, detail), and a record of human edits so they win over later ingests. The whole ingest runs in one transaction.
  - **Ingester**: walks the folder, checks each file's content hash and skips unchanged notes, parses, sorts by Meeting Date, resolves owners and dates, and matches Duplicates. Returns a report (skipped notes with reasons, counts, flags).
  - **Duplicate matcher**: candidates must share at least one Owner (or overlap an Ambiguous group). Similarity is a token-based ratio on normalized task text (lowercase, punctuation, articles and filler stripped, due phrase removed). At or above the high threshold, items merge automatically. Between the low and high thresholds, they are flagged as possible duplicates. Both thresholds are named constants.
  - **Follow-up composer**: `compose(owner, items, today) -> Email(to, subject, body)`. Plain text, with sections Overdue, Open and "Can you confirm whether this is yours?".
  - **Draft sink**: an interface with two adapters. The Claude adapter runs `claude -p` with `--allowedTools` set to the Gmail `create_draft` tool only, passing the composed email as data, and fails loudly on a non-zero exit (ADR-0001). The Print adapter is used by `--dry-run` and the tests.
  - **CLI**: thin. It parses arguments, wires the modules together and formats output (table or `--json`). Exit codes: 0 for success, including runs where notes were skipped; 1 for an operation error (unknown id, Gmail failure); 2 for a usage error.
- **Status model**: a Done item stays Done forever. Overdue is derived at read time, never stored.
- **Human edits win**: a field set by `edit` is never overwritten by ingest; `merge` is recorded so a later ingest doesn't split the items again.
- **Review flags**: `ambiguous-owner`, `unknown-owner` (not in people.json), `unowned`, `unresolved-due` (with the original phrase), `possible-duplicate` (with the other id). The matching fix clears a flag.
- **People directory**: `people.json` maps full name to email. Missing file means no emails, and every follow-up owner is reported as having no address.
- **Re-ingest**: each Source is keyed by note path and line text, so re-reading a note adds nothing twice. A note whose content changed is re-parsed, and new lines are merged in.

## Testing Decisions

- A good test drives behaviour through a public seam and asserts on what a user would see: CLI output, exit codes, the items `list --json` returns, or the email a sink received. It never queries SQLite directly and never mocks internal modules. Expected values are worked out by hand from the spec, not recomputed the way the code computes them.
- **Seam 1, the CLI**: `main(argv)` called in-process with a temporary notes folder written by the test, a temporary database, a pinned `--today`, and the Print or a recording fake Draft sink. This covers ingest reports, merges, idempotency, filters, edits, merges and follow-ups.
- **Seam 2, `parse_note(text)`**: table-style tests of the note language (header styles, item forms, Decoys, owner phrases, due phrases) using small inline note strings.
- Date resolution is tested through `parse_note`/the CLI unless a table of date phrases proves clumsier there. In that case `resolve_due` is an acceptable extra seam.
- Tests use small made-up notes written for each case, so passing never depends on the sample folder. One smoke test runs `ingest` over the shipped `notes/` folder and asserts only that nothing crashes and the expected files are reported as Malformed.
- The real Claude/Gmail adapter is verified by hand: create one draft, open Gmail, and confirm it is a draft and nothing was sent.
- Prior art: none in this repo; this is the first code.

## Out of Scope

- Sending email, scheduling sends, or tracking whether a follow-up was answered.
- Writing back to the notes (ticking boxes in markdown).
- Reading folders recursively or non-markdown formats.
- Multi-user or shared storage, a server, or a UI beyond the CLI.
- Natural-language understanding beyond the grammar above, such as an LLM extracting items from free prose.
- Deleting items whose source line was removed from a note; they stay until marked Done.

## Further Notes

- The Gmail connector also exposes a send tool. The only protection against sending is the `--allowedTools` list in the Claude adapter, so that list is a single constant and has a test asserting it contains only the create-draft tool.
- The duplicate thresholds are the main tuning knob. The sample notes are used to sanity-check them, not to set them to fit.
- `people.json` in the repo holds placeholder `example.com` addresses only.
