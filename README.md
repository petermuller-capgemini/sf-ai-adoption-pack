# sf-ai-adoption-pack

CLI installer for Salesforce AI adoption packs — installs and keeps up to date
the GitHub Copilot (`.github`) and/or Claude Code (`.claude`) assets in an
existing Salesforce DX project, with project-specific naming conventions
substituted via placeholders.

> **Status:** initial slice. Core CLI (`init-config`, `install`, `update`,
> `validate`) is implemented and tested end-to-end. Template content currently
> covers a representative subset for each target (see [CHANGELOG.md](CHANGELOG.md)
> for what's migrated so far vs. pending).
>
> This repository is public for visibility, but the code is proprietary
> Capgemini IP — see [LICENSE](LICENSE). Public visibility does not grant any
> right to reuse, copy, or redistribute this code.

---

## Prerequisites

- Node.js 18 or later.
- A GitHub account authenticated to GitHub Packages (`npm.pkg.github.com`
  always requires an authenticated npm login to install from it, even for
  public packages).

---

## Authenticating to GitHub Packages

GitHub Packages only supports npm scoped packages, authenticated with a
personal access token (classic) that has at least `read:packages` scope.

1. Create a classic PAT with `read:packages` (and `repo` if the repository is
   private) at <https://github.com/settings/tokens>.
2. Export it as an environment variable — **never** commit it:

   ```bash
   export GITHUB_PACKAGES_TOKEN="<your token>"
   ```

3. Copy [.npmrc.example](.npmrc.example) to `~/.npmrc` (user-level, not inside
   any project you ship), or merge its two lines into your existing `~/.npmrc`:

   ```text
   @petermuller-capgemini:registry=https://npm.pkg.github.com
   //npm.pkg.github.com/:_authToken=${GITHUB_PACKAGES_TOKEN}
   ```

---

## Install

### Global install

```bash
npm install --global @petermuller-capgemini/sf-ai-adoption-pack
```

### One-off via npx

```bash
npx @petermuller-capgemini/sf-ai-adoption-pack install --target both
```

---

## Usage

```bash
cd /path/to/salesforce-project

# 1. Write a reusable preset (.sf-ai-pack.env) with your project's naming conventions
sf-ai-pack init-config --target both --project-name "Acme Platform" --apex-prefix ACM

# 2. Install (safe by default: never overwrites a file that already exists)
sf-ai-pack install --target both

# 3. Validate that no {{PLACEHOLDER}} tokens were left unresolved
sf-ai-pack validate
```

With explicit overrides and a merge strategy:

```bash
npx @petermuller-capgemini/sf-ai-adoption-pack install \
  --target both \
  --env-file .sf-ai-pack.env \
  --merge-strategy backup
```

### Configuration precedence

```
CLI argument  >  --env-file <path>  >  project .sf-ai-pack.env  >  built-in defaults
```

### All CLI options

| Flag                                                                                                 | Purpose                                                        |
| ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `--target github\|claude\|both`                                                                      | Which asset set(s) to install/update                           |
| `--project-dir <path>`                                                                               | Target Salesforce DX project (default: cwd)                    |
| `--env-file <path>`                                                                                  | Load a specific preset file instead of the project default     |
| `--merge-strategy skip\|overwrite\|backup\|fail`                                                     | How to handle files that already exist                         |
| `--dry-run`                                                                                          | Report what would happen without writing anything              |
| `--project-name`, `--project-description`, `--team-name`                                             | `{{PROJECT_NAME}}`, `{{PROJECT_DESCRIPTION}}`, `{{TEAM_NAME}}` |
| `--apex-prefix`, `--lwc-prefix`, `--flow-prefix`, `--subflow-prefix`, `--config-prefix`              | Naming convention placeholders                                 |
| `--test-data-factory`, `--logger-class`, `--logger-factory`, `--utility-controller`, `--default-psg` | Shared utility class name placeholders                         |
| `--min-coverage`, `--target-coverage`, `--sf-api-version`                                            | Quality gate placeholders                                      |
| `--salesforce-clouds`, `--external-integrations`, `--cicd-tool`, `--work-item-tool`                  | Platform context placeholders                                  |

Run `sf-ai-pack --help` any time for the short version of this list.

---

## Merge strategies (existing-file handling)

| Strategy                       | Behavior                                                                          |
| ------------------------------ | --------------------------------------------------------------------------------- |
| `skip` (default for `install`) | Leaves the existing file untouched                                                |
| `overwrite`                    | Replaces the file with the freshly rendered template                              |
| `backup`                       | Copies the existing file to `<file>.bak.<timestamp>`, then writes the new version |
| `fail`                         | Stops immediately with a clear error, no files are touched                        |

`.claude/settings.json` is a special case: regardless of merge strategy, its
`permissions.allow` list and `hooks` are **merged** into the existing file
(duplicates removed) rather than replaced, so your own customizations in that
file are preserved.

---

## Dry run

Add `--dry-run` to any `install`/`update` call to see a per-target summary
(written/skipped/backed-up/merged counts) without touching the filesystem.

---

## Keeping a project up to date — the `update` command

```bash
sf-ai-pack update --target both
```

Unlike `install` (which is safe-by-default and never clobbers a file that
already exists), `update` is designed to be run periodically to **refresh**
previously installed assets with your current placeholder values — it
defaults to `overwrite` for template-managed files and ignores a stale
`MERGE_STRATEGY` that may have been persisted by an earlier `install` or
`init-config` run. Pass an explicit `--merge-strategy` to override that.

`update` also checks the configured registry for a newer published version of
this CLI itself:

```bash
# Just check and report (no changes to the global install)
sf-ai-pack update

# Check, and install the newer CLI version if one is found
sf-ai-pack update --self-update

# Skip the registry check entirely (e.g. offline), only refresh templates
sf-ai-pack update --skip-version-check
```

`--self-update` runs `npm install --global <package>@latest` using the
registry from this package's own `publishConfig` — it only updates the
globally installed binary. Run `sf-ai-pack update` again afterwards (new
process) to apply the refreshed template content from the new version.

---

## Placeholder validation

```bash
sf-ai-pack validate --target both
```

Scans every installed text file for unresolved `{{PLACEHOLDER}}` tokens and
reports `file:line  unresolved placeholder {{TOKEN}}` for each one found.
Exits non-zero if any remain, `0` if clean.

---

## Upgrade process

```bash
npm install --global @petermuller-capgemini/sf-ai-adoption-pack@latest
cd /path/to/salesforce-project
sf-ai-pack update --target both
```

## Uninstall

```bash
npm uninstall --global @petermuller-capgemini/sf-ai-adoption-pack
```

The generated `.github`/`.claude` files in your project are plain files — delete
them manually (or via version control) if you no longer want them; the CLI
does not track or remove them for you.

## Release / versioning

- Semantic versioning (`MAJOR.MINOR.PATCH`). Versions are not bumped
  automatically by CI — bump `version` in `package.json` as part of the PR
  that should trigger a release.
- Publishing is driven by creating a GitHub Release whose tag matches the
  `version` in `package.json`. The `publish.yml` workflow then runs `npm
publish` using the repository's own `GITHUB_TOKEN` (no personal access
  token required in CI).

