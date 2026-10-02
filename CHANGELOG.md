# Changelog

All notable changes to this project are documented in this file.
Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- `CLAUDE.md` is now installed at the project root instead of `.claude/CLAUDE.md`.
- The bundled env reference is installed as `.env.example` (was `.sf-ai-pack.env.example`).

### Added

- `install` writes values passed on the command line to `.sf-ai-pack.env`:
  a new file is created with all resolved values; an existing file has only
  the passed keys updated or appended, leaving other lines untouched.
- `install` adds `.claude/`, `.github/` and `CLAUDE.md` (per target) to
  `.gitignore`, creating it if needed and skipping entries already present.

## [0.2.0] - 2026-10-01

### Added

- Full Claude skill set in `templates/claude/skills` (previously only
  `apex-standards` and `security-standards`).
- `.env.example` is now installed alongside the other assets.
- Placeholder defaults for values not supplied at install time.

## [0.1.0] - 2026-10-01

### Added

- Initial CLI: `init-config`, `install`, `update`, `validate` commands.
- `.env`-style preset configuration (`.sf-ai-pack.env`) with precedence
  CLI argument > `--env-file` > project `.sf-ai-pack.env` > built-in defaults.
- Recursive template rendering with `{{UPPER_CASE_PLACEHOLDER}}` replacement.
- `.github`, `.claude`, or combined (`both`) installation targets.
- Merge strategies for existing files: `skip`, `overwrite`, `backup`, `fail`.
- Safe JSON merge into an existing `.claude/settings.json` (permissions +
  hooks), with duplicate-hook prevention across repeated installs.
- `update` command: re-applies current placeholder values to already-installed
  assets (default `overwrite`, ignoring any stale `MERGE_STRATEGY` persisted by
  a prior `install`/`init-config`), with an optional `--self-update` flag to
  check the registry for a newer published CLI version and install it.
- `validate` command: scans installed assets for unresolved placeholders and
  reports file, line, and token.
- Path-traversal protection for all generated file writes.
- Starter templates:
  - `.claude`: `CLAUDE.md`, `settings.json`, pre-deploy quality-gate hook,
    `apex-standards` and `security-standards` skills.
  - `.github`: `copilot-instructions.md`, `security-and-owasp.instructions.md`.
- Node.js built-in test runner suite (51 tests) covering env parsing, argument
  parsing, placeholder replacement, path-traversal prevention, all merge
  strategies, Claude settings merge/dedupe, idempotent installs, dry-run, and
  full CLI integration via the packaged binary.
- CI workflow (`ci.yml`) and GitHub Packages publish workflow (`publish.yml`).

### Known gaps (tracked for a follow-up pass)

- Only a representative subset of the full Salesforce adoption-pack content
  has been migrated and anonymized so far (2 Claude skills, 1 GitHub
  instructions file). The remaining skills, prompts, agents, and hooks from
  the source pack still need migration.
- No Windows-specific path test coverage yet (tests run on macOS/Linux paths).
