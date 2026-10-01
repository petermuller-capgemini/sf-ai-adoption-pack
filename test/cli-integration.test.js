import { test } from "node:test";
import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "node:fs/promises";
import { makeTempDir, cleanup, readFileIfExists } from "./helpers.js";

const execFileAsync = promisify(execFile);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BIN = path.join(__dirname, "..", "bin", "sf-ai-pack.js");

async function runCli(args, cwd) {
  try {
    const { stdout, stderr } = await execFileAsync("node", [BIN, ...args], {
      cwd,
    });
    return { code: 0, stdout, stderr };
  } catch (err) {
    return {
      code: err.code ?? 1,
      stdout: err.stdout ?? "",
      stderr: err.stderr ?? "",
    };
  }
}

test("--help prints usage without error", async () => {
  const { code, stdout } = await runCli(["--help"], process.cwd());
  assert.equal(code, 0);
  assert.match(stdout, /sf-ai-pack <command>/);
});

test("init-config writes a .sf-ai-pack.env preset file", async () => {
  const projectDir = await makeTempDir();
  try {
    const { code } = await runCli(
      [
        "init-config",
        "--project-dir",
        projectDir,
        "--target",
        "claude",
        "--project-name",
        "Acme",
      ],
      process.cwd(),
    );
    assert.equal(code, 0);
    const content = await readFileIfExists(
      path.join(projectDir, ".sf-ai-pack.env"),
    );
    assert.match(content, /TARGET=claude/);
    assert.match(content, /PROJECT_NAME=Acme/);
  } finally {
    await cleanup(projectDir);
  }
});

test("install writes .claude assets end to end and validate reports clean", async () => {
  const projectDir = await makeTempDir();
  try {
    const install = await runCli(
      [
        "install",
        "--project-dir",
        projectDir,
        "--target",
        "claude",
        "--project-name",
        "Acme Corp",
      ],
      process.cwd(),
    );
    assert.equal(install.code, 0, install.stderr);

    const claudeMd = await readFileIfExists(
      path.join(projectDir, ".claude", "CLAUDE.md"),
    );
    assert.ok(claudeMd.includes("Acme Corp"));

    const validate = await runCli(
      ["validate", "--project-dir", projectDir, "--target", "claude"],
      process.cwd(),
    );
    assert.equal(validate.code, 0, validate.stdout + validate.stderr);
    assert.match(validate.stdout, /No unresolved placeholders/);
  } finally {
    await cleanup(projectDir);
  }
});

test("install is idempotent when re-run with the same args (both targets)", async () => {
  const projectDir = await makeTempDir();
  try {
    await runCli(
      ["install", "--project-dir", projectDir, "--target", "both"],
      process.cwd(),
    );
    const second = await runCli(
      ["install", "--project-dir", projectDir, "--target", "both"],
      process.cwd(),
    );
    assert.equal(second.code, 0, second.stderr);

    const settingsRaw = await readFileIfExists(
      path.join(projectDir, ".claude", "settings.json"),
    );
    const settings = JSON.parse(settingsRaw);
    assert.equal(settings.hooks.PreToolUse.length, 1);
  } finally {
    await cleanup(projectDir);
  }
});

test("update refreshes placeholder values even when a file already exists", async () => {
  const projectDir = await makeTempDir();
  try {
    await runCli(
      [
        "install",
        "--project-dir",
        projectDir,
        "--target",
        "claude",
        "--project-name",
        "Old Name",
      ],
      process.cwd(),
    );
    const update = await runCli(
      [
        "update",
        "--project-dir",
        projectDir,
        "--target",
        "claude",
        "--project-name",
        "New Name",
        "--skip-version-check",
      ],
      process.cwd(),
    );
    assert.equal(update.code, 0, update.stderr);

    const content = await readFileIfExists(
      path.join(projectDir, ".claude", "CLAUDE.md"),
    );
    assert.ok(content.includes("New Name"));
    assert.ok(!content.includes("Old Name"));
  } finally {
    await cleanup(projectDir);
  }
});

test("update respects an explicit --merge-strategy skip even though its default is overwrite", async () => {
  const projectDir = await makeTempDir();
  try {
    await runCli(
      [
        "install",
        "--project-dir",
        projectDir,
        "--target",
        "claude",
        "--project-name",
        "Old Name",
      ],
      process.cwd(),
    );
    await runCli(
      [
        "update",
        "--project-dir",
        projectDir,
        "--target",
        "claude",
        "--project-name",
        "New Name",
        "--merge-strategy",
        "skip",
        "--skip-version-check",
      ],
      process.cwd(),
    );
    const content = await readFileIfExists(
      path.join(projectDir, ".claude", "CLAUDE.md"),
    );
    assert.ok(
      content.includes("Old Name"),
      "skip should preserve the previously installed content",
    );
  } finally {
    await cleanup(projectDir);
  }
});

test("update ignores a stale MERGE_STRATEGY=skip persisted via init-config and still refreshes", async () => {
  const projectDir = await makeTempDir();
  try {
    // init-config always persists MERGE_STRATEGY=skip by default; update must
    // not let that stored value suppress its own refresh-by-default behavior.
    await runCli(
      ["init-config", "--project-dir", projectDir, "--target", "claude"],
      process.cwd(),
    );
    await runCli(
      ["install", "--project-dir", projectDir, "--project-name", "Old Name"],
      process.cwd(),
    );
    const update = await runCli(
      [
        "update",
        "--project-dir",
        projectDir,
        "--project-name",
        "New Name",
        "--skip-version-check",
      ],
      process.cwd(),
    );
    assert.equal(update.code, 0, update.stderr);
    const content = await readFileIfExists(
      path.join(projectDir, ".claude", "CLAUDE.md"),
    );
    assert.ok(
      content.includes("New Name"),
      "update must refresh despite stored MERGE_STRATEGY=skip",
    );
  } finally {
    await cleanup(projectDir);
  }
});

test("validate exits non-zero when an unresolved placeholder is present", async () => {
  const projectDir = await makeTempDir();
  try {
    await fs.mkdir(path.join(projectDir, ".claude"), { recursive: true });
    await fs.writeFile(
      path.join(projectDir, ".claude", "stray.md"),
      "{{NOT_A_REAL_PLACEHOLDER}}",
    );
    const { code, stdout } = await runCli(
      ["validate", "--project-dir", projectDir, "--target", "claude"],
      process.cwd(),
    );
    assert.equal(code, 1);
    assert.match(stdout, /NOT_A_REAL_PLACEHOLDER/);
  } finally {
    await cleanup(projectDir);
  }
});

test("rejects an invalid --target value", async () => {
  const { code, stderr } = await runCli(
    ["install", "--target", "bogus"],
    process.cwd(),
  );
  assert.equal(code, 1);
  assert.match(stderr, /Invalid --target/);
});

test("rejects an invalid --merge-strategy value", async () => {
  const { code, stderr } = await runCli(
    ["install", "--merge-strategy", "bogus"],
    process.cwd(),
  );
  assert.equal(code, 1);
  assert.match(stderr, /Invalid --merge-strategy/);
});

test("works when the project path contains spaces", async () => {
  const base = await makeTempDir();
  const spacedDir = path.join(base, "my project dir");
  await fs.mkdir(spacedDir, { recursive: true });
  try {
    const { code } = await runCli(
      ["install", "--project-dir", spacedDir, "--target", "claude"],
      process.cwd(),
    );
    assert.equal(code, 0);
    const content = await readFileIfExists(
      path.join(spacedDir, ".claude", "CLAUDE.md"),
    );
    assert.ok(content);
  } finally {
    await cleanup(base);
  }
});
