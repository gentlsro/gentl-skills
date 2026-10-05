# Gentl skills

Agent skills and MCP connection settings for working with Gentl from coding agents such as
Claude Code, Codex, and Cursor.

| Skill | What it does |
| --- | --- |
| [`gentl-task-tracking`](skills/gentl-task-tracking/SKILL.md) | Tracks ongoing work, including exploration, implementation, review, and documentation, with brief descriptions of what you're doing, why, and meaningful progress. No assigned task or external ticket required. |

## Install a skill

```bash
npx skills add gentlsro/gentl-skills --skill gentl-task-tracking -g
```

`-g` installs it for all your projects; leave it out to install into the current repository only. The
[skills CLI](https://github.com/vercel-labs/skills) asks which agents to install for; pass `-a claude-code -a codex -a
cursor` to choose up front. Update later with `npx skills update`.

The skill needs the Gentl Tasks MCP connected (below). Once both are in place, start substantive work as usual
("Investigate why exports are slow" or "Update the setup docs"). The skill is intended for automatic selection by
the agent from the work being done; it finds or creates a Gentl Task and announces tracking. An existing Gentl Task
or Azure DevOps, GitLab, GitHub, or Jira item can be used when available, but is optional. Tracking normally uses
one Task per goal and short updates at meaningful milestones, without a prompt-by-prompt log or automatic subtasks.
Say "pause tracking" or "stop tracking" at any time, and ask to resume when ready.

## Connect the Gentl MCP servers

| Server | Endpoint | Used for |
| --- | --- | --- |
| Gentl Tasks MCP (`gentl-tasks`) | `https://<your-gentl-host>/api/mcp/gentl` | Boards and Tasks; required by `gentl-task-tracking` |
| Gentl Editor MCP (`gentl-editor`) | `https://<your-gentl-host>/api/mcp` | Inspecting and editing an open DynamicGrid editor session |

You need three values:

- **Gentl host**: the address you open Gentl at.
- **API key**: create one in Gentl under **My account → API keys and credentials**. It acts as you, with your
  permissions. Keep it out of files and repositories: the settings below read it from the `GENTL_API_KEY` environment
  variable, so set that in your shell profile (`export GENTL_API_KEY=…`).
- **Instance id**: the id of the Gentl instance to work in. Ask your Gentl administrator if you do not know it.

Replace `<your-gentl-host>` and `<your-instance-id>` in the snippet for your agent:

| Agent | Settings file | Snippet |
| --- | --- | --- |
| Claude Code | `.mcp.json` in a repository, or `claude mcp add-json` (below) | [`mcp/claude-code.mcp.json`](mcp/claude-code.mcp.json) |
| Codex | `~/.codex/config.toml` | [`mcp/codex.config.toml`](mcp/codex.config.toml) |
| Cursor | `~/.cursor/mcp.json` or `.cursor/mcp.json` | [`mcp/cursor.mcp.json`](mcp/cursor.mcp.json) |

For Claude Code across all your projects, add the servers to your user settings. The single quotes keep
`${GENTL_API_KEY}` unexpanded, so Claude Code reads the key from your environment each time instead of storing it:

```bash
claude mcp add-json gentl-tasks --scope user '{"type":"http","url":"https://<your-gentl-host>/api/mcp/gentl","headers":{"Authorization":"Bearer ${GENTL_API_KEY}","X-Instance-Id":"<your-instance-id>"}}'
```

```bash
claude mcp add-json gentl-editor --scope user '{"type":"http","url":"https://<your-gentl-host>/api/mcp","headers":{"Authorization":"Bearer ${GENTL_API_KEY}","X-Instance-Id":"<your-instance-id>"}}'
```

Optional: add an `X-Gentl-Preferred-Board` header (board id or name) to the Tasks MCP so agents use that board unless
you name another one.

### Using the Editor MCP

Open a grid in the Gentl editor and use its connect button. It gives you a short message with a session id and a
6-digit pairing code; paste it to your agent. The agent attaches to that editor session and works on the unsaved grid
in your browser; saving and publishing stay with you.

## Feedback

Issues and pull requests are welcome. The skills live in this repository. The Gentl MCP servers they use, and the
end-to-end test that drives `gentl-task-tracking` with a real coding agent through a scripted developer session, live
in the Gentl monorepo.
