# 02: Skip and report Malformed Notes

**What to build:** `ingest` never crashes on bad input. Empty files, binary or undecodable files, and notes without a readable Meeting Date are skipped. Each one is reported on stderr with its file name and reason, and the run carries on with the remaining notes. Only `.md` files are read. A byte-order mark, Windows line endings and typographic dashes and quotes parse normally. Every run ends with a summary (notes read, skipped, items new, merged, needing review) and exits 0 even when notes were skipped.

**Blocked by:** 01

**Status:** done

- [x] An empty note, a note containing binary or NUL bytes, and a note with an unreadable date are each reported with a distinct reason, and the other notes still ingest
- [x] Non-`.md` files are ignored and are not reported as skipped
- [x] A note with a BOM and CRLF line endings ingests the same as its plain equivalent
- [x] The summary line reports the correct counts, and the exit code is 0 with skips present

Spec: `.scratch/actiontrack/spec.md`

## Comments

- Deferred to ticket 03: Meeting Date is ISO-only here, so notes with other header styles or date formats (e.g. 2026-09-09-qa-standup.md, 2026-09-14-onboarding-flow-design.md in `notes/`) are skipped as "no readable Meeting Date" for now.
- Deferred to ticket 06: the summary's `merged` count is a constant 0 until Duplicates are merged.
- Skipped files also include unreadable ones (OSError) and directories named `*.md` are ignored silently.
