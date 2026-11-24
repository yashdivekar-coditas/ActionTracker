# Actiontrack

Turns a folder of markdown meeting notes into a tracked list of action items, and drafts follow-up emails to their owners for human review.

## Notes

**Meeting Note**:
One `.md` file recording a single meeting, with a meeting date, attendees and discussion.
_Avoid_: Minutes, doc, file

**Meeting Date**:
The date the meeting took place, read from the note's header; every relative due phrase in the note is resolved against it.

**Malformed Note**:
A Meeting Note that cannot be read as text or has no usable Meeting Date; it is skipped and reported, never partly ingested.
_Avoid_: Invalid note, broken file

**Source**:
A Meeting Note an Action Item was seen in; one Action Item can have many Sources.

## Action items

**Action Item**:
A single commitment recorded in a Meeting Note: a task, its Owner and optionally a Due Date.
_Avoid_: Task, todo, action

**Decoy**:
Text in a note that looks like an Action Item but was not agreed: quoted lines, code blocks, commented-out lines.

**Owner**:
A Person responsible for an Action Item, identified by full name; an Action Item has one or more Owners.
_Avoid_: Assignee

**Owner Group**:
The set of Owners of one Action Item when more than one Person is responsible: named together ("Anita & Rahul") or as "Everyone"/"Team", meaning that meeting's attendees. Every member is accountable and gets the item in their Follow-up.
_Avoid_: Co-owners, team

**Ambiguous Owner**:
An owner name that matches more than one attendee (two Priyas present, no surname or initial); every matching attendee is held in the Owner Group, flagged unconfirmed, until it is resolved to one Person.

**Unowned**:
An Action Item that names nobody ("Someone", "TBD"); it is listed but appears in no Follow-up.

**Due Date**:
The real calendar date an Action Item is due, resolved from the note's wording against the Meeting Date; absent when the wording has none or cannot be resolved.
_Avoid_: Deadline

**Duplicate**:
The same Action Item recorded again in a later Meeting Note, with the same Owner and essentially the same task wording; merged into the existing item rather than stored twice.
_Avoid_: Repeat, copy

## Review

**Needs Review**:
The state of an Action Item the tool could not settle on its own (Ambiguous Owner, unknown Person, unreadable due phrase, possible Duplicate); a person resolves it.
_Avoid_: Error, warning, invalid

**Possible Duplicate**:
An Action Item similar to an existing one but not similar enough to merge automatically; kept separate until a person merges it or leaves it.

## Status

**Open**:
An Action Item not yet done.

**Done**:
An Action Item ticked `[x]` in any Source, or marked done by a person through the tool; once Done it never reopens.

**Overdue**:
An Open Action Item whose Due Date is before today; derived, never stored.

## Follow-up

**Follow-up**:
One email per Owner listing their Open and Overdue Action Items.
_Avoid_: Reminder, nudge

**Draft**:
A Follow-up saved to Gmail drafts for a human to review and send; the tool never sends.

**Person**:
Someone who can own Action Items, known by full name and email address.
_Avoid_: User, member, contact
