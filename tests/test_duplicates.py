from __future__ import annotations

import json

from test_cli import ws  # noqa: F401  (the Workspace fixture)

PEOPLE = {
    "Priya Nair": "pn@example.com",
    "Priya Shah": "ps@example.com",
    "Rahul Mehta": "rm@example.com",
}


def meeting(date: str, attendees: str, *items: str, title: str = "Weekly") -> str:
    return f"# Meeting: {title}\nDate: {date}\nAttendees: {attendees}\n\n" + "".join(f"- {i}\n" for i in items)


def listed(ws, *args):  # noqa: F811
    code, out, _ = ws.run("list", "--json", "--today", "2026-12-01", *args)
    assert code == 0
    return json.loads(out)


def test_task_reworded_across_three_meetings_is_one_item_with_three_sources_and_the_latest_due(ws):  # noqa: F811
    ws.directory(PEOPLE)
    ws.note("a.md", meeting("2026-09-01", "Priya Nair, Rahul Mehta", "[ ] Priya Nair to send the revised quote to Acme by 2026-09-08"))
    ws.note("b.md", meeting("2026-09-08", "Priya Nair, Rahul Mehta", "[ ] Priya N. to send revised quote to Acme. by 2026-09-15"))
    ws.note("c.md", meeting("2026-09-15", "Priya Nair, Rahul Mehta", "[ ] Priya Nair to send the revised quote to Acme by 2026-09-22"))

    code, out, _ = ws.ingest()

    assert out.strip() == "3 notes read, 0 skipped, 1 new items, 2 merged, 0 need review"
    [item] = listed(ws)
    assert (item["id"], item["due"], item["status"]) == (1, "2026-09-22", "open")
    assert [(s["note"], s["line"], s["date"], s["title"]) for s in item["sources"]] == [
        ("a.md", 5, "2026-09-01", "Weekly"),
        ("b.md", 5, "2026-09-08", "Weekly"),
        ("c.md", 5, "2026-09-15", "Weekly"),
    ]


def test_meetings_are_processed_in_meeting_date_order_not_file_name_order(ws):  # noqa: F811
    ws.directory(PEOPLE)
    ws.note("a-late.md", meeting("2026-09-15", "Rahul Mehta", "[ ] Rahul to fix the build by 2026-09-30"))
    ws.note("z-early.md", meeting("2026-09-01", "Rahul Mehta", "[ ] Rahul to fix the build by 2026-09-10"))

    ws.ingest()

    [item] = listed(ws)
    assert item["due"] == "2026-09-30"
    assert item["sources"][0]["note"] == "z-early.md"


def test_item_ticked_in_a_middle_meeting_stays_done_when_a_later_meeting_lists_it_unticked(ws):  # noqa: F811
    ws.directory(PEOPLE)
    ws.note("a.md", meeting("2026-09-01", "Rahul Mehta", "[ ] Rahul to set up staging"))
    ws.note("b.md", meeting("2026-09-08", "Rahul Mehta", "[x] Rahul to set up staging"))
    ws.note("c.md", meeting("2026-09-15", "Rahul Mehta", "[ ] Rahul to set up staging"))

    ws.ingest()

    [item] = listed(ws)
    assert item["status"] == "done"
    assert len(item["sources"]) == 3


def test_different_tasks_stay_separate_and_a_borderline_pair_is_flagged_possible_duplicate(ws):  # noqa: F811
    ws.directory(PEOPLE)
    ws.note("a.md", meeting("2026-09-01", "Rahul Mehta", "[ ] Rahul to send the quote to Acme", "[ ] Rahul to send the quote to Acme by Friday"))
    ws.note("b.md", meeting("2026-09-08", "Rahul Mehta", "[ ] Rahul to book the venue", "[ ] Rahul to send the quote to Globex"))

    _, out, _ = ws.ingest()

    assert out.strip() == "2 notes read, 0 skipped, 3 new items, 1 merged, 1 need review"
    items = listed(ws)
    assert [i["task"] for i in items] == ["send the quote to Acme", "book the venue", "send the quote to Globex"]
    assert [f for i in items for f in i["flags"] if f["kind"] == "possible-duplicate"] == [
        {"kind": "possible-duplicate", "detail": "#1"}
    ]
    assert items[2]["flags"] == [{"kind": "possible-duplicate", "detail": "#1"}]


def test_ambiguous_owner_is_narrowed_by_a_later_single_person_repeat(ws):  # noqa: F811
    ws.directory(PEOPLE)
    both = "Priya Nair, Priya Shah"
    ws.note("a.md", meeting("2026-09-01", both, "[ ] Priya to send the quote"))
    ws.note("b.md", meeting("2026-09-08", both, "[ ] Priya N. to send the quote"))

    ws.ingest()

    [item] = listed(ws)
    assert item["owners"] == [{"name": "Priya Nair", "confirmed": True}]
    assert item["flags"] == []


def test_ambiguous_repeat_does_not_unconfirm_or_split_an_item(ws):  # noqa: F811
    ws.directory(PEOPLE)
    both = "Priya Nair, Priya Shah"
    ws.note("a.md", meeting("2026-09-01", both, "[ ] Priya Nair to send the quote"))
    ws.note("b.md", meeting("2026-09-08", both, "[ ] Priya to send the quote"))

    ws.ingest()

    [item] = listed(ws)
    assert item["owners"] == [{"name": "Priya Nair", "confirmed": True}]
    assert len(item["sources"]) == 2


def test_reingest_changes_nothing_and_reports_notes_unchanged(ws):  # noqa: F811
    ws.directory(PEOPLE)
    ws.note("a.md", meeting("2026-09-01", "Rahul Mehta", "[ ] Rahul to fix the build by 2026-09-10"))
    ws.note("b.md", meeting("2026-09-08", "Rahul Mehta", "[ ] Rahul to fix the build", "[x] Rahul to book the venue"))
    ws.ingest()
    first = ws.run("list", "--json", "--today", "2026-12-01")[1]

    _, out, _ = ws.ingest()

    assert out.strip() == "2 notes read, 0 skipped, 0 new items, 0 merged, 0 need review, 2 unchanged"
    assert ws.run("list", "--json", "--today", "2026-12-01")[1] == first


def test_new_note_adds_only_its_items_and_a_changed_note_merges_its_new_lines(ws):  # noqa: F811
    ws.directory(PEOPLE)
    ws.note("a.md", meeting("2026-09-01", "Rahul Mehta", "[ ] Rahul to fix the build by 2026-09-10"))
    ws.ingest()
    ws.note("b.md", meeting("2026-09-08", "Rahul Mehta", "[ ] Rahul to book the venue"))

    _, out, _ = ws.ingest()

    assert out.strip() == "2 notes read, 0 skipped, 1 new items, 0 merged, 0 need review, 1 unchanged"
    # a.md gains a ticked box, a rewritten due date and a new line
    ws.note("a.md", meeting("2026-09-01", "Rahul Mehta", "[x] Rahul to fix the build by 2026-09-12", "[ ] Rahul to write the report"))
    _, out, _ = ws.ingest()

    assert out.strip() == "2 notes read, 0 skipped, 1 new items, 1 merged, 0 need review, 1 unchanged"
    items = listed(ws)
    assert [(i["id"], i["task"], i["status"], i["due"]) for i in items] == [
        (1, "fix the build", "done", "2026-09-12"),
        (2, "book the venue", "open", None),
        (3, "write the report", "open", None),
    ]
    assert len(items[0]["sources"]) == 2
