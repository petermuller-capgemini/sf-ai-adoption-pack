---
name: prompt-standards
description: "Create or review Copilot prompt files following project standards — frontmatter, body structure, input handling, tool guidance, and output definition. Run with: /prompt-standards [file.prompt.md]"
---

# prompt-standards

Create and review Copilot prompt files following project standards.

**Applies to:** `**/*.prompt.md`

---

## What is a Copilot Prompt File?

A `.prompt.md` file provides a reusable, structured instruction set for GitHub Copilot to execute a specific task. Prompt files are consumed by Copilot as context when invoked.

---

## File Naming

- Use kebab-case: `review-apex-class.prompt.md`
- Name should reflect the task, not the tool: `generate-test-class.prompt.md` not `copilot-apex-tests.prompt.md`
- Store under `.github/prompts/` (project-level) or `~/.vscode/prompts/` (user-level)

---

## Required Frontmatter

Every `.prompt.md` must begin with YAML frontmatter:

```yaml
---
mode: 'agent'           # 'agent' | 'ask' | 'edit'
model: 'gpt-4o'         # target model identifier
tools: []               # list of tools the prompt may invoke (see Tools section)
description: >
  One-sentence summary of what this prompt does.
---
```

### `mode` Values

| Mode | Description |
|---|---|
| `agent` | Full agentic mode — can read/write files, run tools, iterate |
| `ask` | Chat mode — reads context, answers questions, does not modify files |
| `edit` | Edit mode — modifies specific files in selection |

### `tools` Values (common)

| Tool | Use for |
|---|---|
| `codebase` | Search and read project files |
| `editFiles` | Write/update files |
| `runCommands` | Execute shell commands |
| `githubRepo` | Query GitHub Issues, PRs, commits |
| `fetch` | Retrieve external URLs |
| `problems` | Read IDE diagnostics / linter output |

Only list tools the prompt actually needs — minimum required set.

---

## Body Structure

### 1. Task Title (H2)

Start with a clear H2 that names the task:

```markdown
## Review Apex Class for Project Standards
```

### 2. Context Block

One paragraph explaining what the prompt does and why. Include:
- What problem this solves
- When to use it
- Any assumptions about the code/environment

```markdown
This prompt reviews an Apex class file against the project's Apex coding standards
(`.github/instructions/apex.instructions.md`). Use it when reviewing a PR or
preparing a class for production deployment.
```

### 3. Input Variables

Declare all variables the prompt expects using `${variableName}` syntax. Document each variable:

```markdown
## Inputs

- `${file}` — Path to the Apex class to review (e.g. `force-app/main/default/classes/{{APEX_PREFIX}}_OrderService.cls`)
- `${context}` _(optional)_ — Additional context about the change (e.g. "this is a new integration class")
```

### 4. Instructions

Numbered list of concrete steps. Each step should be a single, unambiguous action:

```markdown
## Instructions

1. Read the file at `${file}` using the `codebase` tool.
2. Read `.github/instructions/apex.instructions.md` for the full standards reference.
3. Check each rule category in order: Security, Logging, SOQL/DML, Static vs Instance, Naming, Tests.
4. For each violation found, record: file path, line number, rule violated, severity (Critical/Major/Minor), recommended fix.
5. Output a structured review report (see Output section).
```

### 5. Output Definition

Describe the exact format of the response:

```markdown
## Output

Return a Markdown report with:

### Review Summary
- Files reviewed: `<count>`
- Total violations: `<count>`
- Blocking (Critical/Major): `<count>`

### Violations

| Line | Severity | Rule | Issue | Fix |
|---|---|---|---|---|
| 42 | Major | static-soql | `private static List<Order__c> fetchOrders()` performs SOQL — must be instance method | Convert to `public List<Order__c> fetchOrders()` |

### Verdict
`PASS` | `FAIL` — `<one-sentence rationale>`
```

---

## Input Handling Rules

- **Never** include sensitive values (tokens, passwords, org IDs) as input variables — reference Named Credentials or config instead.
- **Always** validate expected file types: if `${file}` should be Apex, instruct the prompt to error if extension is not `.cls`.
- Use `_(optional)_` to mark non-required inputs.
- Provide example values in variable descriptions.

---

## Tool Guidance

When the prompt reads instruction files, declare them explicitly:

```markdown
## Reference Files

- `.github/instructions/apex.instructions.md` — Apex coding standards
- `.github/instructions/integration-framework.instructions.md` — Integration architecture
```

When the prompt writes files, describe the target path and format:

```markdown
## Output File

Write the report to `reports/apex-review-${timestamp}.md`.
```

---

## Iterative Refinement

For `agent` mode prompts that may need to loop (e.g., fix until tests pass):

```markdown
## Iteration Rules

1. After making a change, run `npm run lint:apex` and check for new errors.
2. If errors remain, repeat the fix cycle up to **3 times**.
3. If unresolved after 3 iterations, stop and report the remaining issues.
4. Never modify files outside the component directory without explicit confirmation.
```

---

## QA Checklist

Before committing a `.prompt.md` file:

- [ ] Frontmatter present and valid YAML
- [ ] `mode`, `model`, `tools`, `description` all populated
- [ ] `tools` list is minimum required (no unused tools)
- [ ] All `${variable}` inputs documented with type and example
- [ ] Output format explicitly defined
- [ ] No hardcoded credentials, URLs, or org-specific IDs
- [ ] Reference instruction files are named correctly (they exist in `.github/instructions/`)
- [ ] Prompt tested against at least one real file before committing
- [ ] File name is kebab-case and describes the task

---

## Example: Minimal Valid Prompt

```markdown
---
mode: 'ask'
model: 'gpt-4o'
tools: ['codebase']
description: >
  Summarise the purpose and public API of an Apex class.
---

## Summarise Apex Class

Read `${file}` and provide:

1. One-paragraph description of the class's purpose.
2. Bulleted list of all `public` and `@AuraEnabled` methods with signatures and a one-line description of each.
3. Dependencies: any other classes, custom objects, or external services this class relies on.

## Output

Return plain Markdown. No headers. Bullet lists only.
```
