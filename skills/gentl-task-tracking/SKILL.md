---
name: gentl-task-tracking
description: Mirror a working session onto a Gentl board through the Gentl Tasks MCP while the work happens: implementation, bug fixing, research, investigation, design, or any other work done with an agent. Use when the developer names a Gentl Task (board number like #412, or its name), references a tracker item (Azure DevOps work item, GitLab or GitHub issue, Jira ticket, a pasted URL or id, or a branch named after one), or asks to track, log, or report the work on the Gentl board. Keeps the board Task, its steps, and a summarized log of the developer's prompts in sync as the plan changes.
---

# Gentl Task Tracking

Keep a Gentl board in step with the work as it happens. The board is read by people who did not watch the session: a
manager, a reviewer, the developer next week. They need to see **what is being done now**, **how the plan changed and
why**, and **how the developer drove the work** (the approach), not only the final result.

The work can be anything done in an agent session: code, a bug investigation, research, a comparison of options, a
design or a document. Tracking does not assume a repository, a branch, or a ticket. The **Gentl Task is the anchor**;
a tracker item (Azure DevOps, GitLab, GitHub, Jira) is extra context when there is one.

Tracking runs alongside the work. It never replaces it, blocks it, or slows it noticeably.

Tool calls, payloads, and message templates are in [references/tool-cookbook.md](references/tool-cookbook.md). Read
it before the first tracking call in a session.

## What lives where

| Board object | Holds | Changes when |
| --- | --- | --- |
| **Work Task** | The original request (untouched) plus an agent-owned `## Work tracking` section: goal, current approach, scope, step checklist, deviations, linked items | The plan, scope, or approach changes |
| **Step Tasks** (children of the work Task) | One reviewable slice each, 3 to 8 per work Task: a change worth reviewing on its own, a question answered, an option evaluated, a draft written | A step is added, reshaped, started, finished, or dropped |
| **Comments on the work Task** | Chronological session log: prompt summaries, plan changes, progress, verification, blockers, handoffs | Every substantive event |

## How the work Task is addressed

A work Task is addressed in one of two ways, decided once at session start and kept for the session:

- **Correlated**: the work comes from a tracker item. The Task is found and written through `provider` + `externalId`
  (the tracked tools), so any session in any harness finds it again from the tracker reference, and retried log
  entries are never posted twice.
- **Board-native**: there is no tracker item. The Task is found by its name or board number with `find_tasks` and
  written by its Gentl id. Another session finds it again the same way, from what the developer calls the work.

Never rely on Gentl ids remembered from an earlier session; look the Task up again each session.

## Session start

1. **Identify the work.** In this order:
   - The developer names a Gentl Task (board number `#412`, its name, or words from it): `find_tasks`. One clear
     match: use it. Several plausible matches: show them (name, board number, board, status) and ask once.
   - The developer references a tracker item (URL, id, or a branch named after one): build the correlation key as the
     cookbook shows and `get_task` by it.
   - Neither, but the developer asked to track the work: `find_tasks` with the main words of the request to catch an
     existing Task. Nothing fits: create a new board-native Task named after the work.
   - Ask once only when you cannot tell which of these applies. Keep working while you wait.
2. **Resume or create.**
   - Found: read its description, its child steps, and the last few comments, then `get_board_task_metadata` for its
     board (statuses and your permissions). Continue from there. Do not recreate steps that exist. A Task found by
     name that carries a correlation written by this skill (a step reference ending in `/step-…`, or a reference
     whose metadata has `source: gentl-task-tracking`) is correlated: keep using that key.
   - Not found: `get_task_tracking_context` → pick the board: the one the developer named, else `preferredBoard.board`
     when the preference resolved, else the only board with `canEditTasks: true`. Ask only when several editable
     boards remain or the preference came back with a `problem` (board names can repeat, so show columns or ids) →
     `get_board_task_metadata` → create the work Task (correlated: `upsert_tracked_task`; board-native:
     `create_task`), then one step Task per initial step.
   - `canEditTasks: false` on the board: tell the developer and stop tracking for this session.

   Keep the board id, status names, the work Task id, and its addressing for the rest of the session; do not fetch
   them again.
3. **Announce once, in one line**, that tracking is on, which Task it writes to (name and board number), and that
   prompt summaries are logged for the team. The developer can say "pause tracking" or "stop tracking" at any time;
   honour it immediately and log one `paused` entry. Do not track silently.
4. **Log a `session-start` entry**: harness, the working context that exists (repository and branch for code; the
   question or deliverable for other work), the developer's opening request summarized, and the initial plan or the
   point being resumed.

Initial steps can be few and coarse. They are expected to change; the record of how they change is part of the value.

A tracker item that turns up later for a board-native Task (the developer pastes an issue link mid-session) goes into
the tracking section under **Linked items** and gets a `plan-change` entry. Keep the Task board-native; do not create
a second, correlated Task for the same work.

## During the session

After each developer prompt, at the end of your turn (or earlier if the turn is long), decide which of these apply
and do them. Several can apply to one prompt.

| Event | Board update |
| --- | --- |
| Developer gives a substantive instruction, correction, question that redirects work, or decision | `prompt` entry |
| Requirement, scope, or approach changes (from the developer, from a discovery in the code or the sources, or from a stakeholder the developer quotes) | `plan-change` entry and rewrite the tracking section |
| New step needed | Create a new step Task; mention it in the `plan-change` entry |
| Step reshaped | Update the step's name and description; keep its identity (correlated: its externalId slug) |
| Step dropped | Archive the step; say why in the `plan-change` entry. Never delete |
| Finished or dropped step needed again | Reopen it as the cookbook shows (clear `doneDate`, and `archivedAt` if archived); say why |
| Work starts on a step | Move the step (and the work Task, the first time) to a status in an `IN_PROGRESS` column |
| Step done and checked | Complete the step; `progress` entry naming what was checked |
| A result is checked: tests or builds run, a finding confirmed against a source, an experiment or measurement made, a draft reviewed | `verification` entry: what was checked and how, the result, what was not covered |
| Waiting on someone or something | `blocker` entry; say who or what |
| Developer ends or hands off ("that's it for today", switching tasks) | `handoff` entry: where it stands, next concrete step, open questions. Only at the end of a session; mid-session status belongs in `progress` |

Fold trivial prompts ("yes", "go", "continue", "looks good") into the next substantive entry instead of logging them
alone. Several entries from one turn may share a comment; each still starts its own line with its bold kind
(`**prompt**`, `**plan-change**`, …) so readers and reports can tell them apart.

Keep the cost low: by default one checkpoint per turn, with one combined comment, at most one description rewrite,
and one call per Task whose name, description, or status changed (name, description, and status go in one call).

## Prompt summaries: record the approach, do not grade it

Each `prompt` entry captures how the developer steered the work, in neutral factual language:

- **Asked**: the instruction or question in one or two sentences, in your words.
- **Context given**: constraints, examples, files, sources, or reasons the developer supplied, or "none".
- **Decided by**: developer, or agent proposal accepted or modified by the developer.
- **Effect**: what changed in the work or the plan as a result (step numbers where relevant).

Also note, when they happen: a correction of the agent's earlier output (what was wrong and what the developer asked
instead), the developer asking for or skipping verification, and rework of earlier steps.

