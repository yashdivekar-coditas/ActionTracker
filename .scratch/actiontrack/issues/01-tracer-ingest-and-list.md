# 01: Tracer bullet: ingest a clean note and list its Action Items

**What to build:** A person runs `ingest <folder>` on a folder holding one well-formed Meeting Note (a `Date:` line with an ISO date, an `Attendees:` line, checkbox Action Items such as "Priya to send the quote by 2026-09-08"), then `list` shows each item with its id, status, Owner (full name), task and Due Date. The local database, the people directory (`people.json`, overridable path) and the review-flag mechanism are created here. An Owner not found in the people directory is flagged `unknown-owner`, and `list --needs-review` shows flagged items with their reason. This ticket sets up the CLI and the `parse_note(text)` test seams the rest of the work uses.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] `ingest` then `list` on a one-note folder prints every checkbox item with its full-name Owner, task and ISO Due Date
- [x] A ticked `[x]` item is listed as done, an unticked one as open
- [x] An Owner's first name resolves to the single attendee with that first name
- [x] An Owner missing from the people directory is flagged `unknown-owner` and appears in `list --needs-review` with that reason
- [x] The database path and the people directory path can be overridden on the command line
- [x] Tests run through the in-process CLI and `parse_note`, using notes written inside the test

Spec: `.scratch/actiontrack/spec.md`

## Comments

- Review (Standards + Spec) applied: name-like owner phrases only, `ActionItem` naming, flag formatting moved onto `Flag`.
- Deferred to their owning tickets: Malformed Notes crash the run (02); owner lookup falls back to the people directory even when the note has attendees (05); unresolved due phrases are dropped without a flag (04); re-ingest duplicates items and notes are read in filename order (06).
