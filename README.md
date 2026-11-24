# actiontrack

CLI that reads a folder of markdown meeting notes, tracks the action items in SQLite, and saves follow-up emails to Gmail **drafts** (it never sends). Python 3.9+, standard library only. Domain words (Action Item, Owner Group, Needs Review, ...) are defined in [GLOSSARY.md](GLOSSARY.md).

## Install

```sh
uv venv --python 3.9 .venv && uv pip install --python .venv/bin/python -e '.[dev]'
.venv/bin/python -m pytest          # full suite
```

The examples below use `actiontrack` for `.venv/bin/actiontrack`. Every command takes `--db FILE` (default `.actiontrack.db`) and `--people FILE` (default `people.json`, a name -> email map; placeholder `example.com` addresses only). Exit codes: 0 ok, 1 error, 2 usage error.

## Commands

### `ingest <folder>`

Reads every `*.md` note. Malformed Notes are skipped with a reason on stderr; the rest are ingested. Re-running is safe: unchanged notes are skipped by content hash.

```console
$ actiontrack ingest notes/
skipped 2026-09-09-notes-final-v2.md: empty file
skipped 2026-10-03-sales-pipeline.md: no readable Meeting Date
skipped scratch.md: binary or undecodable file
skipped untitled.md: no readable Meeting Date
31 notes read, 4 skipped, 92 new items, 23 merged, 14 need review
```

### `list`

Filters combine. `--owner` takes a first name (every match), a full name (exact) or `none` (Unowned). `--status` is `open`, `done` or `overdue` (open and due before today). `--due-before DATE`, `--today DATE` (pin "today"; default is the real date), `--json` for machine output (adds `overdue`, owners with `confirmed`, `sources`, `flags`), `--needs-review` adds a REVIEW column with the reason.

```console
$ actiontrack list --owner Meera --status overdue --due-before 2026-10-01 --today 2026-10-15
ID  STATUS  DUE         OWNER       TASK
26  open    2026-09-18  Meera Iyer  update the pipeline sheet

$ actiontrack list --owner none
ID  STATUS  DUE  OWNER  TASK
18  open    -    -      update the CRM notes
33  open    -    -      write the design-system changelog
```

### `done <id>`, `edit <id>`, `merge <id> <into>`

Human corrections. They survive later ingests; Done never reopens.

```console
$ actiontrack done 5
#5 done, due 2026-09-03, Rahul Mehta: open the repo access request
$ actiontrack edit 10 --due 2026-10-09          # also --owner NAME (repeat for a group), --task TEXT
#10 open, due 2026-10-09, Sam Okafor: snapshot the production DB
$ actiontrack merge 23 3                        # fold #23 into #3
#3 open, due 2026-09-03, Anita Desai: share first wireframes
$ actiontrack edit 999 --due 2026-10-09
error: no item with id 999                      # exit 1; `edit 27` with no option exits 2
```

### `followup [owner]`

Composes one email per Owner (Overdue first, then Open, then "Can you confirm whether this is yours?" for Ambiguous Owners) and creates a Gmail draft for each by running `claude -p` with only `create_draft` allowed ([ADR 0001](docs/adr/0001-gmail-drafts-via-claude-p.md)). Needs the `claude` binary and an authorised Gmail connector. `--dry-run` prints the emails and stops; `--yes` skips the `Create N drafts? [y/N]` prompt. Owners with no address in `people.json` are reported on stderr.

```console
$ actiontrack followup "Priya Shah" --dry-run --today 2026-10-15
To: priya.shah@example.com
Subject: Follow-up: 6 overdue, 3 open, 2 to confirm

Hi Priya,

Here is where your action items stand.

Overdue (6)
- draft the test plan for invoice rounding (due 2026-09-11; from Billing migration sync, 2026-09-03)
- ...

Can you confirm whether this is yours?
- own the hiring plan for the two QA roles (no due date; from Q4 planning offsite, 2026-09-30)
- ...
```

## Review flow

The tool flags what it is unsure of instead of guessing. A person then settles each flag:

1. `actiontrack list --needs-review` shows items with the reason: `ambiguous-owner`, `unknown-owner`, `unowned`, `unresolved-due`, `possible-duplicate: #id`.
2. Fix with `edit <id> --owner NAME` (clears the owner flags), `edit <id> --due DATE` (clears `unresolved-due`), or `merge <id> <into>` for a possible duplicate.
3. Re-run `ingest` whenever notes change; the corrections stay.

