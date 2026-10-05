# Gentl Task Tracking: tool cookbook

Use these Gentl Tasks MCP calls for lightweight work tracking. Connection settings:
https://github.com/gentlsro/gentl-skills#connect-the-gentl-mcp-servers

## Work identity

Use the active Task's identity throughout a coherent goal. A ticket is optional; a branch is context, not sufficient
identity for new work. Different investigations on the same branch must not silently share a Task.

| Source | `provider` | `externalId` | `url` |
| --- | --- | --- | --- |
| Azure DevOps work item | `azure-devops` | `<organization>/<id>`, e.g. `acme/18342` | work item URL |
| GitLab issue | `gitlab` | `<host>/<group>/<project>#<iid>`, e.g. `gitlab.com/acme/shop#311` | issue URL |
| GitHub issue | `github` | `<owner>/<repo>#<number>`, e.g. `acme/shop#87` | issue URL |
| Jira ticket | `jira` | `<site>/<key>`, e.g. `acme.atlassian.net/SHOP-512` | ticket URL |
| Work without an external item | `gentl-work` | `work/<UUID generated once for this goal>` | omit |

- For an explicit Gentl Task, retrieve it with the selector exposed by `get_task`. Reuse an existing external
  reference when available. If it has none, use the semantic Task tools exposed by the server with that Task's id;
  do not create a duplicate just to gain a correlation key.
- Keep a generated work key in the session context and on the created Task through `upsert_tracked_task`.
  Reuse it on retries and continued work; never generate a new key for each turn or phase.
- When resuming in a new session, use an explicit Task/reference or search the selected board using `find_tasks`
  or `query_tasks`, as exposed by the server. Read the description and recent comments to establish continuity
  with the goal. Reuse a clear match; a shared branch or similar title alone is not enough. If several plausible
  matches remain, ask which to resume while continuing the work. Create a record if none matches.
- External ids need tenancy, as shown above. Take it from the URL or repository remote. If a bare ticket number
  cannot be resolved, start a work record rather than making that missing context a prerequisite; ask for the
  tracker context only when needed to link it correctly. `provider` is lowercased by Gentl; `externalId` is
  case-sensitive and trimmed. Use the same spelling every time; lowercase hosts and organizations.
- Older records may use `git` with `<remote host>/<repo path>#<branch>`. Resume them when their goal matches;
  do not create new records with that branch-only identity.
- If a ticket is supplied later, look up its correlation first. If it already belongs to another Task, show both
  records and ask which to continue; do not silently switch or duplicate the work. Otherwise attach it to the
  current Task as shown below. Keep the existing work reference too.

## Attach a tracker item to an existing Task

When `upsert_tracked_task` exposes `taskId`, attach the item without creating a second Task:

```json
upsert_tracked_task {
  "provider": "gitlab",
  "externalId": "gitlab.com/acme/shop#311",
  "taskId": "<current Task id>",
  "url": "https://gitlab.com/acme/shop/-/issues/311",
  "metadata": { "source": "gentl-task-tracking" }
}
```

The reply has `created: false`. Repeating the call is safe, and a Task may carry several correlations.
`CONFLICT` with `details.taskId` means the key belongs to that other Task: show both and ask which to continue.
Do not retry with a changed key or another Task id. `NOT_FOUND` or `FORBIDDEN` means nothing was attached.
If the exposed schema lacks `taskId`, note the URL on the current Task and keep its existing addressing.

## Find, choose a board, and create

```json
get_task { "by": "external_reference", "provider": "gentl-work", "externalId": "work/<UUID>" }
```

`NOT_FOUND` means there is no record for that key. `CORRELATION_NOT_FOUND` from a tracked write means the key
was not found; check its spelling instead of blindly creating another Task.

For a found Task, read its description and recent comments:

```json
query_tasks {
  "where": { "id": "<Task id>" },
  "select": {
    "description": true,
    "comments": { "select": { "message": true, "createdAt": true }, "orderBy": { "createdAt": "desc" }, "take": 3 }
  }
}
```

For a new record, resolve the board:

```json
get_task_tracking_context {}
```

