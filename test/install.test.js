import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import {
  installTarget,
  runInstall,
  installEnvExample,
} from "../src/install.js";
import { DEFAULT_PLACEHOLDERS } from "../src/constants.js";
import {
  makeTempDir,
  cleanup,
  writeFile,
  readFileIfExists,
} from "./helpers.js";

test("installs claude templates into a fresh project", async () => {
  const projectDir = await makeTempDir();
  try {
    const result = await installTarget({
      target: "claude",
      projectDir,
      placeholders: { ...DEFAULT_PLACEHOLDERS, PROJECT_NAME: "Acme" },
      mergeStrategy: "skip",
      dryRun: false,
    });
    assert.ok(result.written.includes("CLAUDE.md"));
    const content = await readFileIfExists(path.join(projectDir, "CLAUDE.md"));
    assert.ok(content.includes("Acme"));
    assert.ok(!content.includes("{{PROJECT_NAME}}"));
  } finally {
    await cleanup(projectDir);
  }
});

test("dry-run does not write any files", async () => {
  const projectDir = await makeTempDir();
  try {
    const result = await installTarget({
      target: "claude",
      projectDir,
      placeholders: DEFAULT_PLACEHOLDERS,
      mergeStrategy: "skip",
      dryRun: true,
    });
    assert.ok(result.written.length > 0, "should report what would be written");
    const content = await readFileIfExists(path.join(projectDir, "CLAUDE.md"));
    assert.equal(content, null, "dry-run must not touch the filesystem");
  } finally {
    await cleanup(projectDir);
  }
});

test("merge-strategy skip preserves an existing file", async () => {
  const projectDir = await makeTempDir();
  try {
    await writeFile(projectDir, "CLAUDE.md", "MY CUSTOM CONTENT");
    const result = await installTarget({
      target: "claude",
      projectDir,
      placeholders: DEFAULT_PLACEHOLDERS,
      mergeStrategy: "skip",
      dryRun: false,
    });
    assert.ok(result.skipped.includes("CLAUDE.md"));
    const content = await readFileIfExists(path.join(projectDir, "CLAUDE.md"));
    assert.equal(content, "MY CUSTOM CONTENT");
  } finally {
    await cleanup(projectDir);
  }
});

test("merge-strategy overwrite replaces an existing file", async () => {
  const projectDir = await makeTempDir();
  try {
    await writeFile(projectDir, "CLAUDE.md", "OLD CONTENT");
    await installTarget({
      target: "claude",
      projectDir,
      placeholders: DEFAULT_PLACEHOLDERS,
      mergeStrategy: "overwrite",
      dryRun: false,
    });
    const content = await readFileIfExists(path.join(projectDir, "CLAUDE.md"));
    assert.ok(content.includes("Agent Instructions"));
  } finally {
    await cleanup(projectDir);
  }
});

test("merge-strategy backup keeps a timestamped copy before overwriting", async () => {
  const projectDir = await makeTempDir();
  try {
    await writeFile(projectDir, "CLAUDE.md", "OLD CONTENT");
    const result = await installTarget({
      target: "claude",
      projectDir,
      placeholders: DEFAULT_PLACEHOLDERS,
      mergeStrategy: "backup",
      dryRun: false,
    });
    const backedUpRel = result.backedUp.find((f) => f.endsWith("CLAUDE.md"));
    assert.ok(backedUpRel);
    const entries = await fs.readdir(projectDir);
    const backupFile = entries.find((f) => f.startsWith("CLAUDE.md.bak."));
    assert.ok(backupFile, "expected a timestamped backup file");
    const backupContent = await readFileIfExists(
      path.join(projectDir, backupFile),
    );
    assert.equal(backupContent, "OLD CONTENT");
  } finally {
    await cleanup(projectDir);
  }
});

