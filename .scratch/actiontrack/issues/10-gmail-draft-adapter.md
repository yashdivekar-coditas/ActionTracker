# 10: Create Gmail Drafts via `claude -p`

**What to build:** As described in ADR-0001, the real Draft sink runs `claude -p` with the allowed tools limited to the Gmail create-draft tool, passing each composed email as data, and reports the drafts created. Missing `claude`, a non-zero exit or an output showing no draft was created fails with exit 1 and a clear message, never a silent success. The allowed-tools list is a single constant.

**Blocked by:** 09

**Status:** done

- [x] A test asserts the allowed-tools constant contains exactly the Gmail create-draft tool and no send tool
- [x] A test with a fake `claude` executable on PATH proves the email content reaches it and that failures exit 1
- [ ] Verified by hand: one real `followup <owner> --yes` creates a draft visible in Gmail Drafts, and nothing appears in Sent

Spec: `.scratch/actiontrack/spec.md`

## Comments

- The "verified by hand" criterion is left for the orchestrator and the user: it is not yet known whether claude.ai connectors load in `-p` mode here.
- The prompt is piped on stdin, not passed as an argument, because `--allowedTools`/`--disallowedTools` are variadic and would swallow it.
- Removed `PrintSink` (the ticket 09 placeholder); `ClaudeSink` is the default for non-dry-run `followup`. Drafts run one `claude -p` call per email, so a failure on a later email leaves earlier drafts already created (no rollback; Drafts are harmless).
- Timeout is a 300s constant per call.
