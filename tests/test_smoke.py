from __future__ import annotations

from pathlib import Path

from actiontrack.cli import main

REPO = Path(__file__).resolve().parent.parent

# Read by hand from notes/: an empty file, a binary file, a note with no header
# and a note whose Date is "sometime last week". The .txt file is not a Meeting Note.
MALFORMED = {
    "2026-09-09-notes-final-v2.md",
    "scratch.md",
    "untitled.md",
    "2026-10-03-sales-pipeline.md",
}


def test_shipped_notes_ingest_without_crashing_and_report_the_malformed_notes(tmp_path, capsys):
    code = main(["ingest", str(REPO / "notes"), "--db", str(tmp_path / "t.db"), "--people", str(REPO / "people.json")])

    skipped = {line.split()[1].rstrip(":") for line in capsys.readouterr().err.splitlines() if line.startswith("skipped ")}
    assert code == 0
    assert skipped == MALFORMED