test("merge-strategy fail throws and does not modify the file", async () => {
  const projectDir = await makeTempDir();
  try {
    await writeFile(projectDir, "CLAUDE.md", "OLD CONTENT");
    await assert.rejects(
      () =>
        installTarget({
          target: "claude",
          projectDir,
          placeholders: DEFAULT_PLACEHOLDERS,
          mergeStrategy: "fail",
          dryRun: false,
        }),
      /merge-strategy is "fail"/,
    );
    const content = await readFileIfExists(path.join(projectDir, "CLAUDE.md"));
    assert.equal(content, "OLD CONTENT");
  } finally {
    await cleanup(projectDir);
  }
});

test("repeated install is idempotent (second run manages the same total file count)", async () => {
  const projectDir = await makeTempDir();
  try {
    const first = await installTarget({
      target: "claude",
      projectDir,
      placeholders: DEFAULT_PLACEHOLDERS,
      mergeStrategy: "overwrite",
      dryRun: false,
    });
    const second = await installTarget({
      target: "claude",
      projectDir,
      placeholders: DEFAULT_PLACEHOLDERS,
      mergeStrategy: "overwrite",
      dryRun: false,
    });
    // settings.json moves from "written" (first run, file didn't exist) to
    // "merged" (second run, file exists and is merged instead of overwritten).
    const firstTotal = first.written.length + first.merged.length;
    const secondTotal = second.written.length + second.merged.length;
    assert.equal(firstTotal, secondTotal);
  } finally {
    await cleanup(projectDir);
  }
});

test("settings.json is merged (not replaced) on repeated install, with no duplicate hooks", async () => {
  const projectDir = await makeTempDir();
  try {
    await writeFile(
      projectDir,
      ".claude/settings.json",
      JSON.stringify({ permissions: { allow: ["Bash(custom command *)"] } }),
    );
    await installTarget({
      target: "claude",
      projectDir,
      placeholders: DEFAULT_PLACEHOLDERS,
      mergeStrategy: "skip",
      dryRun: false,
    });
    await installTarget({
      target: "claude",
      projectDir,
      placeholders: DEFAULT_PLACEHOLDERS,
      mergeStrategy: "skip",
      dryRun: false,
    });

    const raw = await readFileIfExists(
      path.join(projectDir, ".claude", "settings.json"),
    );
    const parsed = JSON.parse(raw);
    assert.ok(
      parsed.permissions.allow.includes("Bash(custom command *)"),
      "custom rule preserved",
    );
    assert.ok(
      parsed.permissions.allow.includes("Bash(sf org list *)"),
      "generated rule merged in",
    );
    assert.equal(
      parsed.hooks.PreToolUse.length,
      1,
      "hook must not be duplicated across repeated installs",
    );
  } finally {
    await cleanup(projectDir);
  }
});

test("runInstall with target=both installs github and claude trees", async () => {
  const projectDir = await makeTempDir();
  try {
    const results = await runInstall({
      target: "both",
      projectDir,
      placeholders: DEFAULT_PLACEHOLDERS,
      mergeStrategy: "skip",
      dryRun: false,
    });
    assert.ok(results.github.written.length > 0);
    assert.ok(results.claude.written.length > 0);
  } finally {
    await cleanup(projectDir);
  }
});

test("runInstall always writes a .env.example reference file", async () => {
  const projectDir = await makeTempDir();
  try {
    const results = await runInstall({
      target: "claude",
      projectDir,
      placeholders: DEFAULT_PLACEHOLDERS,
      mergeStrategy: "skip",
      dryRun: false,
    });
    assert.deepEqual(results.envExample.written, [".env.example"]);
    const content = await readFileIfExists(
      path.join(projectDir, ".env.example"),
    );
    assert.match(content, /TARGET=both/);
    assert.match(content, /APEX_PREFIX=/);
  } finally {
    await cleanup(projectDir);
  }
});

test("installEnvExample respects merge-strategy skip on repeated install", async () => {
  const projectDir = await makeTempDir();
  try {
    await writeFile(projectDir, ".env.example", "MY CUSTOM NOTES");
    const result = await installEnvExample({
      projectDir,
      mergeStrategy: "skip",
      dryRun: false,
    });
    assert.deepEqual(result.skipped, [".env.example"]);
    const content = await readFileIfExists(
      path.join(projectDir, ".env.example"),
    );
    assert.equal(content, "MY CUSTOM NOTES");
  } finally {
    await cleanup(projectDir);
  }
});

