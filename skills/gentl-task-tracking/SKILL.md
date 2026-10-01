---
name: gentl-task-tracking
description: Mirror a coding session onto a Gentl board through the Gentl Tasks MCP while the work happens. Use when a developer starts or resumes implementation work tied to a work item (Azure DevOps work item, GitLab or GitHub issue, Jira ticket, a pasted tracker URL or id, or a branch named after one), or asks to track, log, or report the work on the Gentl board. Keeps the board Task, its implementation steps, and a summarized log of the developer's prompts in sync as the plan changes.
---

# Gentl Task Tracking

Keep a Gentl board in step with an implementation as it happens. The board is read by people who did not watch the
session: a manager, a reviewer, the developer next week. They need to see **what is being built now**, **how the plan
changed and why**, and **how the developer drove the work** (the development approach), not only the final diff.

Tracking runs alongside the coding work. It never replaces it, blocks it, or slows it noticeably.

Tool calls, payloads, and message templates are in [references/tool-cookbook.md](references/tool-cookbook.md). Read
it before the first tracking call in a session.

## What lives where

| Board object | Holds | Changes when |
| --- | --- | --- |
| **Work item Task** (correlated with the external item) | Original request (untouched) plus an agent-owned `## Implementation tracking` section: goal, current approach, scope, step checklist, deviations | The plan, scope, or approach changes |
| **Step Tasks** (children of the work item) | One reviewable slice each (roughly a commit or PR-sized change), 3 to 8 per work item | A step is added, reshaped, started, finished, or dropped |
| **Comments on the work item** | Chronological session log: prompt summaries, plan changes, progress, verification, blockers, handoffs | Every substantive event |

Find Tasks by correlation (`provider` + `externalId`), never by remembered Gentl ids, so any session in any harness
can pick the thread up again.

## Session start

1. **Identify the work item.** Take it from the developer's message (URL or id), the branch name
   (`feature/1234-export`, `5678-fix-login`), or the tracker the developer names. If unclear, ask once. Build the
   correlation key with the tracker's tenancy (organization, site, or repository) as the cookbook shows; if there is no
   external item, use the git fallback there.
2. **Resume or create.** `get_task` by provider and externalId.
   - Found: read its description, its child steps, and the last few comments, then `get_board_task_metadata` for its
     board (statuses and your permissions). Continue from there. Do not recreate steps that exist.
   - Not found: `get_task_tracking_context` → pick the board: the one the developer named, else `preferredBoard.board`
     when the preference resolved, else the only board with `canEditTasks: true`. Ask only when several editable
     boards remain or the preference came back with a `problem` (board names can repeat, so show columns or ids), and
     keep coding while you wait → `get_board_task_metadata` → `upsert_tracked_task` for the work item, then one
     `upsert_tracked_task` per initial step.
   - `canEditTasks: false` on the board: tell the developer and stop tracking for this session.

   Keep the board id, status names, and the work item id for the rest of the session; do not fetch them again.
3. **Announce once, in one line**, that tracking is on, which Task it writes to, and that prompt summaries are logged
   for the team. The developer can say "pause tracking" or "stop tracking" at any time; honour it immediately and log
   one `paused` entry. Do not track silently.
4. **Log a `session-start` entry**: harness, branch, the developer's opening request summarized, and the initial plan
   or the point being resumed.

Initial steps can be few and coarse. They are expected to change; the record of how they change is part of the value.

## During the session

After each developer prompt, at the end of your turn (or earlier if the turn is long), decide which of these apply
and do them. Several can apply to one prompt.

