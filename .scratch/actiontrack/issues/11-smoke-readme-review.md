# 11: Sample-folder smoke test, README and review

**What to build:** The shipped `notes/` folder ingests without crashing, with the expected Malformed Notes reported. The README covers install, every command with examples, the design decisions (linking ADRs), known limits and a How I used AI section. `/code-review` runs over the whole branch, and agreed findings are fixed.

**Blocked by:** 02, 03, 06, 08, 10

**Status:** ready-for-agent

- [ ] The smoke test asserts only: no crash, exit 0, and the set of Malformed Note file names reported
- [ ] A fresh clone set up from the README commands passes the full test suite
- [ ] Code-review findings are either fixed or listed with the reason they were rejected

Spec: `.scratch/actiontrack/spec.md`
