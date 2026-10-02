# Gentl Task Tracking: tool cookbook

Exact Gentl Tasks MCP calls and message templates for the `gentl-task-tracking` skill. Connecting the MCP to a
harness: https://github.com/gentlsro/gentl-skills#connect-the-gentl-mcp-servers

Most operations come in two forms: **correlated** (the work Task comes from a tracker item and is addressed by
`provider` + `externalId`) and **board-native** (no tracker item; the work Task is addressed by its Gentl id, found by
name or board number). SKILL.md says which applies.

## Correlation keys (correlated work only)

| Source | `provider` | `externalId` | `url` |
| --- | --- | --- | --- |
| Azure DevOps work item | `azure-devops` | `<organization>/<id>`, e.g. `acme/18342` | the work item URL |
| GitLab issue | `gitlab` | `<host>/<group>/<project>#<iid>`, e.g. `gitlab.com/acme/shop#311` | the issue URL |
| GitHub issue | `github` | `<owner>/<repo>#<number>`, e.g. `acme/shop#87` | the issue URL |
| Jira ticket | `jira` | `<site>/<key>`, e.g. `acme.atlassian.net/SHOP-512` | the ticket URL |
| Step of any of the above | same as the work Task | `<work Task externalId>/step-<slug>` | omit |

- Tracker ids are only unique within an organization, site, or repository, and one Gentl instance can serve several,
  so the key carries that tenancy. Take it from the item URL, else from `git remote get-url origin` when there is a
  repository (Azure DevOps and GitLab remotes name the organization or group). If the developer gives only a bare id
  and neither source says where it lives, ask once.
- `provider` is lowercased by Gentl. `externalId` is **case-sensitive** and trimmed: write it exactly the same way
  every time; lowercase hosts and organizations.
- A step slug is short kebab-case derived from the step's first name (`step-xlsx-writer`). It never changes, even
  when the step is renamed or reshaped, because it is the step's identity.

Board-native work has no keys. Its steps are the work Task's child Tasks, addressed by their Gentl ids, which you read
from the steps query below at session start.

## Session start

### Find the work Task

By name or board number (board-native, or a correlated Task the developer names on the board):

```json
find_tasks { "text": "rate limit research", "boardId": "<board id, if known>" }
```

```json
find_tasks { "text": "#412", "boardId": "<board id>" }
```

Names tolerate typos and come closest first; each hit has `id`, board number (`uuid`), `name`, board, and status.
Archived Tasks are skipped unless `includeArchived: true` (use it when the developer says the work was closed and is
being reopened). A board number needs `boardId`.

By tracker item (correlated):

```json
get_task { "by": "external_reference", "provider": "azure-devops", "externalId": "acme/18342" }
```

`NOT_FOUND` means it is not tracked yet. (`CORRELATION_NOT_FOUND` from a tracked *write* means the externalId was
spelled differently; fix the key, do not create a second Task.)

### Load its steps, description, and recent log

```json
query_tasks {
  "where": { "parentId": "<work Task id>" },
  "select": {
    "id": true, "uuid": true, "name": true, "archivedAt": true, "doneDate": true,
    "status": { "select": { "name": true } },
    "externalReferences": { "select": { "provider": true, "externalId": true, "metadata": true } }
  },
  "orderBy": { "position": "asc" }
}
```

```json
query_tasks {
  "where": { "id": "<work Task id>" },
  "select": {
    "description": true,
    "externalReferences": { "select": { "provider": true, "externalId": true, "metadata": true } },
    "comments": { "select": { "message": true, "createdAt": true }, "orderBy": { "createdAt": "desc" }, "take": 8 }
  }
}
```

A Task found by name is correlated when it or its steps carry a reference this skill wrote (step externalIds ending
in `/step-<slug>`, or `metadata.source` of `gentl-task-tracking`); continue with that `provider` and `externalId`.

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

Gives statuses (with their `processState`), Task types, priorities, tags, assignable users, sprints, custom fields,
and the caller's permissions. Pass names from this response afterwards (`"status": "Ongoing"`, `"type": "Bug"`).

### Create the work Task

Correlated:

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
  "description": "<request text, then the tracking section>"
}
```

Board-native:

```json
create_task {
  "boardId": "<board id>",
  "name": "Compare rate limits of the payment providers",
  "type": "Research",
  "status": "Upcoming",
  "assignees": ["<developer email, if known and assignable>"],
  "description": "<request text, then the tracking section>"
}
```

- `name` and `boardId` are required (`upsert_tracked_task` needs them on the first call only). Use the tracker item's
  own title, or a short name for the work in the developer's terms, so it can be found by name later.
- `metadata` (correlated) carries `source: "gentl-task-tracking"` and the harness; add `repo` and `branch` only when
  the work happens in a repository.
- `type`: the board type closest to the work (Bug, Feature, Story, Task, Research, …); omit when nothing fits.
- Put the request above the tracking section, restated in your words without secrets, credentials, or personal or
  customer data (the summary rules in SKILL.md apply). If you could not read the original item, write what the
  developer told you and say so. On an existing Task, leave the text above the tracking section untouched.
- `create_task` is not idempotent. If it fails without a clear error, `find_tasks` by the name before retrying.

### Create a step

Correlated:

```json
upsert_tracked_task {
  "provider": "azure-devops",
  "externalId": "acme/18342/step-xlsx-writer",
  "boardId": "<board id>",
  "parent": "<work Task id>",
  "name": "Write orders to XLSX with exceljs",
  "status": "Upcoming",
  "description": "What this step delivers and how it will be checked."
}
```

Board-native:

```json
create_task {
  "boardId": "<board id>",
  "parent": "<work Task id>",
  "name": "Collect documented limits for each provider",
  "status": "Upcoming",
  "description": "What this step delivers and how it will be checked."
}
```

## During the session

### Log entry

Correlated:

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

Board-native:

```json
add_task_comment { "taskId": "<work Task id>", "message": "<entry markdown>" }
```

No deduplication: after a failure without a clear error, load the latest comments (query above, `take: 3`) and
retry only if the entry is missing.

Always log on the **work Task**, not on steps.

### Move a step or the work Task

```json
upsert_tracked_task { "provider": "azure-devops", "externalId": "acme/18342/step-xlsx-writer", "status": "Ongoing" }
```

```json
update_task { "taskId": "<step id>", "status": "Ongoing" }
```

Use a status in an `IN_PROGRESS` column. The first time any step starts, move the work Task the same way.
Combine a status change with any name or description change for the same Task in one call.

### Reopen a finished or dropped step

```json
upsert_tracked_task { "provider": "azure-devops", "externalId": "acme/18342/step-xlsx-writer", "status": "Ongoing", "doneDate": null, "archivedAt": null }
```

```json
update_task { "taskId": "<step id>", "status": "Ongoing", "doneDate": null, "archivedAt": null }
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

