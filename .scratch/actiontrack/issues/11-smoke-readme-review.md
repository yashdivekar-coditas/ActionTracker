# 11: Sample-folder smoke test, README and review

**What to build:** The shipped `notes/` folder ingests without crashing, with the expected Malformed Notes reported. The README covers install, every command with examples, the design decisions (linking ADRs), known limits and a How I used AI section. `/code-review` runs over the whole branch, and agreed findings are fixed.

**Blocked by:** 02, 03, 06, 08, 10

**Status:** ready-for-agent

- [x] The smoke test asserts only: no crash, exit 0, and the set of Malformed Note file names reported
- [x] A fresh clone set up from the README commands passes the full test suite
- [ ] Code-review findings are either fixed or listed with the reason they were rejected

Spec: `.scratch/actiontrack/spec.md`

## Comments

- Status stays `ready-for-agent`: the `/code-review` run over the whole branch (third criterion) is pending and is run by the orchestrator on the integration branch.
- Smoke test: `tests/test_smoke.py`. Expected Malformed set derived by reading `notes/`: `2026-09-09-notes-final-v2.md` (empty), `scratch.md` (binary), `untitled.md` (no header), `2026-10-03-sales-pipeline.md` ("sometime last week"). The `.txt` file is never read.
- README's "How I used AI" has `TODO(Yash):` placeholders for where the author overrode the AI and what was verified by hand; the author fills them in.
- README examples were run against the shipped `notes/` (never the real `claude`; `followup` shown with `--dry-run`).
