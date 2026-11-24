# 09: Compose Follow-ups with preview and confirmation

**What to build:** `followup [<owner>]` composes one plain-text email per Owner (or only the named one) who has Open or Overdue items. The email has a subject with counts, then an Overdue section, an Open section, and a "Can you confirm whether this is yours?" section for items where they are an unconfirmed candidate. Each item shows its task, Due Date (or "no due date") and source meeting. Owner Group items appear for every member. Owners with nothing open get no email. Owners without an email address are skipped and reported. The tool shows a preview of every email and asks "Create N drafts? [y/N]"; `--yes` skips the prompt, and `--dry-run` prints and stops. Drafts go to a Draft sink; this ticket ships the printing sink and a recording test sink.

**Blocked by:** 05, 07

**Status:** done

- [x] For a pinned `--today`, the composed email for one Owner matches a hand-written expected email, with sections in order
- [x] An Ambiguous item appears only in the confirm section of both candidates' emails
- [x] Answering "n" or empty at the prompt sends nothing to the sink, while `--yes` sends every email
- [x] An Owner missing from the people directory is reported and gets no draft
- [x] `--dry-run` never calls the sink

Spec: `.scratch/actiontrack/spec.md`

## Comments

- Source meetings: `followup._sources(item)` is the seam; it reads an optional `item.sources` (labels) and the email shows "from <label>" only when present. Ticket 06 must populate it (and pick the label format, e.g. meeting title plus date).
- The default sink is still the printing sink (prints a "not saved" line, then "Created N drafts."); ticket 10 swaps in the Claude/Gmail adapter in `main(argv, sink=None)` and should raise `DraftError` on failure (CLI exits 1). The recording sink lives in `tests/test_followup.py`.
- An Owner whose only open items are unconfirmed (Ambiguous) still gets an email with just the confirm section; the subject counts "to confirm".
- Owner arg uses list's matching (first name = every match, full name exact), now shared as `store.matches_name`.
- Owners without an address are reported on stderr; exit code stays 0.
