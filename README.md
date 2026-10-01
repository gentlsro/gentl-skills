# Gentl skills

Agent skills and MCP connection settings for working with Gentl from coding agents such as
Claude Code, Codex, and Cursor.

| Skill | What it does |
| --- | --- |
| [`gentl-task-tracking`](skills/gentl-task-tracking/SKILL.md) | Keeps a Gentl board in step with your implementation while you work on a work item (Azure DevOps, GitLab, GitHub, Jira): the board Task, its implementation steps, the current plan, and a summarized log of how the work was steered. |

## Install a skill

```bash
npx skills add gentlsro/gentl-skills --skill gentl-task-tracking -g
```

`-g` installs it for all your projects; leave it out to install into the current repository only. The
[skills CLI](https://github.com/vercel-labs/skills) asks which agents to install for; pass `-a claude-code -a codex -a
cursor` to choose up front. Update later with `npx skills update`.

The skill needs the Gentl Tasks MCP connected (below). Once both are in place, start working on a work item as usual
("Picking up work item 1234 …"); the agent announces that tracking is on and which Task it writes to. Say "pause
tracking" or "stop tracking" at any time.

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

Issues and pull requests are welcome. The skill in this repository is published from the Gentl monorepo, where its
end-to-end test (a real coding agent driven through a scripted developer session) lives.
