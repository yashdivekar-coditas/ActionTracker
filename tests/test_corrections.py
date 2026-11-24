from __future__ import annotations

import json

from test_cli import ws  # noqa: F401  (the Workspace fixture)
from test_duplicates import PEOPLE, meeting


def listed(ws, *args):  # noqa: F811
    code, out, _ = ws.run("list", "--json", "--today", "2026-12-01", *args)
    assert code == 0
    return json.loads(out)


def by_id(ws, item_id):  # noqa: F811
    return next(i for i in listed(ws) if i["id"] == item_id)


def test_done_marks_the_item_done_echoes_it_and_a_reingest_of_an_unticked_copy_keeps_it_done(ws):  # noqa: F811
    ws.directory(PEOPLE)
    ws.note("a.md", meeting("2026-09-01", "Priya Nair, Rahul Mehta", "[ ] Rahul to review the pricing page"))
    ws.ingest()

    code, out, _ = ws.run("done", "1")

    assert code == 0
    assert "#1" in out and "review the pricing page" in out
    ws.note("b.md", meeting("2026-09-08", "Priya Nair, Rahul Mehta", "[ ] Rahul to review the pricing page"))
    ws.note("a.md", meeting("2026-09-01", "Priya Nair, Rahul Mehta", "[ ] Rahul to review the pricing page", "[ ] Rahul to book a room"))
    ws.ingest()
    assert by_id(ws, 1)["status"] == "done"


def test_edit_owner_on_an_ambiguous_item_leaves_one_confirmed_owner_and_survives_a_changed_note(ws):  # noqa: F811
    ws.directory(PEOPLE)
    ws.note("a.md", meeting("2026-09-01", "Priya Nair, Priya Shah", "[ ] Priya to send the revised quote to Acme"))
    ws.ingest()
    assert [f["kind"] for f in by_id(ws, 1)["flags"]] == ["ambiguous-owner"]

    code, out, _ = ws.run("edit", "1", "--owner", "Priya Nair")

    assert code == 0 and "Priya Nair" in out
    item = by_id(ws, 1)
    assert item["owners"] == [{"name": "Priya Nair", "confirmed": True}]
    assert item["flags"] == []
    # the note changes (new line) and a later meeting names the other Priya's initial: nothing is overwritten
    ws.note("a.md", meeting("2026-09-01", "Priya Nair, Priya Shah", "[ ] Priya to send the revised quote to Acme", "[ ] Rahul to book a room"))
    ws.note("b.md", meeting("2026-09-08", "Priya Nair, Priya Shah", "[ ] Priya to send the revised quote to Acme"))
    ws.ingest()
    item = by_id(ws, 1)
    assert item["owners"] == [{"name": "Priya Nair", "confirmed": True}]
    assert item["flags"] == []


def test_edit_owner_repeated_makes_a_group_and_clears_unowned(ws):  # noqa: F811
    ws.directory(PEOPLE)
    ws.note("a.md", meeting("2026-09-01", "Priya Nair, Rahul Mehta", "[ ] Someone to book a room"))
    ws.ingest()
    assert [f["kind"] for f in by_id(ws, 1)["flags"]] == ["unowned"]

    ws.run("edit", "1", "--owner", "Priya Nair", "--owner", "Rahul Mehta")

    item = by_id(ws, 1)
    assert [o["name"] for o in item["owners"]] == ["Priya Nair", "Rahul Mehta"]
    assert item["flags"] == []


def test_edit_due_clears_unresolved_due_and_a_later_ingest_keeps_the_date(ws):  # noqa: F811
    ws.directory(PEOPLE)
    ws.note("a.md", meeting("2026-09-01", "Priya Nair", "[ ] Priya to send the revised quote to Acme before cutover"))
    ws.ingest()
    assert [f["kind"] for f in by_id(ws, 1)["flags"]] == ["unresolved-due"]

    assert ws.run("edit", "1", "--due", "2026-10-20")[0] == 0

    item = by_id(ws, 1)
    assert (item["due"], item["flags"]) == ("2026-10-20", [])
    ws.note("b.md", meeting("2026-09-08", "Priya Nair", "[ ] Priya to send the revised quote to Acme by 2026-09-15"))
    ws.note("c.md", meeting("2026-09-15", "Priya Nair", "[ ] Priya to send the revised quote to Acme before cutover"))
    ws.ingest()
    item = by_id(ws, 1)
    assert (item["due"], item["flags"]) == ("2026-10-20", [])


