# Sequential Workflow Patterns

This reference provides guidance for skills that guide multi-step processes with clear sequential patterns.

## When to Use Workflows

Use workflow patterns when:

- Tasks have clear ordering requirements
- Steps depend on outcomes of previous steps
- Users need guidance through complex processes
- Multiple decision points exist along the path

## Basic Workflow Structure

```markdown
## Workflow

### Step 1: [Action Name]

**Goal**: What this step accomplishes
**Prerequisites**: What must be ready

[Guidance for this step]

**Success Criteria**: How to know you're ready for next step

### Step 2: [Action Name]

...
```

## Conditional Workflows

For workflows with branching:

```markdown
### Step 3: Choose Path

**If [condition]:**
→ Continue to Step 4a: [Path A]

**If [different condition]:**
→ Continue to Step 4b: [Path B]
```

## Iterative Workflows

For processes that loop:

```markdown
### Step 5: Review and Iterate

1. Evaluate the output against criteria
2. If issues found:
   - Return to Step 3 with adjustments
   - Apply learnings from previous iteration
3. If acceptable:
   - Proceed to Step 6
```

## Decision Matrices

For complex decision points:

```markdown
### Decision Point: Tool Selection

| Criteria | Tool A | Tool B | Tool C |
| -------- | ------ | ------ | ------ |
| Speed    | Fast   | Medium | Slow   |
| Quality  | Good   | Better | Best   |
| Cost     | Low    | Medium | High   |

**Recommendation**: Choose based on your priority
```

## Best Practices

1. **Clear Entry Points**: Make it obvious where to start
2. **Exit Conditions**: Define when the workflow is complete
3. **Recovery Paths**: Provide guidance when steps fail
4. **Progress Indicators**: Help users track where they are
5. **Next Actions**: Always end steps with clear next actions

## Anti-Patterns to Avoid

- **Ambiguous Ordering**: Don't use "also" or "additionally" - be explicit about sequence
- **Hidden Dependencies**: Always state prerequisites
- **Dead Ends**: Every path should lead somewhere
- **Excessive Branching**: Too many paths create confusion
