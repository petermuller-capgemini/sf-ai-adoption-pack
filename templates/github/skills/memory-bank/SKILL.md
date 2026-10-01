---
name: memory-bank
description: "Initialize or update the project Memory Bank — read all memory files at session start, manage tasks, and maintain project intelligence across context resets. Run with: /memory-bank [init|update|add-task|show-tasks]"
---

# memory-bank

Initialize and maintain the project Memory Bank — the persistent context layer that survives session resets.

**Applies to:** `**`

---

## Memory Bank Structure

Memory resets between sessions. Read ALL memory bank files at the start of EVERY task — no exceptions. Memory Bank is the only context after reset.

```
memory-bank/
├── projectbrief.md      ← Foundation; source of truth for project scope
├── productContext.md    ← Why this project exists; problems it solves; UX goals
├── activeContext.md     ← Current work focus; recent changes; next steps
├── systemPatterns.md    ← Architecture; key technical decisions; component relationships
├── techContext.md       ← Technologies; dev setup; constraints; dependencies
├── progress.md          ← What works; what's left; known issues
└── tasks/
    ├── _index.md        ← Master list of all tasks with IDs, names, statuses
    └── TASKID-taskname.md  ← Individual task files
```

### Core Files (Required)

1. **`projectbrief.md`** — Foundation document. Created at project start. Defines core requirements and goals. Source of truth for project scope.
2. **`productContext.md`** — Why this project exists. Problems it solves. How it should work. User experience goals.
3. **`activeContext.md`** — Current work focus. Recent changes. Next steps. Active decisions and considerations.
4. **`systemPatterns.md`** — System architecture. Key technical decisions. Design patterns in use. Component relationships.
5. **`techContext.md`** — Technologies used. Development setup. Technical constraints. Dependencies.
6. **`progress.md`** — What works. What's left to build. Current status. Known issues.
7. **`tasks/`** — Individual markdown files for each task plus `_index.md`.

---

## Core Workflows

### Plan Mode

1. Read Memory Bank
2. Check files complete?
   - If No → Create Plan and Document in Chat
   - If Yes → Verify Context → Develop Strategy → Present Approach

### Act Mode

1. Check Memory Bank
2. Update Documentation
3. Update instructions if needed
4. Execute Task
5. Document Changes

### Task Management

For each new task:
1. Create task file in `tasks/` folder
2. Document thought process
3. Create implementation plan
4. Update `_index.md`

During execution:
1. Add progress log entry
2. Update task status
3. Update `_index.md`
4. Mark as Completed when done

---

## Documentation Updates

Memory Bank updates occur when:
1. Discovering new project patterns
2. After implementing significant changes
3. When user requests with **update memory bank** (MUST review ALL files)
4. When context needs clarification

When triggered by **update memory bank**: review every memory bank file, even if some don't require updates. Focus particularly on `activeContext.md`, `progress.md`, and `tasks/` (including `_index.md`).

---

## Task Index Structure (`tasks/_index.md`)

```markdown
# Tasks Index

## In Progress

- [TASK003] Implement user authentication - Working on OAuth integration

## Pending

- [TASK006] Add export functionality - Planned for next sprint

## Completed

- [TASK001] Project setup - Completed on 2025-03-15

## Abandoned

- [TASK008] Integrate with legacy system - Abandoned due to API deprecation
```

---

## Individual Task File Structure (`tasks/TASKID-taskname.md`)

```markdown
# [Task ID] - [Task Name]

**Status:** [Pending/In Progress/Completed/Abandoned]
**Added:** [Date Added]
**Updated:** [Date Last Updated]

## Original Request

[The original task description as provided by the user]

## Thought Process

[Documentation of the discussion and reasoning that shaped the approach]

## Implementation Plan

- [Step 1]
- [Step 2]

## Progress Tracking

**Overall Status:** [Not Started/In Progress/Blocked/Completed] - [Completion %]

### Subtasks

| ID  | Description | Status | Updated | Notes |
|-----|-------------|--------|---------|-------|
| 1.1 | [Subtask]   | [Status] | [Date] | [Notes] |

## Progress Log

### [Date]

- Updated subtask 1.1 status to Complete
- Encountered issue with [specific problem]
- Made decision to [approach/solution]
```

---

## Task Commands

**`add task` / `create task`** — Create new task file with unique Task ID, document thought process, develop implementation plan, update `_index.md`.

**`update task [ID]`** — Open specific task file, add progress log entry with today's date, update status, update `_index.md`.

**`show tasks [filter]`** — Display filtered list:
- `all` — Show all tasks
- `active` — Show In Progress tasks
- `pending` — Show Pending tasks
- `completed` — Show Completed tasks
- `blocked` — Show Blocked tasks
- `recent` — Show tasks updated in last week
- `tag:[tagname]` — Show tasks with specific tag

---

## Project Intelligence (Instructions)

The instructions files capture important patterns, preferences, and project intelligence. Update them when discovering:
- Critical implementation paths
- User preferences and workflow
- Project-specific patterns
- Known challenges
- Evolution of project decisions
- Tool usage patterns

The format is flexible — focus on insights that help work more effectively with the user and the project.