def test_edit_task_changes_the_text_and_the_old_wording_still_merges_into_it(ws):  # noqa: F811
    ws.directory(PEOPLE)
    ws.note("a.md", meeting("2026-09-01", "Rahul Mehta", "[ ] Rahul to rvw prcng pge"))
    ws.ingest()

    assert ws.run("edit", "1", "--task", "Review the pricing page")[0] == 0
    ws.note("b.md", meeting("2026-09-08", "Rahul Mehta", "[ ] Rahul to rvw prcng pge!"))
    ws.ingest()

    [item] = listed(ws)
    assert item["task"] == "Review the pricing page"
    assert len(item["sources"]) == 2


def test_merge_joins_sources_keeps_done_clears_the_flag_and_is_not_undone_by_a_changed_note(ws):  # noqa: F811
    ws.directory(PEOPLE)
    ws.note("a.md", meeting("2026-09-01", "Rahul Mehta", "[ ] Rahul to send the quote to Acme"))
    ws.note("b.md", meeting("2026-09-08", "Rahul Mehta", "[x] Rahul to send the quote to Globex"))
    ws.ingest()
    one, two = listed(ws)
    assert two["flags"] == [{"kind": "possible-duplicate", "detail": "#1"}]
    assert two["status"] == "done"

    code, out, _ = ws.run("merge", "2", "1")

    assert code == 0 and "#1" in out
    [item] = listed(ws)
    assert (item["id"], item["status"], item["flags"]) == (1, "done", [])
    assert [s["note"] for s in item["sources"]] == ["a.md", "b.md"]
    # b.md changes (new line, old line kept) and a reworded copy of the merged-away wording arrives
    ws.note("b.md", meeting("2026-09-08", "Rahul Mehta", "[ ] Rahul to send the quote to Globex", "[ ] Rahul to book a room"))
    ws.note("c.md", meeting("2026-09-15", "Rahul Mehta", "[ ] Rahul to send the quote to Globex."))
    ws.ingest()
    items = listed(ws)
    assert [i["id"] for i in items] == [1, 3]
    assert (items[0]["status"], items[0]["flags"]) == ("done", [])
    assert [s["note"] for s in items[0]["sources"]] == ["a.md", "b.md", "c.md"]


def test_merge_removes_possible_duplicate_flags_other_items_held_against_the_merged_away_item(ws):  # noqa: F811
    ws.directory(PEOPLE)
    ws.note("a.md", meeting("2026-09-01", "Rahul Mehta", "[ ] Rahul to send the quote to Acme"))
    ws.note("b.md", meeting("2026-09-08", "Rahul Mehta", "[ ] Rahul to send the quote to Globex"))
    ws.ingest()

    ws.run("merge", "1", "2")  # the older item folds into the newer, which carried the flag

    [item] = listed(ws)
    assert (item["id"], item["flags"]) == (2, [])


def test_unknown_ids_exit_1_with_a_message(ws):  # noqa: F811
    ws.directory(PEOPLE)
    ws.note("a.md", meeting("2026-09-01", "Rahul Mehta", "[ ] Rahul to review the pricing page"))
    ws.ingest()

    for args in (("done", "9"), ("edit", "9", "--task", "x"), ("merge", "9", "1"), ("merge", "1", "9"), ("merge", "1", "1")):
        code, _, err = ws.run(*args)
        assert code == 1 and err.startswith("error:"), args
    assert "9" in ws.run("done", "9")[2]
    assert by_id(ws, 1)["status"] == "open"


def test_edit_with_nothing_to_change_or_an_invalid_date_is_refused(ws):  # noqa: F811
    ws.directory(PEOPLE)
    ws.note("a.md", meeting("2026-09-01", "Rahul Mehta", "[ ] Rahul to review the pricing page"))
    ws.ingest()

    assert ws.run("edit", "1")[0] == 2
    assert ws.run("edit", "1", "--due", "soon")[0] == 2
