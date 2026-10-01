---
name: tag-work-item
description: "Add tags to an Azure DevOps work item (e.g. a User Story) after it has been reviewed or developed, using the ado-local-sync VS Code extension's silent tagging command. Use whenever the user asks to tag, label, or mark a work item/User Story as reviewed, developed, AI-reviewed, etc. Run with: /tag-work-item <WorkItemId(s)> <Tags> [dryRun]"
---

# tag-work-item

Append one or more tags to Azure DevOps work item(s) (User Stories, Bugs, Tasks) via the
**ado-local-sync** VS Code extension (`pettll.ado-local-sync`). Use this after a code review or
development pass completes, to mark the linked work item accordingly — e.g. `AI Reviewed`,
`Copilot-PR-Review`, `Copilot-Developed`.

Existing tags on the work item are preserved; new tags are appended. Duplicate tags are ignored
case-insensitively, so this is always safe to re-run.

## Usage

```
/tag-work-item <WorkItemId(s)> <Tags> [dryRun]
```

**Examples:**

```
/tag-work-item 598760 "AI Reviewed"
/tag-work-item 598760,598761 "Copilot-PR-Review,Copilot-Developed" dryRun
```

## Parameters

| Parameter       | Required | Default | Notes                                                           |
| --------------- | -------- | ------- | --------------------------------------------------------------- |
| `WorkItemId(s)` | Yes      | —       | One or more numeric ADO work item IDs, comma-separated          |
| `Tags`          | Yes      | —       | One or more tags, comma-separated. Spaces inside a tag are fine |
| `dryRun`        | No       | `false` | Pass `dryRun` / `true` to preview without writing               |

If `WorkItemId(s)` or `Tags` are missing, ask the user before proceeding (`vscode_askQuestions`).

## Steps

1. **Confirm the extension is configured** — this skill assumes `pettll.ado-local-sync` is already
   installed and configured (organisation/project/PAT set via `ADO Sync: Configure`). Do not ask
   the user for a PAT; the command reports a clear configuration error if it is missing.

2. **Preview with a dry run first** for any multi-item or first-time tagging request, unless the
   user explicitly asks for an immediate real update:

```bash
open "vscode://pettll.ado-local-sync/addTags?ids=<ids>&tags=<tags>&dryRun=true"
```

- `<ids>`: comma-separated work item IDs, e.g. `598760,598761`
- `<tags>`: URL-encoded, comma-separated tags, e.g. `AI%20Reviewed` or `Copilot-PR-Review%2CCopilot-Developed`
- Use VS Code Insiders' URI scheme (`vscode-insiders://...`) if the user is on Insiders — check
  which binary/scheme is active before assuming `vscode://`.
- Results are written to the **ADO Local Sync** output channel. Read it back if you need to
  confirm what would change (`existingTags`, `addedTags`, `finalTags` per work item).

3. **Confirm with the user** before running the real (non-dry-run) update — tagging a shared ADO
   work item is a write to a shared system. Summarize the dry-run preview (which tags would be
   added to which IDs) and get explicit go-ahead, unless the user already asked for a direct,
   non-preview update in their request.

4. **Run the real update:**

```bash
open "vscode://pettll.ado-local-sync/addTags?ids=<ids>&tags=<tags>&dryRun=false"
```

This requires the user setting `adoLocalSync.allowUriWriteActions: true`. If the command
silently has no effect, check this setting and ask the user to enable it (`ADO Sync` extension
settings) rather than guessing further.

5. **Report the outcome** — state which work item IDs were changed vs. unchanged (tag already
   present) vs. failed, based on the output channel log or the user's confirmation in VS Code
   (an information message `Tag update completed. Changed: N. Failed: N.` appears for non-silent
   runs; the silent command only logs to the output channel).

## Choosing tags

Prefer the project's existing AI-tagging convention over inventing new tags:

- `Copilot-PR-Review` — after a code review pass (see global Copilot instructions, "AI Usage Tagging")
- Ask the user if they want a different tag (e.g. `AI Reviewed`, `Copilot-Developed`) when the
  request doesn't match an existing convention — don't silently invent new tag taxonomy.

## Notes

- The extension also exposes `adoLocalSync.addTagsSilent` as a direct VS Code command
  (`{ ids: number[], tags: string[], dryRun: boolean }`) and an interactive `adoLocalSync.addTags`
  command (opens input boxes) — the URI handler above is the only variant that doesn't require
  interactive VS Code command execution, so it's the reliable path.
- Tags are appended, never removed — this skill cannot remove or replace tags.
- IDs and tags are parsed from comma/semicolon/space-separated strings, so loose formatting in the
  URI query string is tolerated.