---

## Security notes

- Installation performs **no network access** — `install`/`validate` only read
  and write local files. Only `update` (registry version check / `--self-update`)
  makes network calls, and only when not passed `--skip-version-check`.
- All generated paths are resolved against the project root and rejected if
  they would escape it (path-traversal protection).
- `.env` files are parsed as plain key/value pairs only — values are never
  evaluated or executed as shell commands.
- Malformed existing `.claude/settings.json` is backed up, never silently
  discarded or overwritten without a copy.
- Never commit a real GitHub Packages token. Supply it only via the
  `GITHUB_PACKAGES_TOKEN` environment variable referenced from `~/.npmrc`.

---

## Troubleshooting

| Symptom                                                             | Likely cause / fix                                                                                          |
| ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `npm error 404 ... does not exist under owner`                      | Package not yet published, or you lack `read:packages` access — check `~/.npmrc` and your PAT scopes        |
| `ENEEDAUTH` from `npm whoami --registry=https://npm.pkg.github.com` | `~/.npmrc` auth token missing/expired — re-export `GITHUB_PACKAGES_TOKEN` and re-check `.npmrc`             |
| `validate` reports unresolved placeholders                          | Re-run `install`/`update` with the missing `--xxx-prefix`/`--xxx-name` flag, or add it to `.sf-ai-pack.env` |
| File already exists and merge-strategy is "fail"                    | Expected behavior of the `fail` strategy — re-run with `backup` or `overwrite`, or resolve manually         |
| `update` didn't change anything                                     | Check whether you passed `--merge-strategy skip` explicitly, or whether `--dry-run` was set                 |

---

## Example `.sf-ai-pack.env`

See [.env.example](.env.example) for a complete, copy-pasteable preset file.

## Contents of this repository

```
bin/sf-ai-pack.js       CLI entry point
src/                    CLI implementation (env, args, config, template, install, validate, selfUpdate)
templates/github/       GitHub Copilot asset templates
templates/claude/       Claude Code asset templates
test/                   Node built-in test runner suite
.github/workflows/      This repo's own CI and publish workflows
```