Use the board the developer named. Otherwise, when `boardSelectionInstructions` is present, apply it to the app,
paths, and goal using board names and descriptions, and choose only a board with `canEditTasks: true`. Routing
wins over a literal preferred board. If no routing applies, use resolved `preferredBoard.board`, else the only
editable board. Whenever routing is configured, pass `boardId` explicitly on board-dependent calls, including
when using a fallback. Ask if the destination or ownership of shared work is unclear; do not infer one board for
unrelated work across apps. Older MCP deployments omit the instructions field; use the ordinary defaults there.
A preference may return `problem: "not_found"` or `problem: "ambiguous"` with candidates. Ask about an unresolved
destination; board names can repeat, so show ids or columns. Do not write to an arbitrary board while waiting.

```json
get_board_task_metadata { "boardId": "<board id>" }
```

Use valid names from the metadata. Choose status by the column's `processState` (`INACTIVE`, `IN_PROGRESS`,
`DONE`), not by guessing from names. Omit optional type, priority, assignee, and other fields unless useful and known.

```json
upsert_tracked_task {
  "provider": "gentl-work",
  "externalId": "work/<UUID>",
  "boardId": "<board id>",
  "name": "Investigate slow order exports",
  "status": "<status in an IN_PROGRESS column>",
  "description": "Investigating why large order downloads time out so we can choose an appropriate fix."
}
```

`name` and `boardId` are required on creation only. For a known external item, substitute its key and URL.
Use its title when suitable; describe the actual work, including investigation before implementation.

## Progress and current state

```json
record_task_progress {
  "provider": "gentl-work",
  "externalId": "work/<UUID>",
  "eventId": "2026-10-05T09:22:05Z-progress-k3f9q2",
  "message": "The query is fast; workbook generation appears to cause the delay. Checking a streaming approach before deciding on a fix."
}
```

Make a unique `eventId` for each comment, such as `<UTC timestamp>-progress-<random suffix>`. Reuse it unchanged
when retrying that exact comment. Gentl returns the existing comment for a repeated id without comparing text;
reusing it for new text drops that update, while retrying with a new id duplicates the comment.
A new Task's description can serve as the opening summary; do not duplicate it in a comment by default.

Update the description only when the goal or current state materially changes. For an existing Task:

1. Read the description immediately before writing; `description` replaces the whole field.
2. Preserve human-written text. Add or update a short agent-owned `## Work tracking` section.
   If the Task has the older `## Implementation tracking` section, update that section in place instead of
   appending another. Preserve anything outside the agent-owned section, including later human-added sections.
   If ownership is unclear, use a comment rather than rewriting text.
3. Write the preserved text and the updated section together, combining any status change in the same call.

A sufficient section is:

```markdown
## Work tracking

Investigating export timeouts to choose a fix. The database query is fast; checking workbook streaming next.
```

```json
upsert_tracked_task { "provider": "gentl-work", "externalId": "work/<UUID>", "status": "<IN_PROGRESS status>", "description": "<preserved text and short tracking section>" }
```

For native Tasks without correlation, use `get_task { "by": "id", "id": "<Task id>" }`,
`add_task_comment { "taskId": "<Task id>", "message": "<brief summary>" }`, and
`update_task { "taskId": "<Task id>", "status": "<valid status>", "description": "<preserved text>" }`.
Native comments are not deduplicated: after a timeout or dropped connection, read recent comments before retrying,
and retry only if the comment is missing. Use the same summary and preservation rules.

## Reopen and finish

```json
upsert_tracked_task { "provider": "gentl-work", "externalId": "work/<UUID>", "status": "<IN_PROGRESS status>", "doneDate": null, "archivedAt": null }
```

A status move alone does not clear completion or archive fields.

After the developer confirms the goal is done, leave a brief result comment if not already recorded, then:

```json
complete_tracked_task { "provider": "gentl-work", "externalId": "work/<UUID>" }
```

Without `status`, this picks the sole status in the board's `DONE` column. If it returns candidate statuses, ask
which one to use. An investigation result is a valid outcome; do not imply that a proposed fix was implemented.
For native Tasks without correlation, use `update_task` with `taskId`, a status from the board's `DONE` column,
and `doneDate` set to the current UTC timestamp. Ask if several completion statuses remain.

## Older Gentl deployments

Before semantic Task tools, take status ids from `get_task_tracking_context` and pass `statusId` to
`upsert_tracked_task`. These deployments resolve no names: use `typeId`, `priorityId`, `tagIds`, and
`assignedUserIds`, or omit them. The correlation tools (`upsert_tracked_task`, `record_task_progress`,
`complete_tracked_task`, `archive_tracked_task`, `get_task`) behave the same.