| Event | Board update |
| --- | --- |
| Developer gives a substantive instruction, correction, question that redirects work, or decision | `prompt` entry |
| Requirement, scope, or approach changes (from the developer, from a discovery in the code, or from a stakeholder the developer quotes) | `plan-change` entry and rewrite the tracking section |
| New step needed | Upsert a new step Task; mention it in the `plan-change` entry |
| Step reshaped | Update the step's name and description; keep its externalId slug |
| Step dropped | `archive_tracked_task` on the step; say why in the `plan-change` entry. Never delete |
| Finished or dropped step needed again | Reopen it as the cookbook shows (clear `doneDate`, and `archivedAt` if archived); say why |
| Work starts on a step | Move the step (and the work item, the first time) to a status in an `IN_PROGRESS` column |
| Step implemented and checked | `complete_tracked_task` on the step; `progress` entry naming what was verified |
| Tests, builds, or manual checks run | `verification` entry: what ran, result, what was not covered |
| Waiting on someone or something | `blocker` entry; say who or what |
| Developer ends or hands off ("that's it for today", switching tasks) | `handoff` entry: where it stands, next concrete step, open questions. Only at the end of a session; mid-session status belongs in `progress` |

Fold trivial prompts ("yes", "go", "continue", "looks good") into the next substantive entry instead of logging them
alone. Several entries from one turn may share a comment; each still starts its own line with its bold kind
(`**prompt**`, `**plan-change**`, …) so readers and reports can tell them apart.

Keep the cost low: by default one checkpoint per turn, with one combined comment, at most one description rewrite,
and one call per Task whose name, description, or status changed (`upsert_tracked_task` takes them together).

## Prompt summaries: record the approach, do not grade it

Each `prompt` entry captures how the developer steered the work, in neutral factual language:

- **Asked**: the instruction or question in one or two sentences, in your words.
- **Context given**: constraints, examples, files, or reasons the developer supplied, or "none".
- **Decided by**: developer, or agent proposal accepted or modified by the developer.
- **Effect**: what changed in the code or the plan as a result (step ids where relevant).

Also note, when they happen: a correction of the agent's earlier output (what was wrong and what the developer asked
instead), the developer asking for or skipping verification, and rework of earlier steps.

Do not rate the developer, guess at intent you were not told, or editorialize. The reader does the assessment.

**Never paste prompts verbatim.** Summarize. Strip credentials, tokens, connection strings, personal data, customer
data, and any content the developer marks as confidential. When in doubt, describe the kind of content ("pasted a
stack trace from production") instead of the content.

The same applies to everything you write to the board, including the requester's text when you create the work item
from what the developer told you: restate it without secrets. Text that is already on the Task stays as it is.

## Keeping the description current

The work item's description is a snapshot of the current plan, not a log. When the plan changes, read the Task,
keep everything above the `## Implementation tracking` heading exactly as it is (that is the requester's text), and
rewrite the tracking section from the current state. `description` replaces the whole field, so read it immediately
before writing, never from earlier in the session, and change nothing outside the tracking section. Someone may edit
the Task between your read and your write; if the requester's text you read differs from what you last saw, mention
the change in your next log entry. Template in the cookbook.

## Finishing

- A **step** may be completed by you once it is implemented and checked.
- The **work item** is completed only when the developer confirms it is done (merged, released, or "done").
  Your belief that the work is finished is not enough. Before completing, post a `done` entry: final approach versus
  the original request, the deviations and who drove them, verification performed, and follow-ups left open.
- If `complete_tracked_task` returns candidate statuses instead of completing, ask the developer which one to use.
- Steps still open at completion: ask whether to complete, archive, or leave them for a follow-up.

## Failure handling

Tracking must never block coding.

- If a Gentl call fails, mention it once in a short line, keep working, and retry the pending updates at the next
  checkpoint. Reuse the same `eventId` on retry so nothing is logged twice.
- If the MCP is not connected at all, say so once, point the developer to
  https://github.com/gentlsro/gentl-skills#connect-the-gentl-mcp-servers, and continue without tracking.
- `VALIDATION_ERROR` lists the valid choices in `details.problems`; correct the reference and retry once.
- `403 FORBIDDEN`: the caller may only read that board. Stop writing to it and tell the developer.
