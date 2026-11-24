# 09: Compose Follow-ups with preview and confirmation

**What to build:** `followup [<owner>]` composes one plain-text email per Owner (or only the named one) who has Open or Overdue items. The email has a subject with counts, then an Overdue section, an Open section, and a "Can you confirm whether this is yours?" section for items where they are an unconfirmed candidate. Each item shows its task, Due Date (or "no due date") and source meeting. Owner Group items appear for every member. Owners with nothing open get no email. Owners without an email address are skipped and reported. The tool shows a preview of every email and asks "Create N drafts? [y/N]"; `--yes` skips the prompt, and `--dry-run` prints and stops. Drafts go to a Draft sink; this ticket ships the printing sink and a recording test sink.

**Blocked by:** 05, 07

**Status:** ready-for-agent

- [ ] For a pinned `--today`, the composed email for one Owner matches a hand-written expected email, with sections in order
- [ ] An Ambiguous item appears only in the confirm section of both candidates' emails
- [ ] Answering "n" or empty at the prompt sends nothing to the sink, while `--yes` sends every email
- [ ] An Owner missing from the people directory is reported and gets no draft
- [ ] `--dry-run` never calls the sink

Spec: `.scratch/actiontrack/spec.md`
