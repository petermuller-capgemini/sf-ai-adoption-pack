---
name: markdown-standards
description: "Apply documentation and content creation standards for Markdown files — structure, formatting, and validation rules. Run with: /markdown-standards [file.md]"
---

# markdown-standards

Apply documentation and Markdown content standards.

**Applies to:** `**/*.md`

---

## Markdown Content Rules

1. **Headings**: Use appropriate heading levels (H2, H3, etc.) to structure content. Do not use an H1 heading — this is generated from the title.
2. **Lists**: Use bullet points or numbered lists. Ensure proper indentation and spacing.
3. **Code Blocks**: Use fenced code blocks for code snippets. Specify the language for syntax highlighting.
4. **Links**: Use proper markdown syntax for links. Ensure links are valid and accessible.
5. **Images**: Use proper markdown syntax. Include alt text for accessibility.
6. **Tables**: Use markdown tables for tabular data. Ensure proper formatting and alignment.
7. **Line Length**: Limit line length to 400 characters for readability.
8. **Whitespace**: Use appropriate whitespace to separate sections and improve readability.
9. **Front Matter**: Only include YAML front matter if the target publishing platform requires it (see note below).

---

## Formatting and Structure

- **Headings**: Use `##` for H2 and `###` for H3. Hierarchical structure only. Recommend restructuring if content includes H4; more strongly recommend for H5.
- **Lists**: Use `-` for bullet points and `1.` for numbered lists. Indent nested lists with two spaces.
- **Code Blocks**: Use triple backticks to create fenced code blocks. Specify the language after the opening backticks (e.g., ` ```apex `).
- **Links**: Use `[link text](URL)`. Ensure link text is descriptive and URL is valid.
- **Images**: Use `![alt text](image URL)`. Include a brief description in alt text.
- **Tables**: Use `|` to create tables. Ensure columns are properly aligned and headers are included.
- **Line Length**: Break lines at 80 characters to improve readability. Use soft line breaks for long paragraphs.
- **Whitespace**: Use blank lines to separate sections. Avoid excessive whitespace.

---

## Front Matter

Front matter requirements are project-specific — if this repo publishes to a blog/CMS platform, document the required fields here; otherwise plain Markdown without front matter is fine.

---

## Quick Checklist

- [ ] No H1 headings (generated from title)
- [ ] Heading hierarchy is logical (H2 → H3, no skips)
- [ ] All code blocks have language specifiers
- [ ] All links are valid
- [ ] Images have alt text
- [ ] Tables are properly aligned
- [ ] Line length ≤ 400 characters
- [ ] Front matter (if required by the publishing target) is present and complete
