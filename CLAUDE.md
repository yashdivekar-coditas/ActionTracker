# actiontrack

CLI that ingests markdown meeting notes, tracks action items in SQLite, and creates Gmail **drafts** for follow-ups.

## Commands

- Setup: `uv venv --python 3.9 .venv && uv pip install --python .venv/bin/python -e '.[dev]'`
- Tests: `.venv/bin/python -m pytest` (single file: `.venv/bin/python -m pytest tests/test_parse.py`)
- Run: `.venv/bin/actiontrack ingest notes/`

## Before you change behaviour, read

- `GLOSSARY.md`: the domain words (Action Item, Owner Group, Ambiguous Owner, Duplicate, Malformed Note…). Use them in code, tests and commit messages.
- `docs/adr/`: decisions already made (Gmail via `claude -p`, duplicate merging, owner groups). Flag it if your change contradicts one.
- `.scratch/actiontrack/spec.md` and `.scratch/actiontrack/issues/`: the spec and the tickets, worked blockers-first.

## Rules

- Python 3.9 and the standard library only; `pytest` is the single dev dependency. Start modules with `from __future__ import annotations`.
- Email leaves the tool only as a Gmail draft. The `claude -p` call allows exactly the Gmail `create_draft` tool and nothing else.
- Every date calculation takes `today` / the Meeting Date as a parameter, so tests pin dates (`--today` on the CLI).
- Tests drive two seams only: the CLI (`main(argv)` in-process) and `parse_note(text)`. Fixtures are small notes written in the test; the sample `notes/` folder is only for one smoke test.
- Nothing is tuned to the sample notes: grammar for dates, owners and item forms must be general.
- `people.json` holds placeholder `example.com` addresses only; this repo is public.
