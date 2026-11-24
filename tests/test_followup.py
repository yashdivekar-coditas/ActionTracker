from __future__ import annotations

from actiontrack.cli import main
from actiontrack.followup import DraftError, DraftSink
from test_cli import ws  # noqa: F401  (the Workspace fixture)

DIRECTORY = {
    "Priya Nair": "priya.nair@example.com",
    "Priya Shah": "priya.shah@example.com",
    "Anita Desai": "anita.desai@example.com",
    "Rahul Mehta": "rahul.mehta@example.com",
}

NOTE = """\
Date: 2026-09-01
Attendees: Priya Nair, Priya Shah, Anita Desai, Rahul Mehta

- [ ] Priya N. to send the revised quote to Acme by 2026-09-08
- [ ] Priya N. to book the venue by 2026-09-30
- [ ] Priya N. to write the summary
- [x] Priya N. to archive the old board
- [ ] Priya to review the contract by 2026-09-20
- [ ] Anita & Rahul to audit contrast by 2026-09-12
- [ ] Anita to plan the demo
"""

TODAY = ["--today", "2026-09-10"]


class RecordingSink(DraftSink):
    def __init__(self, fail: bool = False, fail_on: int = 0):
        self.drafts = []
        self.fail = fail
        self.fail_on = fail_on  # the 1-based draft that fails

    def create_draft(self, email):
        if self.fail or len(self.drafts) + 1 == self.fail_on:
            raise DraftError("gmail unavailable")
        self.drafts.append(email)
        return f"draft-{len(self.drafts)}"


def followup(ws, sink, *args, answer=None, monkeypatch=None):  # noqa: F811
    if monkeypatch is not None:
        monkeypatch.setattr("builtins.input", lambda _prompt="": answer)
    ws._capsys.readouterr()
    code = main(["followup", *args, *TODAY, "--db", str(ws.db), "--people", str(ws.people)], sink=sink)
    out, err = ws._capsys.readouterr()
    return code, out, err


def seeded(ws):  # noqa: F811
    ws.directory(DIRECTORY)
    ws.note("kickoff.md", NOTE)
    assert ws.ingest()[0] == 0


def test_email_for_one_owner_lists_overdue_then_open_then_confirm_in_plain_text(ws):
    seeded(ws)
    sink = RecordingSink()

    code, _, _ = followup(ws, sink, "Priya Nair", "--yes")

    assert code == 0
    (email,) = sink.drafts
    assert email.to == "priya.nair@example.com"
    assert email.subject == "Follow-up: 1 overdue, 2 open, 1 to confirm"
    assert email.body == (
        "Hi Priya,\n"
        "\n"
        "Here is where your action items stand.\n"
        "\n"
        "Overdue (1)\n"
        "- send the revised quote to Acme (due 2026-09-08; from kickoff.md, 2026-09-01)\n"
        "\n"
        "Open (2)\n"
        "- book the venue (due 2026-09-30; from kickoff.md, 2026-09-01)\n"
        "- write the summary (no due date; from kickoff.md, 2026-09-01)\n"
        "\n"
        "Can you confirm whether this is yours?\n"
        "- review the contract (due 2026-09-20; from kickoff.md, 2026-09-01)\n"
        "\n"
        "Thanks\n"
    )
    assert not any(mark in email.body for mark in ("#", "**", "|"))


def test_ambiguous_item_is_only_in_the_confirm_section_of_both_candidates(ws):
    seeded(ws)
    sink = RecordingSink()

    followup(ws, sink, "Priya", "--yes")

    assert [e.to for e in sink.drafts] == ["priya.nair@example.com", "priya.shah@example.com"]
    shah = sink.drafts[1]
    assert shah.subject == "Follow-up: 1 to confirm"
    assert shah.body.count("review the contract") == 1
    assert "Overdue" not in shah.body and "Open (" not in shah.body


def test_group_item_goes_to_every_member_and_no_owner_means_one_email_each(ws):
    seeded(ws)
    sink = RecordingSink()

    followup(ws, sink, "--yes")

    assert [e.to for e in sink.drafts] == [
        "anita.desai@example.com",
        "priya.nair@example.com",
        "priya.shah@example.com",
        "rahul.mehta@example.com",
    ]
    assert "audit contrast (due 2026-09-12; from kickoff.md, 2026-09-01)" in sink.drafts[0].body
    assert "audit contrast (due 2026-09-12; from kickoff.md, 2026-09-01)" in sink.drafts[3].body
    assert sink.drafts[3].subject == "Follow-up: 1 open"  # only the shared item; Done items are left out


def test_declining_the_prompt_creates_nothing_and_yes_creates_every_email(ws, monkeypatch):
    seeded(ws)
    for answer in ("n", "", "nope"):
        sink = RecordingSink()
        code, out, _ = followup(ws, sink, answer=answer, monkeypatch=monkeypatch)
        assert code == 0 and sink.drafts == []
        assert "Subject: Follow-up: 1 to confirm" in out  # the preview was still shown

    sink = RecordingSink()
    followup(ws, sink, answer="y", monkeypatch=monkeypatch)
    assert len(sink.drafts) == 4


def test_owner_missing_from_people_directory_is_reported_and_gets_no_draft(ws):
    ws.directory({"Anita Desai": "anita.desai@example.com", "Rahul Mehta": "rahul.mehta@example.com"})
    ws.note("kickoff.md", NOTE)
    ws.ingest()
    sink = RecordingSink()

    code, _, err = followup(ws, sink, "--yes")

    assert code == 0
    assert [e.to for e in sink.drafts] == ["anita.desai@example.com", "rahul.mehta@example.com"]
    assert "skipped Priya Nair: no email address" in err
    assert "skipped Priya Shah: no email address" in err


def test_dry_run_prints_the_emails_and_never_calls_the_sink(ws):
    seeded(ws)
    sink = RecordingSink()

    code, out, _ = followup(ws, sink, "Rahul", "--dry-run")

    assert code == 0 and sink.drafts == []
    assert "To: rahul.mehta@example.com" in out and "audit contrast" in out


def test_sink_failure_is_an_error_exit(ws):
    seeded(ws)

    code, _, err = followup(ws, RecordingSink(fail=True), "Rahul", "--yes")

    assert code == 1 and "gmail unavailable" in err


def test_a_failure_part_way_lists_which_owners_have_drafts_and_which_do_not(ws):
    seeded(ws)

    code, _, err = followup(ws, RecordingSink(fail_on=3), "--yes")

    assert code == 1 and "gmail unavailable" in err
    assert "drafts already created: Anita Desai, Priya Nair" in err
    assert "not created: Priya Shah, Rahul Mehta" in err


def test_nothing_open_means_no_email(ws):
    ws.directory(DIRECTORY)
    ws.note("done.md", "Date: 2026-09-01\nAttendees: Rahul Mehta\n- [x] Rahul to ship it\n")
    ws.ingest()
    sink = RecordingSink()

    code, out, _ = followup(ws, sink, "--yes")

    assert code == 0 and sink.drafts == [] and "no follow-ups" in out
