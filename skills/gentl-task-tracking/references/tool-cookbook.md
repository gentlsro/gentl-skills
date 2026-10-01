# Gentl Task Tracking: tool cookbook

Exact Gentl Tasks MCP calls and message templates for the `gentl-task-tracking` skill. Connecting the MCP to a
harness: https://github.com/gentlsro/gentl-skills#connect-the-gentl-mcp-servers

## Correlation keys

| Source | `provider` | `externalId` | `url` |
| --- | --- | --- | --- |
| Azure DevOps work item | `azure-devops` | `<organization>/<id>`, e.g. `acme/18342` | the work item URL |
| GitLab issue | `gitlab` | `<host>/<group>/<project>#<iid>`, e.g. `gitlab.com/acme/shop#311` | the issue URL |
| GitHub issue | `github` | `<owner>/<repo>#<number>`, e.g. `acme/shop#87` | the issue URL |
| Jira ticket | `jira` | `<site>/<key>`, e.g. `acme.atlassian.net/SHOP-512` | the ticket URL |
| No external item | `git` | `<remote host>/<repo path>#<branch>`, e.g. `github.com/acme/shop#feature/csv-export` | omit |
| Step of any of the above | same as the work item | `<work item externalId>/step-<slug>` | omit |

- Tracker ids are only unique within an organization, site, or repository, and one Gentl instance can serve several,
  so the key carries that tenancy. Take it from the item URL, else from `git remote get-url origin` (Azure DevOps and
  GitLab remotes name the organization or group). If the developer gives only a bare id and neither source says where
  it lives, ask once.
- `provider` is lowercased by Gentl. `externalId` is **case-sensitive** and trimmed: write it exactly the same way
  every time; lowercase hosts and organizations.
- A step slug is short kebab-case derived from the step's first name (`step-xlsx-writer`). It never changes, even
  when the step is renamed or reshaped, because it is the step's identity.
- The `git` fallback is tied to the branch. If the developer later names a real work item, create the tracked Task
  for it and post a `plan-change` entry on both Tasks linking them; do not try to move the correlation.

## Session start

### Find an existing work item Task

```json
get_task { "by": "external_reference", "provider": "azure-devops", "externalId": "acme/18342" }
```

`NOT_FOUND` means it is not tracked yet. (`CORRELATION_NOT_FOUND` from a tracked *write* means the externalId was
spelled differently; fix the key, do not create a second Task.) On success, load its steps and recent log:

```json
query_tasks {
  "where": { "parentId": "<work item id>" },
  "select": {
    "id": true, "uuid": true, "name": true, "archivedAt": true, "doneDate": true,
    "status": { "select": { "name": true } },
    "externalReferences": { "select": { "externalId": true } }
  },
  "orderBy": { "position": "asc" }
}
```

```json
query_tasks {
  "where": { "id": "<work item id>" },
  "select": {
    "description": true,
    "comments": { "select": { "message": true, "createdAt": true }, "orderBy": { "createdAt": "desc" }, "take": 8 }
  }
}
```

### Pick the board and read its metadata

```json
get_task_tracking_context {}
```

Board choice, in order: the board the developer named; `preferredBoard.board` (the preference resolved); the only
board with `canEditTasks: true`. `preferredBoard` can instead be `{ "reference", "problem": "not_found" }` or
`{ "reference", "problem": "ambiguous", "candidates": [...] }`; then ask, showing the candidates. Board names can
repeat, so confirm by column names or id. Each column has a `processState`: `INACTIVE` (backlog, upcoming),
`IN_PROGRESS`, or `DONE`. Map lifecycle moves to statuses by that, not by guessing from names.

```json
get_board_task_metadata { "boardId": "<board id>" }
```

Gives statuses, Task types, priorities, tags, assignable users, sprints, custom fields, and the caller's permissions.
Pass names from this response afterwards (`"status": "Ongoing"`, `"type": "Bug"`).

### Create the work item Task

```json
upsert_tracked_task {
  "provider": "azure-devops",
  "externalId": "acme/18342",
  "url": "https://dev.azure.com/acme/shop/_workitems/edit/18342",
  "metadata": { "source": "gentl-task-tracking", "harness": "claude-code", "repo": "shop", "branch": "feature/18342-export" },
  "boardId": "<board id>",
  "name": "Export orders to Excel",
  "type": "Feature",
  "status": "Upcoming",
  "assignees": ["<developer email, if known and assignable>"],
  "description": "<requester's text, then the tracking section>"
}
```

- `name` and `boardId` are required on the first call only. Use the work item's own title.
- `type`: the board type closest to the tracker's (Bug, Feature, Story, Task); omit when nothing fits.
- Put the request above the tracking section, restated in your words without secrets, credentials, or personal or
  customer data (the summary rules in SKILL.md apply). If you could not read the original item, write what the
  developer told you and say so. On an existing Task, leave the text above the tracking section untouched.

### Create a step

```json
upsert_tracked_task {
  "provider": "azure-devops",
  "externalId": "acme/18342/step-xlsx-writer",
  "boardId": "<board id>",
  "parent": "<work item Task id>",
  "name": "Write orders to XLSX with exceljs",
  "status": "Upcoming",
  "description": "What this step delivers and how it will be checked."
}
```

## During the session

### Log entry

```json
record_task_progress {
  "provider": "azure-devops",
  "externalId": "acme/18342",
  "eventId": "2026-10-01T14:22:05Z-prompt-k3f9q2",
  "message": "<entry markdown>"
}
```

