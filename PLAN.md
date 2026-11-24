# actiontrack: execution plan (run this in a NEW session)

## 0. Ground rules
- The assessment grades how you use AI, and the submission includes the full Claude transcript. So the goal is work that is visibly **yours and directed by you**, not work that is hidden.
- You make every decision. Claude proposes, you accept or reject, and you write the reason in an ADR.
- Keep the `Co-Authored-By` trailer on commits. Add a short "How I used AI" section to the README.
- Use **one dedicated repo** for actiontrack. Do not reuse the Gatepass repo in `Ai Session/`.
  - `mkdir actiontrack && cd actiontrack && git init`, then `cp -r <path>/assesment/notes ./notes`.
  - Create a **public** GitHub repo on your personal account and push at the end.
- Commit small and often, with messages you write yourself. One slice means one commit (or two: red, then green).
- Stack suggestion: **Python 3, stdlib only** (`argparse`, `sqlite3`, `datetime`, `re`) plus `pytest`.
  - Both Python and Node are installed. Python needs no dependencies and keeps the diff small.
  - Confirm the choice in step 2.

## 1. Orient (about 10 min, no AI)
- Read 8 to 10 of the notes yourself, especially the long and messy ones, and take your own notes. In the sample set these include:
  - `2026-09-09-notes-final-v2.md`
  - `2026-09-19-offsite-draft.txt` (not `.md`)
  - `scratch.md`
  - `untitled.md`
- Run `grep -h "^- \[" notes/* | sort | uniq -c | sort -rn | head -20` to see duplicates.
- Already visible in the data (about 36 files, about 114 checkbox lines):
  - Two Priyas (Nair, Shah) and two Rahuls (Mehta, Verma).
  - Relative dates such as "by Friday", "by tomorrow" and "end of next week".
  - Absolute dates in both `2026-09-08` and `10 Sep` formats.
  - Items with no owner or no due date.
- Write 5 bullets of "what worries me" in `docs/my-notes.md`. This is your human-judgment evidence.

## 2. Grill and design (`/grilling`, then `/domain-modeling`)
- Start the new session by pasting the problem statement and your 5 bullets.
- Run `/grilling` on the design. Questions to force out:
  - **Same first name:** resolve against that meeting's attendee list. If both Priyas are present, mark the owner `ambiguous` and never merge. Never guess.
  - **Duplicate identity:** normalized task text plus resolved owner. Keep the first-seen meeting, record all source files, and keep done status sticky.
  - **Relative dates:** resolve against the meeting date, not today. Decide what "Friday" means when the meeting is on a Friday. Decide what "end of next week" means.
  - **Overdue:** `due < today` and not done. Use an injectable clock so tests are deterministic.
  - **Malformed notes:** what exactly counts as malformed (missing date, missing attendees, unreadable). Skip, report to stderr, exit 0 with a summary.
  - **Unowned and undated items:** stored and listed. `followup` groups them under "Unassigned" or skips them. You decide.
  - **Storage:** SQLite file, `.actiontrack.db`.
  - **Gmail draft path:** a CLI cannot call MCP directly. Options:
    - (a) `followup` shells out to `claude -p` with only the Gmail `create_draft` tool allowed.
    - (b) `followup --emit json` writes draft payloads and a Claude session creates them through the MCP connector.
    - Whatever you pick, put it behind a small `DraftSink` interface with a `--dry-run` that prints the email.
    - Never expose a send tool.
  - **Owner emails:** the notes have no emails. Use a `people.json` mapping (name to email) that you create. Unmapped owners get a draft with an empty "To".
- Run `/domain-modeling` to create or extend `GLOSSARY.md`. Terms: Meeting note, Action item, Owner, Due date, Status (open, done, overdue), Follow-up draft. Decide whether this repo's glossary is separate from Gatepass's.
- Write ADRs (about 4) in `docs/adr/`:
  - Python and stdlib
  - Dedup identity
  - Ambiguous-owner policy
  - Draft-only Gmail via MCP
