# Gmail drafts are created by shelling out to `claude -p` with only `create_draft` allowed

The brief requires drafts "through the Gmail MCP connector", but that connector lives inside a Claude session, not on the network where a plain CLI can reach it. `actiontrack followup` composes each Follow-up itself, then runs `claude -p` with `--allowedTools` limited to the Gmail `create_draft` tool, so the connector's `send_message` can never be invoked. `--dry-run` prints the drafts instead. Composing the email in our code (not in the prompt) keeps the content deterministic and testable.

## Considered Options

- CLI emits JSON, a Claude Code slash command creates drafts: simpler, but the CLI alone can't finish the job.
- Self-hosted Gmail MCP server the CLI talks to as an MCP client: needs Google OAuth setup and infra, out of scope.

## Consequences

`followup` needs the `claude` binary on PATH and a session with the Gmail connector authorised; drafting fails loudly (not silently) when it isn't.