Do not rate the developer, guess at intent you were not told, or editorialize. The reader does the assessment.

**Never paste prompts verbatim.** Summarize. Strip credentials, tokens, connection strings, personal data, customer
data, and any content the developer marks as confidential. When in doubt, describe the kind of content ("pasted a
stack trace from production", "shared an internal pricing sheet") instead of the content.

The same applies to everything you write to the board, including the request text when you create the work Task
from what the developer told you: restate it without secrets. Text that is already on the Task stays as it is.

## Keeping the description current

The work Task's description is a snapshot of the current plan, not a log. When the plan changes, read the Task, keep
everything above the `## Work tracking` heading exactly as it is (that is the requester's text), and rewrite the
tracking section from the current state. A Task tracked by an earlier version of this skill has the heading
`## Implementation tracking` instead; treat it as the same section and write it back as `## Work tracking`.

`description` replaces the whole field, so read it immediately before writing, never from earlier in the session, and
change nothing outside the tracking section. Someone may edit the Task between your read and your write; if the
requester's text you read differs from what you last saw, mention the change in your next log entry. Template in the
cookbook.

## Finishing

- A **step** may be completed by you once it is done and checked.
- The **work Task** is completed only when the developer confirms it is done: merged or released for code; findings
  accepted, a decision taken, or the document delivered for other work; or simply "done". Your belief that the work
  is finished is not enough. Before completing, post a `done` entry: the outcome versus the original request, the
  deviations and who drove them, verification performed, and follow-ups left open.
- If completing returns candidate statuses instead of completing (correlated), or the board's `DONE` column has
  several statuses (board-native), ask the developer which one to use.
- Steps still open at completion: ask whether to complete, archive, or leave them for a follow-up.

## Failure handling

Tracking must never block the work.

- If a Gentl call fails, mention it once in a short line, keep working, and retry the pending updates at the next
  checkpoint. Correlated: reuse the same `eventId` on retry so nothing is logged twice. Board-native comments have no
  such protection: when a comment call failed without a clear error (timeout, dropped connection), read the latest
  comments first and retry only if it is not there.
- If the MCP is not connected at all, say so once, point the developer to
  https://github.com/gentlsro/gentl-skills#connect-the-gentl-mcp-servers, and continue without tracking.
- `VALIDATION_ERROR` lists the valid choices in `details.problems`; correct the reference and retry once.
- `403 FORBIDDEN`: the caller may only read that board. Stop writing to it and tell the developer.
