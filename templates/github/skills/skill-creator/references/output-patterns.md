# Output Patterns and Templates

This reference provides patterns for skills that generate structured output.

## When to Use Output Patterns

Use output patterns when:

- Skills generate code, configuration, or documents
- Consistent formatting is important
- Quality standards must be maintained
- Templates accelerate common tasks

## Code Generation Patterns

### Template with Placeholders

```python
TEMPLATE = """
class {CLASS_NAME}:
    \"\"\"
    {DESCRIPTION}
    \"\"\"

    def __init__(self, {PARAMETERS}):
        {INITIALIZATION}

    def {METHOD_NAME}(self, {METHOD_PARAMS}):
        {METHOD_BODY}
"""
```

### Progressive Enhancement

Start minimal, add complexity:

```markdown
## Basic Version

[Simple implementation that works]

## Enhanced Version

[Add error handling, logging, etc.]

## Production Version

[Add full validation, edge cases, documentation]
```

## Documentation Patterns

### API Reference Format

```markdown
## `function_name(param1, param2)`

**Purpose**: One-line description

**Parameters**:

- `param1` (type): Description
- `param2` (type): Description

**Returns**: Description of return value

**Example**:
\`\`\`python
result = function_name("value1", 42)
\`\`\`

**Notes**: Additional context or gotchas
```

### Configuration Format

```yaml
# Configuration Template
service:
  name: { SERVICE_NAME }
  version: { VERSION }

  settings:
    option1: { VALUE } # Description of what this controls
    option2: { VALUE } # Description of what this controls

  # Optional advanced settings
  advanced:
    feature_flag: false
```

## Quality Standards

### Code Output Should Include

1. **Documentation**: Comments explaining non-obvious parts
2. **Error Handling**: Try/catch or error checking
3. **Type Hints**: Where language supports them
4. **Validation**: Input validation where appropriate
5. **Examples**: Usage examples in comments or docstrings

### Markdown Output Should Include

1. **Clear Hierarchy**: Proper heading levels
2. **Examples**: Concrete illustrations
3. **Links**: References to related docs
4. **Formatting**: Code blocks, tables, lists as appropriate

## Example-Driven Patterns

Provide multiple examples showing range:

```markdown
## Examples

### Minimal Example

[Simplest possible use case]

### Common Example

[Most typical use case]

### Complex Example

[Edge case or advanced usage]
```

## Validation Patterns

Include validation with output:

```python
def validate_output(generated_code):
    """Validate generated code meets standards"""
    checks = [
        ("Has docstring", 'def' in generated_code and '"""' in generated_code),
        ("Has error handling", 'try' in generated_code or 'if' in generated_code),
        ("Proper indentation", check_indentation(generated_code))
    ]
    return checks
```

## Best Practices

1. **Consistency**: Use same patterns throughout skill
2. **Completeness**: Generated output should be usable as-is
3. **Clarity**: Prefer readability over cleverness
4. **Standards**: Follow language/framework conventions
5. **Flexibility**: Allow customization through parameters

## Anti-Patterns to Avoid

- **Incomplete Output**: Leaving TODOs or placeholders without guidance
- **Inconsistent Style**: Mixing naming conventions or formats
- **Hardcoded Values**: Use parameters for anything that might change
- **Missing Context**: Output should be self-documenting