```console
$ actiontrack list --needs-review --owner Priya
ID  STATUS  DUE         OWNER                                               TASK                                      REVIEW
27  open    2026-09-21  Priya Shah (unconfirmed), Priya Nair (unconfirmed)  sign off the cutover checklist            ambiguous-owner: Priya
...
$ actiontrack edit 27 --owner "Priya Nair"
#27 open, due 2026-09-21, Priya Nair: sign off the cutover checklist
```

## Design decisions

- [ADR 0001: Gmail drafts via `claude -p` with only `create_draft` allowed](docs/adr/0001-gmail-drafts-via-claude-p.md)
- [ADR 0002: Duplicates merge on Owner plus fuzzy task wording; Done is sticky](docs/adr/0002-duplicates-merge-by-owner-and-fuzzy-task.md)
- [ADR 0003: Owner Groups; ambiguous names become unconfirmed groups](docs/adr/0003-owner-groups-and-ambiguous-owners.md)

Also: the spec is in [.scratch/actiontrack/spec.md](.scratch/actiontrack/spec.md), the tickets in `.scratch/actiontrack/issues/`. Tests drive only the CLI (`main(argv)` in-process) and `parse_note(text)`; one smoke test ingests the shipped `notes/`.

## Known limits

From the ticket comments in `.scratch/actiontrack/issues/`:

- **Notes**
  - Frontmatter is a small `key: value` / `- item` reader, not YAML.
  - `ACTION:` / `TODO:` match upper-case only.
  - Decoy stripping is line-based: a comment or fence opened inside a blockquote is not tracked, and a header row repeated inside one table reads as a data row.
  - A due phrase inside a table task is not split out when there is no Due column.
  - Files that are not `*.md` (like `2026-09-19-offsite-draft.txt`) and directories named `*.md` are ignored silently.
- **Dates**
  - "before ..." phrases are never resolved: no Due Date, flagged `unresolved-due`. Any " before " in a task line counts as a due phrase.
  - Without "by"/"before", a due phrase is found after "due [by|on]", "for" or "on", or as the last few words of the task ("fix build, EOD"), but only when it resolves to a date; "for finance" stays in the task.
  - "next month" is the same day next month, "end of week" the Friday on or after the meeting, "mid-<month>" the 15th.
  - A weekday/date mismatch ("Wed 16 Sep") trusts the date.
- **Owners**
  - Everyone/Team with no attendee list leaves the item Unowned.
  - A name matching no attendee is kept as written and flagged `unknown-owner`.
  - `edit --owner` accepts any non-blank name; one missing from `people.json` is flagged `unknown-owner`.
- **Duplicates**
  - Thresholds (`HIGH_SIMILARITY = 0.85`, `LOW_SIMILARITY = 0.6`) were picked from hand-made examples, not tuned on `notes/`. Two different tasks by one Owner can merge (see [ADR 0002](docs/adr/0002-duplicates-merge-by-owner-and-fuzzy-task.md)); Sources are kept so merges can be audited.
  - Lines removed from a note leave their item behind.
  - Notes are identified by file name, so two folders with a same-named note are treated as one.
  - A later single-owner repeat can merge into a group item and close it for the whole group.
  - A note added later with an earlier Meeting Date merges but does not override a newer Due Date.
  - `merge` keeps the target's owners, due date and flags; edits on the merged-away item are not carried over.
  - Edited owners and dates are not re-flagged by later ingests, even if a newer note disagrees; run `edit` again.
- **Usage:** an invalid date argument (`--due`, `--today`, `--due-before`) is a usage error (exit 2).
- **Storage:** the database schema is not migrated; delete `.actiontrack.db` after upgrading.
- **Gmail:** one `claude -p` call per email (300 s timeout each), no rollback if a later one fails; earlier drafts stay, and the error lists which owners have a draft and which do not. The adapter's real-Gmail path has not been verified end to end (see ticket 10's comments).

## How I used AI

Workflow, in order:

1. `ask-matt`, to pick the workflow.
2. `grill-with-docs`, to stress-test the brief against the domain; produced `GLOSSARY.md` and the ADRs.
3. `to-spec`, which wrote `.scratch/actiontrack/spec.md`.
4. `to-tickets`, which split the spec into the blocker-ordered tickets in `.scratch/actiontrack/issues/`.
5. `implement` for ticket 01 (the tracer: ingest and list).
6. `implement-spec` for the rest: parallel implementer subagents, one git worktree per ticket, plus merger subagents folding finished branches into an integration branch.

Throughout: TDD (red-green-refactor through the two seams above) and a two-axis code review (Standards and Spec) per ticket and over the whole branch.

TODO(Yash): where I overrode the AI (decisions I changed or rejected, and why).

TODO(Yash): what I verified by hand (e.g. real Gmail drafts via `followup`, spot checks of `list` against the notes).