- Write `.scratch/actiontrack/spec.md`. Then write `.scratch/actiontrack/issues/01-...md` onward as vertical slices, one per behaviour. Use `/to-prd` or `/to-issues` if your session has them. If it doesn't, write them by hand.

## 3. Research (`/research`, 15 min)
- Capture the Gmail MCP `create_draft` contract: params, threading, and what happens on an unmapped recipient. Save it as `docs/research/gmail-draft.md`.
- Do the same for the `claude -p --allowedTools` flags if you choose option (a).
- Use primary docs only. Cite the links in the file.

## 4. Prototype the risky part (`/prototype`, optional, 15 min)
- Throwaway script in `prototype/` that resolves the relative-date phrases found in the 114 lines. Print a table of phrase, meeting date and resolved date, and eyeball it.
- Delete the prototype folder after you copy the rules into the spec. Mention this in the README.

## 5. Build with `/tdd` (core of the session)
- Apply `/codebase-design` first. Target deep modules with small interfaces:
  - `parse(note_text, filename) -> Meeting | Malformed`
  - `resolve_due(phrase, meeting_date) -> date | None`
  - `Store` (SQLite: upsert, query, mark done)
  - `render_followup(owner, items) -> Email`
  - `DraftSink`
  - `cli.py` (thin)
- One red-green-refactor slice at a time, in this order:
  1. Parse one clean note: date, attendees, items with owner and task.
  2. Malformed notes are skipped and reported, with no crash.
  3. Due-date resolution: relative, absolute and none.
  4. Ownerless and undated items.
  5. Same-first-name resolution via attendees (the Priya/Rahul cases).
  6. Cross-meeting dedup.
  7. `ingest <folder>` end to end on the real `notes/`, and it must be idempotent when run twice.
  8. `list` with `--owner`, `--status` and `--due-before`, with overdue computed.
  9. `done <id>`.
  10. `followup <owner>` using the fake `DraftSink`, then the real MCP sink.
- Write **two or three tests yourself by hand**, for example the ambiguous-Priya case and the idempotent re-ingest. Have Claude do the rest.
- Test through public interfaces only. Use fixtures from real sample notes, not mocks of your own code.
- If something breaks unexpectedly, use `/diagnosing-bugs` and mention it in the README.

## 6. Verify manually (about 15 min, you personally)
- Run `ingest notes/` and read the malformed-notes report. Check it lists exactly the files you identified in step 1.
- Run `list --status overdue` and `list --owner Priya`. Spot-check 5 items against the source files.
- Run `followup <owner> --dry-run`, then create one real Gmail **draft** and open it in Gmail. Confirm nothing was sent.
- Take 2 or 3 screenshots for the README.

## 7. Review and ship
- Run `/code-review` against the spec and standards. Fix what you agree with, and list what you rejected and why.
- Write `/writing-for-agents`-style `CLAUDE.md`: commands, layout, how to run tests.
- README:
  - Install and usage for the 4 commands.
  - Design decisions, with links to the ADRs.
  - Known limits.
  - **How I used AI**: which skills, where you overrode Claude, and what you verified by hand.
- Use `/pr` for the PR body if you work on a branch, or merge to `main` yourself.
- Push to your personal GitHub repo. Check that the repo is public and a fresh clone passes `pytest`.

## 8. Submission checklist
- Export the full transcript as `.txt`. Also export this planning session. Put them in `docs/ai-transcripts/` and attach them as required.
- Repo link, public.
- The repo contains: `notes/`, `src/`, `tests/`, `GLOSSARY.md`, `docs/adr/`, `.scratch/actiontrack/`, `CLAUDE.md`, `README.md`.
- `.gitignore` covers the DB file. Make sure `people.json` has no real personal emails if the repo is public.
- Nothing in the code path can send an email.
