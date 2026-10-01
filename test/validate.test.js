import { test } from "node:test";
import assert from "node:assert/strict";
import { installTarget } from "../src/install.js";
import { validateInstallation } from "../src/validate.js";
import { DEFAULT_PLACEHOLDERS } from "../src/constants.js";
import { makeTempDir, cleanup, writeFile } from "./helpers.js";

test("reports no findings when all placeholders are resolved", async () => {
  const projectDir = await makeTempDir();
  try {
    await installTarget({
      target: "claude",
      projectDir,
      placeholders: DEFAULT_PLACEHOLDERS,
      mergeStrategy: "skip",
      dryRun: false,
    });
    const { isClean, findings } = await validateInstallation({
      projectDir,
      target: "claude",
    });
    assert.equal(isClean, true);
    assert.deepEqual(findings, []);
  } finally {
    await cleanup(projectDir);
  }
});

test("detects an unresolved placeholder with file and line number", async () => {
  const projectDir = await makeTempDir();
  try {
    await writeFile(
      projectDir,
      ".claude/skills/example/SKILL.md",
      "line one\nSome text with {{NOT_A_REAL_KEY}} left in it\nline three",
    );
    const { isClean, findings } = await validateInstallation({
      projectDir,
      target: "claude",
    });
    assert.equal(isClean, false);
    assert.equal(findings.length, 1);
    assert.equal(findings[0].line, 2);
    assert.equal(findings[0].token, "NOT_A_REAL_KEY");
  } finally {
    await cleanup(projectDir);
  }
});

test("returns clean result when target directory does not exist yet", async () => {
  const projectDir = await makeTempDir();
  try {
    const { isClean, findings } = await validateInstallation({
      projectDir,
      target: "github",
    });
    assert.equal(isClean, true);
    assert.deepEqual(findings, []);
  } finally {
    await cleanup(projectDir);
  }
});
