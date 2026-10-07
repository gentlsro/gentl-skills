---
name: gentl-task-tracking
description: Track the developer's ongoing work on a Gentl board through the Gentl Tasks MCP. Use automatically when the developer starts or resumes substantive work, including exploration, investigation, planning, implementation, debugging, review, testing, documentation, and maintenance, even without an assigned task, ticket, or explicit tracking request. Describe what they are doing, why, and meaningful progress with brief updates.
---

# Gentl Task Tracking

Keep a lightweight record of the developer's work so the team can understand what is happening and why.
The work drives tracking: a Gentl Task is its record, not a prerequisite. Exploration and investigation are useful
work even when they produce a finding or decision rather than a code change.

Tracking runs alongside the work. It must not block it or turn it into a reporting exercise. Read
[references/tool-cookbook.md](references/tool-cookbook.md) before the first tracking call for identity rules and calls.

## Start from the work

1. **Recognize substantive work.** Start tracking from the developer's request and the activity it leads to;
   do not wait for a task assignment, ticket number, special branch, or “track this” instruction. A request to
   investigate an issue, understand a codebase, compare approaches, or update documentation qualifies.
   Skip greetings, acknowledgments, and unrelated casual conversation. Respect a previous pause or stop;
   resume only when the developer asks.
2. **Find or create its record.** Reuse the active Task while the goal remains the same, including across
   exploration, implementation, and verification. If the developer identifies an existing Gentl Task or external
   item, use it. Otherwise infer a short title and purpose from the request and create a Task with a stable work
   correlation key from the cookbook. No repository or external tracker is required. Do not ask the developer to
   supply a task or invent a ticket number. When the goal changes to unrelated work, use a separate Task.
3. **Choose a board.** Use the existing Task's board. For new Tasks, call `get_task_tracking_context` and use the
   board the developer named; otherwise apply `boardSelectionInstructions`, when present, to the app, paths,
   and goal, considering both board names and descriptions. Routing takes precedence over `preferredBoard.board`.
   If no routing applies, use the resolved preferred board, else the only editable board. When routing is present,
   always pass the selected `boardId` explicitly. Ask if routing spans several apps or leaves the destination unclear;
   continue working while waiting. An existing Task stays on its board unless the developer requests a move. Read
   `get_board_task_metadata` for valid statuses, sprints, and permissions, and retain that context for the session.
   When adding a Task to a board, assign its active Sprint as described in the cookbook; respect an explicit
   developer sprint choice and preserve sprint assignments when resuming or updating an existing Task.
4. **Announce once** that tracking is on, which Task it writes to, and that brief work summaries are visible to the
   team. Honour “pause tracking” or “stop tracking” immediately; log one short pause note if possible, then stop
   writing until asked to resume.

Create one Task per coherent goal by default. Do not automatically create child steps, a checklist, or a fixed
number of subtasks. Use child Tasks only if the developer requests them or an existing board workflow requires them.
If resuming an older Task with steps, keep them intact; do not expand that structure by default.

## Describe the work, not every interaction

The Task needs a short description of **what the developer is doing and why**. Keep a brief current-state summary
when useful. Preserve existing human-written text; the cookbook explains safe description updates.

Post a short, plain-language comment when there is meaningful progress: an important finding, a change in direction
and its reason, a useful result, a blocker, or a stopping point. Combine related developments into one comment,
usually one to three sentences. At most one progress comment per turn by default; skip turns with no meaningful
change. For long work, checkpoint at a useful milestone.

For example:

> Investigating slow order exports because large downloads time out. The query appears fast; checking whether
> workbook generation accounts for the delay.

> Switched to streaming the workbook to reduce memory use. The export checks pass; a large-data run is still pending.

Summarize developer direction only when it explains the work or a change. Do not log every prompt, attribute every
decision, grade the developer, or require event labels and fields. Mention verification when it supports the result,
without copying command output or maintaining a separate test log. Do not invent a reason the developer has not
given; state the known purpose or leave it unspecified.

Never paste prompts verbatim. Exclude credentials, tokens, connection strings, personal or customer data, and
anything marked confidential from all new board text. Summarize sensitive material by its role instead.

## Status and stopping points

Move the Task to a status in an `IN_PROGRESS` column when work starts. Combine status and description changes
in one write when possible. Reopening requires clearing completion/archive fields as the cookbook shows.

When the developer pauses, switches goals, or ends the session, leave a brief account of where the work stands and
what remains, if anything. Do not treat a session ending as completion. Complete the Task when the developer
confirms that goal is done; for exploration, that can mean the requested finding or recommendation is accepted.
If completion returns several candidate statuses, ask which to use. A completed investigation does not imply that
any linked implementation, release, or external ticket is complete.

## Keep tracking unobtrusive

- Reuse the Task and board context. Read recent comments when resuming to avoid repeating updates.
- On a failed call, mention it once and continue working. Retry the pending update at the next meaningful
  checkpoint with the same `eventId`; do not repeatedly retry during that checkpoint.
- For `VALIDATION_ERROR`, use `details.problems` to correct the reference and retry once.
- If the board is read-only or returns `403 FORBIDDEN`, stop writing and explain briefly.
- If the MCP is disconnected, say so once, link to
  https://github.com/gentlsro/gentl-skills#connect-the-gentl-mcp-servers, and continue without tracking.
