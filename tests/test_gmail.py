from __future__ import annotations

import json
import os
import stat

from actiontrack.cli import main
from actiontrack.gmail import ALLOWED_TOOLS
from test_cli import ws  # noqa: F401  (the Workspace fixture)
from test_followup import seeded

# A stand-in `claude`: records its argv and stdin, then behaves as MODE (env) says.
FAKE = """\
#!/bin/sh
/bin/cat > "$FAKE_DIR/stdin.$$"
echo "$@" > "$FAKE_DIR/argv.$$"
case "$FAKE_MODE" in
  ok) printf '%s\\n' '{"is_error": false, "result": "Done.\\nDRAFT_ID: r123"}' ;;
  nodraft) echo '{"is_error": false, "result": "I could not do that."}' ;;
  iserror) echo '{"is_error": true, "result": "DRAFT_ID: r1"}' ;;
  garbage) echo 'not json' ;;
  crash) echo boom >&2; exit 3 ;;
esac
"""


def fake_claude(tmp_path, monkeypatch, mode):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    exe = bin_dir / "claude"
    exe.write_text(FAKE)
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", str(bin_dir))  # only the fake is reachable
    monkeypatch.setenv("FAKE_DIR", str(tmp_path))
    monkeypatch.setenv("FAKE_MODE", mode)


def run_followup(ws, *args):  # noqa: F811
    ws._capsys.readouterr()
    code = main(["followup", "Rahul", "--yes", "--today", "2026-09-10", *args, "--db", str(ws.db), "--people", str(ws.people)])
    out, err = ws._capsys.readouterr()
    return code, out, err


def test_allowed_tools_is_exactly_create_draft():
    assert ALLOWED_TOOLS == ("mcp__claude_ai_Gmail__create_draft",)
    assert not any("send" in tool or "reply" in tool or "forward" in tool for tool in ALLOWED_TOOLS)


def test_email_reaches_claude_as_json_data_and_draft_is_reported(ws, tmp_path, monkeypatch):
    seeded(ws)
    fake_claude(tmp_path, monkeypatch, "ok")

    code, out, _ = run_followup(ws)

    assert code == 0 and "Created 1 drafts." in out
    (stdin,) = tmp_path.glob("stdin.*")
    (argv,) = tmp_path.glob("argv.*")
    text = stdin.read_text()
    data = json.loads(text[text.index("{"):])
    assert data["to"] == ["rahul.mehta@example.com"]
    assert data["subject"] == "Follow-up: 1 open"
    assert "audit contrast (due 2026-09-12; from kickoff.md, 2026-09-01)" in data["body"]
    assert "DATA" in text and "create_draft" in text
    assert "mcp__claude_ai_Gmail__create_draft" in argv.read_text()
    assert "--disallowedTools mcp__claude_ai_Gmail__send_message" in argv.read_text()


def test_claude_failures_exit_1_with_a_message(ws, tmp_path, monkeypatch):
    seeded(ws)
    for mode, message in [
        ("crash", "exited 3"),
        ("garbage", "unreadable"),
        ("iserror", "reported an error"),
        ("nodraft", "no DRAFT_ID"),
    ]:
        fake_claude_dir = tmp_path / mode
        fake_claude_dir.mkdir()
        fake_claude(fake_claude_dir, monkeypatch, mode)
        code, out, err = run_followup(ws)
        assert code == 1 and message in err and "Created" not in out


def test_missing_claude_exits_1(ws, tmp_path, monkeypatch):
    seeded(ws)
    monkeypatch.setenv("PATH", str(tmp_path))  # no claude here

    code, _, err = run_followup(ws)

    assert code == 1 and "`claude` command was not found" in err
