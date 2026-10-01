---
name: git-pull-case-safe
description: Pull the latest from a remote branch on a macOS repo, safely handling case-sensitivity filename conflicts that block a normal git pull. Use when the user asks to pull latest, sync with remote, or when git pull fails with "local changes would be overwritten" due to case-only filename diffs.
---

# Safe Git Pull (macOS Case-Sensitivity)

Some repos track files under both uppercase and lowercase names in the git index (a known macOS case-insensitive filesystem issue). A plain `git pull` will fail with "your local changes to the following files would be overwritten by merge". This skill resolves that safely.

## Context

- macOS HFS+/APFS treats `MyFulfillmentOrder.cls` and `myFulfillmentOrder.cls` as the same physical file, but git tracks them as separate entries.
- The remote branch periodically renames files (case changes count as renames in git). This leaves both casings in the local index, causing phantom "local modifications" that block merges.
- Staged new files (not yet committed) are **destroyed** by `git reset --hard` — save them first.

## Process

### 1. Check current state

```bash
git status --short
git fetch origin <branch>
```

Note any staged files (lines starting with `A `) — these must be preserved.

### 2. Stash staged and unstaged changes

Before doing anything destructive, stash everything so it can be recovered:

```bash
# Stash staged new files and any working tree changes
git stash push --include-untracked -m "pre-pull-case-safe backup"
```

Note the stash ref (`stash@{0}`) — it is the recovery point if anything goes wrong.

**Important:** `git stash` saves staged modifications and untracked files, but for NEW staged files the stash stores the content as a blob. After the reset and pull, re-apply with:

```bash
git stash pop
```

If `stash pop` causes conflicts due to the now-updated index, extract files manually:

```bash
git checkout stash@{0} -- <file>   # restore a specific file from the stash
git stash drop                      # clean up after manual extraction
```

### 3. Hard reset to remote

```bash
git reset --hard origin/<branch>
```

This eliminates all case-collision index entries and brings the branch fully up to date. It is the only reliable fix — stash, `git restore`, `git update-index --assume-unchanged`, and `git rm --cached` all fail to fully clear the pre-merge check on macOS.

**Warning:** `git reset --hard` deletes staged-but-never-committed files from disk. Always run the stash step above before this — the stash is the safety net.

### 4. Re-stage the saved files

```bash
git add <file1> <file2> ...
```

New files survive the reset on disk unless they were the only copy (staged but content not elsewhere). Verify each file still exists before re-staging.

### 5. Verify

```bash
git status --short
git log --oneline -3
```

Confirm the branch is at the latest remote commit and staged files are back in the index.

## When `git reset --hard` is not appropriate

If the user has staged **modifications** to existing tracked files (not just new files), use this safer sequence instead:

```bash
# 1. Export staged changes as a patch
git diff --cached > /tmp/staged.patch

# 2. Hard reset
git reset --hard origin/<branch>

# 3. Re-apply the patch
git apply /tmp/staged.patch
git add <modified files>
```

## Notes

- If your workflow routes changes through a {{CICD_TOOL}} commit UI instead of direct git commits, never run `git commit` or `git push` from the agent — always use that tool's commit flow.
- `git add` is safe; staging is safe.
- The case-collision issue will recur whenever a file is renamed in git history between branches that diverged on macOS.
