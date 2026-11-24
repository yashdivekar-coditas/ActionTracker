# 11: Sample-folder smoke test, README and review

**What to build:** The shipped `notes/` folder ingests without crashing, with the expected Malformed Notes reported. The README covers install, every command with examples, the design decisions (linking ADRs), known limits and a How I used AI section. `/code-review` runs over the whole branch, and agreed findings are fixed.

**Blocked by:** 02, 03, 06, 08, 10

**Status:** done

- [x] The smoke test asserts only: no crash, exit 0, and the set of Malformed Note file names reported
- [x] A fresh clone set up from the README commands passes the full test suite
- [x] Code-review findings are either fixed or listed with the reason they were rejected

Spec: `.scratch/actiontrack/spec.md`

## Comments

- Status stays `ready-for-agent`: the `/code-review` run over the whole branch (third criterion) is pending and is run by the orchestrator on the integration branch.
- Smoke test: `tests/test_smoke.py`. Expected Malformed set derived by reading `notes/`: `2026-09-09-notes-final-v2.md` (empty), `scratch.md` (binary), `untitled.md` (no header), `2026-10-03-sales-pipeline.md` ("sometime last week"). The `.txt` file is never read.
- README's "How I used AI" has `TODO(Yash):` placeholders for where the author overrode the AI and what was verified by hand; the author fills them in.
- README examples were run against the shipped `notes/` (never the real `claude`; `followup` shown with `--dry-run`).
- Code review fixed (branch `fix/review-findings`): due phrases without a by marker (tomorrow, EOD, "due"/"for"/"on" that resolve); `edit --owner` flags unknown owners; Unowned items never auto-merge; review queue is Open items only; yearless dates more than 31 days back roll to next year; partial Gmail failures list drafted and undrafted owners; Ambiguous candidates sorted by name; one `is_overdue`, one date grammar, `matches_name` in owners, `Store.items` requires `today`, flag-kind constants, dead code removed, `ingest` reuses `mark_done`, lazy `ClaudeSink`; CLAUDE.md seams and README known limits updated.
- Rejected: `DraftSink` as a Protocol (two real implementations, base class is fine); splitting `cli.py` (thin enough for now); `followup --today`, `DENIED_TOOLS`, the REVIEW column, repeatable `--owner` and the aliases table (small, useful, consistent with the spec).