test("an unknown target never writes outside the project directory", async () => {
  const projectDir = await makeTempDir();
  try {
    const result = await installTarget({
      target: "../escaped",
      projectDir,
      placeholders: DEFAULT_PLACEHOLDERS,
      mergeStrategy: "skip",
      dryRun: false,
    });
    assert.deepEqual(result.written, []);
    const parentEntries = await fs.readdir(path.join(projectDir, ".."));
    assert.ok(
      !parentEntries.includes("escaped"),
      "no directory must be created outside the project root",
    );
  } finally {
    await cleanup(projectDir);
  }
});

test("persistPreset creates a populated .sf-ai-pack.env on first run", async () => {
  const projectDir = await makeTempDir();
  try {
    const results = await runInstall({
      target: "claude",
      projectDir,
      placeholders: { ...DEFAULT_PLACEHOLDERS, PROJECT_NAME: "HAL" },
      cliPlaceholders: { PROJECT_NAME: "HAL" },
      mergeStrategy: "skip",
      dryRun: false,
    });
    assert.equal(results.preset.created, true);
    const env = await readFileIfExists(
      path.join(projectDir, ".sf-ai-pack.env"),
    );
    assert.match(env, /^PROJECT_NAME=HAL$/m);
    assert.match(env, /^APEX_PREFIX=APP$/m);
  } finally {
    await cleanup(projectDir);
  }
});

test("persistPreset updates passed keys and keeps other lines in an existing env", async () => {
  const projectDir = await makeTempDir();
  try {
    await writeFile(
      projectDir,
      ".sf-ai-pack.env",
      "# mine\nPROJECT_NAME=Old\nCUSTOM_KEY=keep\n",
    );
    const results = await runInstall({
      target: "claude",
      projectDir,
      placeholders: { ...DEFAULT_PLACEHOLDERS, PROJECT_NAME: "HAL" },
      cliPlaceholders: { PROJECT_NAME: "HAL", TEAM_NAME: "HAL Delivery Team" },
      mergeStrategy: "skip",
      dryRun: false,
    });
    assert.deepEqual(results.preset.updated, ["PROJECT_NAME"]);
    assert.deepEqual(results.preset.added, ["TEAM_NAME"]);
    const env = await readFileIfExists(
      path.join(projectDir, ".sf-ai-pack.env"),
    );
    assert.equal(
      env,
      "# mine\nPROJECT_NAME=HAL\nCUSTOM_KEY=keep\nTEAM_NAME=HAL Delivery Team\n",
    );
  } finally {
    await cleanup(projectDir);
  }
});

test("runInstall installs CLAUDE.md at the root and updates .gitignore", async () => {
  const projectDir = await makeTempDir();
  try {
    await writeFile(projectDir, ".gitignore", "node_modules/\n.claude\n");
    const results = await runInstall({
      target: "both",
      projectDir,
      placeholders: { ...DEFAULT_PLACEHOLDERS },
      cliPlaceholders: {},
      mergeStrategy: "skip",
      dryRun: false,
    });
    assert.ok(results.claude.written.includes("CLAUDE.md"));
    assert.notEqual(
      await readFileIfExists(path.join(projectDir, "CLAUDE.md")),
      null,
    );
    assert.equal(
      await readFileIfExists(path.join(projectDir, ".claude", "CLAUDE.md")),
      null,
    );
    assert.deepEqual(results.gitignore.added, [".github/", "CLAUDE.md"]);
    const ignore = await readFileIfExists(path.join(projectDir, ".gitignore"));
    assert.match(ignore, /^node_modules\/\n\.claude\n\n# AI assistant assets/);
    assert.equal(ignore.match(/\.claude/g).length, 1);
  } finally {
    await cleanup(projectDir);
  }
});
