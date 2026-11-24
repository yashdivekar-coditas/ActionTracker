# 05: Resolve Owners, Owner Groups and Ambiguous Owners

**What to build:** The owner phrase becomes Owners as described in ADR-0003. A first name matching one attendee resolves to that attendee. "Priya N." resolves by surname initial. A first name matching several attendees becomes an unconfirmed Ambiguous Owner group of all of them, flagged `ambiguous-owner`. "A & B" and "A and B" form an Owner Group. "A (with B)" is owned by A only. "Everyone"/"Team"/"All" mean the meeting's attendees. "Someone"/"TBD"/"TBA"/"Anyone" and lines with no owner phrase are Unowned and flagged `unowned`. `@anita: task` and `Anita: task` work. A note with no attendee list resolves names against everyone known (the people directory plus attendees of all notes). A name nobody matches is kept as written and flagged `unknown-owner`.

**Blocked by:** 01

**Status:** done

- [x] Two same-first-name attendees with no initial produce one item with both as unconfirmed Owners, flagged `ambiguous-owner`
- [x] An initial picks the right one of the two
- [x] Each group, helper, nobody and shorthand form above yields the Owners stated
- [x] A note without attendees resolves a unique first name from the people directory
- [x] `list` marks unconfirmed Owners visibly

Spec: `.scratch/actiontrack/spec.md`

## Comments

- Everyone/Team/All with no attendee list leaves the item Unowned (nobody to expand to); the people directory is deliberately not used for groups.
- With an attendee list, a name matching no attendee is kept as written and flagged `unknown-owner`, even if the people directory knows it (ticket 01's note).
- `unknown-owner` is one flag per item listing every unknown name (flags are keyed by kind).
- Owner phrase grammar stays limited to checkbox lines; `ACTION:`/`TODO:` and table owners belong to the item-forms ticket and need to feed the same `resolve_owners`.
- Ingest now parses all notes before resolving, to learn every attendee; ticket 02 (Malformed Notes) must keep that two-pass shape when it adds skipping.
- Narrowing an Ambiguous Owner via Duplicate merge or `edit --owner` is left to tickets 06/07.