`eventId` is `<UTC timestamp when you composed the comment>-<first kind in it>-<6 random lowercase letters or digits>`,
e.g. `2026-10-01T14:22:05Z-prompt-k3f9q2`. Make a new one for every comment and reuse it unchanged on every retry
of that comment. Gentl keeps one comment per event id on a tracked Task and returns the existing comment for a repeated
id without comparing the text, so a reused id silently drops the new comment, and a retry with a new id duplicates it.
Always log on the **work item**, not on steps.

### Move a step or the work item

```json
upsert_tracked_task { "provider": "azure-devops", "externalId": "acme/18342/step-xlsx-writer", "status": "Ongoing" }
```

Use a status in an `IN_PROGRESS` column. The first time any step starts, move the work item the same way.
Combine a status change with any name or description change for the same Task in one call.

### Reopen a finished or dropped step

```json
upsert_tracked_task { "provider": "azure-devops", "externalId": "acme/18342/step-xlsx-writer", "status": "Ongoing", "doneDate": null, "archivedAt": null }
```

A status move alone leaves `doneDate` (and `archivedAt`) set, so the step would still count as finished or stay
hidden. Update its line in the tracking section's checklist too.

### Reshape a step

```json
upsert_tracked_task {
  "provider": "azure-devops",
  "externalId": "acme/18342/step-xlsx-writer",
  "name": "Write orders to XLSX with a streaming writer",
  "description": "..."
}
```

### Finish or drop a step

```json
complete_tracked_task { "provider": "azure-devops", "externalId": "acme/18342/step-xlsx-writer" }
```

```json
archive_tracked_task { "provider": "azure-devops", "externalId": "acme/18342/step-csv-serializer" }
```

`complete_tracked_task` without `status` picks the sole status of the board's `DONE` column. When it returns
candidates instead, ask the developer and pass the chosen `status`.

### Rewrite the tracking section

1. `get_task { "by": "external_reference", ... }` and take `description`.
2. Keep everything before the line `## Implementation tracking` byte for byte. If the heading is missing, keep the
   whole description and append the section.
3. `upsert_tracked_task { "provider": ..., "externalId": ..., "description": "<kept text>\n\n<new section>" }`.

## Templates

### Tracking section (work item description)

```markdown
## Implementation tracking

_Maintained by the developer's coding agent. Last updated 2026-10-01 14:40 UTC (claude-code, branch `feature/18342-export`)._

**Goal:** Finance can download the filtered order list as an .xlsx file they open in Excel.

**Current approach:** Server-side export endpoint streaming rows with exceljs; the existing filters are reused as-is.

**Scope**
- In: order list export, current filters, column formatting for dates and amounts.
- Out: scheduled exports, other lists.

**Steps**
- [x] #412 Export endpoint reusing the order list query
- [ ] #413 Write orders to XLSX with a streaming writer (in progress)
- [ ] #415 Download button in the order list toolbar
- ~~#414 CSV serializer~~ (dropped: finance needs Excel formatting)

**Deviations from the original request**
- CSV replaced by XLSX at the developer's request (finance opens files in Excel).
```

### Log entries (comments on the work item)

Lead with the kind in bold, then the fields that apply. Keep each entry under about 120 words.

```markdown
**session-start** · claude-code · branch `feature/18342-export`
Opening request: export the order list to CSV for finance, keeping current filters.
Initial plan: #412 endpoint, #414 CSV serializer, #415 toolbar button.
```

```markdown
**prompt**
Asked: switch the export from CSV to XLSX.
Context given: finance opens the file in Excel and needs formatted dates and amounts.
Decided by: developer.
Effect: dropped #414, added #413 (XLSX writer); endpoint #412 unchanged.
```

```markdown
**prompt**
Asked: undo the agent's change to the shared date formatter and format dates in the export only.
Context given: the formatter is used by invoices; changing it broke their layout.
Decided by: developer (correction of agent output).
Effect: reverted the formatter edit; #413 formats dates locally.
```

```markdown
**plan-change**
Discovered: exceljs buffers the whole workbook in memory; 200k-row exports would exceed the API memory limit.
Change: #413 now uses the streaming writer. Origin: agent, accepted by developer.
```

```markdown
**verification**
Ran: `vp test apps/api -t export` (6 passed); manual download of 1,000 filtered orders opened in Excel.
Not covered: 200k-row export (no seed data of that size).
```

```markdown
**handoff**
State: #412 done, #413 in progress (streaming writer works, column widths missing), #415 not started.
Next: set column widths in #413, then the toolbar button.
Open question: should amounts include the currency symbol? Waiting on finance.
```

```markdown
**done**
Delivered: XLSX export of the filtered order list (#412, #413, #415).
Versus the request: CSV became XLSX (developer, finance needs); dates formatted in the export only after a correction.
Verification: API tests, manual Excel check; large exports untested.
Follow-ups: currency symbol question, large-export test data.
```

Other kinds: `progress` (step started or finished), `blocker` (what or who is awaited), `paused` (the developer
paused tracking; no reason needed).

## Older Gentl deployments

Deployments before the semantic Task tools expose `create_task`/`update_task` with `statusId` required and no
`get_board_task_metadata`, `find_tasks`, `move_task`, or `add_task_comment`. There, take status ids from
`get_task_tracking_context` and pass `statusId` (and `parentId` instead of `parent`) to `upsert_tracked_task`. They
resolve no names either: use `typeId`, `priorityId`, `tagIds`, and `assignedUserIds`, or leave those fields out. The
correlation tools (`upsert_tracked_task`, `record_task_progress`, `complete_tracked_task`, `archive_tracked_task`,
`get_task`) behave the same.
