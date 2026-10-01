# {{PROJECT_NAME}} - Global Copilot Instructions

These repository-wide instructions shape Copilot's behavior across the {{PROJECT_NAME}} Salesforce codebase ({{PROJECT_DESCRIPTION}}).
Maintained by {{TEAM_NAME}}.

---

## Communication Style

Be concise in all responses:

- **Fragments OK**: "Run tests before push" not "You should always make sure to run tests before pushing."
- **Drop filler**: cut "just", "really", "basically", "essentially", "actually", "simply".
- **No hedging**: state the action directly instead of "it might be worth" / "you could consider".
- **Merge redundant points**: one example where multiple show the same pattern.

---

## Agent Interaction Protocol

- **User input**: use `vscode_askQuestions` whenever confirmation, clarification, or a user decision is needed mid-task.
- **Subagents for heavy work**: delegate token-intensive steps (large codebase scans, bulk org queries, multi-file analysis) to subagents. Instruct them to return only key findings — no raw data dumps.

---

## Work Item Tagging

Tag reviewed/implemented work in {{WORK_ITEM_TOOL}} with the relevant label, preserving any existing tags.

## Hooks Format

Hooks follow the **VS Code agent hooks format** (`.github/hooks/*.json`):

- Event names are PascalCase: `SessionStart`, `Stop`, `UserPromptSubmit`.
- Each entry uses `command` / `osx` / `linux` / `windows` for OS-specific scripts.
- Timeouts are integers (seconds) in the `timeout` field.

See VS Code documentation: https://code.visualstudio.com/docs/copilot/customization/hooks

---

## Testing Expectations

- Aim for **{{TARGET_COVERAGE}}%+** coverage in practice (minimum {{MIN_COVERAGE}}% to deploy); cover positive/negative paths, bulk contexts, and `System.runAs` where role-based behavior matters.
- Use `@TestSetup` and `{{TEST_DATA_FACTORY}}` for data; avoid `seeAllData=true`. Include assertions in all tests.

---

## How Copilot picks these up

- Repo-wide instructions are read from `.github/copilot-instructions.md`.
- Path-specific rules live under `.github/instructions/*.instructions.md`.
- Reusable prompt files live under `.github/prompts/*.prompt.md`.
