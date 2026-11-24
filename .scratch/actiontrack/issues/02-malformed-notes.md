# 02: Skip and report Malformed Notes

**What to build:** `ingest` never crashes on bad input. Empty files, binary or undecodable files, and notes without a readable Meeting Date are skipped. Each one is reported on stderr with its file name and reason, and the run carries on with the remaining notes. Only `.md` files are read. A byte-order mark, Windows line endings and typographic dashes and quotes parse normally. Every run ends with a summary (notes read, skipped, items new, merged, needing review) and exits 0 even when notes were skipped.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] An empty note, a note containing binary or NUL bytes, and a note with an unreadable date are each reported with a distinct reason, and the other notes still ingest
- [ ] Non-`.md` files are ignored and are not reported as skipped
- [ ] A note with a BOM and CRLF line endings ingests the same as its plain equivalent
- [ ] The summary line reports the correct counts, and the exit code is 0 with skips present

Spec: `.scratch/actiontrack/spec.md`
