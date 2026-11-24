# 05: Resolve Owners, Owner Groups and Ambiguous Owners

**What to build:** The owner phrase becomes Owners as described in ADR-0003. A first name matching one attendee resolves to that attendee. "Priya N." resolves by surname initial. A first name matching several attendees becomes an unconfirmed Ambiguous Owner group of all of them, flagged `ambiguous-owner`. "A & B" and "A and B" form an Owner Group. "A (with B)" is owned by A only. "Everyone"/"Team"/"All" mean the meeting's attendees. "Someone"/"TBD"/"TBA"/"Anyone" and lines with no owner phrase are Unowned and flagged `unowned`. `@anita: task` and `Anita: task` work. A note with no attendee list resolves names against everyone known (the people directory plus attendees of all notes). A name nobody matches is kept as written and flagged `unknown-owner`.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Two same-first-name attendees with no initial produce one item with both as unconfirmed Owners, flagged `ambiguous-owner`
- [ ] An initial picks the right one of the two
- [ ] Each group, helper, nobody and shorthand form above yields the Owners stated
- [ ] A note without attendees resolves a unique first name from the people directory
- [ ] `list` marks unconfirmed Owners visibly

Spec: `.scratch/actiontrack/spec.md`