```json
update_task { "taskId": "<step id>", "name": "Collect documented and observed limits", "description": "..." }
```

### Finish or drop a step (and complete the work Task)

Correlated:

```json
complete_tracked_task { "provider": "azure-devops", "externalId": "acme/18342/step-xlsx-writer" }
```

```json
archive_tracked_task { "provider": "azure-devops", "externalId": "acme/18342/step-csv-serializer" }
```

`complete_tracked_task` without `status` picks the sole status of the board's `DONE` column. When it returns
candidates instead, ask the developer and pass the chosen `status`.

Board-native:

```json
update_task { "taskId": "<step id>", "status": "Done", "doneDate": "2026-10-01T16:05:00Z" }
```

```json
update_task { "taskId": "<step id>", "archivedAt": "2026-10-01T16:05:00Z" }
```

Take the status from the board's `DONE` column in the metadata; when that column has several statuses, ask the
developer. Always set `doneDate` (current UTC time) together with the status.

### Rewrite the tracking section

1. Read the work Task's `description` (`get_task` by external reference, or `get_task { "by": "id", "id": ... }`).
2. Keep everything before the line `## Work tracking` (or the older `## Implementation tracking`) byte for byte. If
   neither heading is there, keep the whole description and append the section.
3. Write `"<kept text>\n\n<new section>"` as `description` (`upsert_tracked_task` or `update_task`).

## Templates

### Tracking section (work Task description)

Code work:

```markdown
## Work tracking

_Maintained by the developer's agent. Last updated 2026-10-01 14:40 UTC (claude-code, repo `shop`, branch `feature/18342-export`)._

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

Other work (research shown):

```markdown
## Work tracking

_Maintained by the developer's agent. Last updated 2026-10-02 10:15 UTC (cursor)._

**Goal:** Decide which payment provider can carry the peak checkout load without throttling.

**Current approach:** Compare documented limits, then confirm the two closest candidates with a sandbox load test.

**Scope**
- In: Stripe, Adyen, GoPay; card payments; peak of 40 requests per second.
- Out: pricing, bank transfers.

**Steps**
- [x] #520 Collect documented limits for each provider
- [ ] #521 Sandbox load test of the two closest candidates (in progress)
- [ ] #522 Recommendation for the team
- ~~#523 Survey of other teams' experience~~ (dropped: no team uses GoPay)

**Deviations from the original request**
- GoPay added at the developer's request (finance wants a local provider in the comparison).

**Linked items**
- https://gitlab.com/acme/shop/-/issues/311 (the checkout incident that prompted this)
```

Leave out **Linked items** when there are none.

### Log entries (comments on the work Task)

Lead with the kind in bold, then the fields that apply. Keep each entry under about 120 words.

```markdown
**session-start** · claude-code · repo `shop`, branch `feature/18342-export`
Opening request: export the order list to CSV for finance, keeping current filters.
Initial plan: #412 endpoint, #414 CSV serializer, #415 toolbar button.
```

```markdown
**session-start** · cursor · no repository
Opening request: find out whether our payment provider throttles us at peak checkout load, and which alternative would not.
Initial plan: #520 documented limits, #521 sandbox load test, #522 recommendation.
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
Asked: stop relying on the providers' marketing pages and use only their API reference docs.
Context given: the marketing pages quote burst limits, not sustained ones.
Decided by: developer (correction of agent output).
Effect: #520 figures redone from the API references; Adyen's limit dropped from 100 to 25 requests per second.
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
**verification**
Checked: documented limits against each provider's API reference (links in #520); sandbox load test at 40 requests per second for 10 minutes on Stripe and Adyen, no throttling on Stripe, Adyen throttled after 3 minutes.
Not covered: production accounts may have different limits than sandbox.
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

```markdown
**done**
Delivered: recommendation to stay on Stripe and raise the sustained limit with their support (#522), accepted by the team lead.
Versus the request: GoPay added to the comparison (developer); figures limited to API references after a correction.
Verification: API references, sandbox load test; production limits unconfirmed.
Follow-ups: ask Stripe support to confirm the production limit.
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

Board-native tracking needs `find_tasks` and `add_task_comment`. Without them, track only correlated work: tell the
developer once that work without a tracker item cannot be tracked on this Gentl deployment, and continue without
tracking.
