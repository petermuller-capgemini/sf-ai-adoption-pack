import { test } from "node:test";
import assert from "node:assert/strict";
import { parseArgs } from "../src/args.js";

test("parses --flag value form", () => {
  const result = parseArgs([
    "--target",
    "claude",
    "--merge-strategy",
    "overwrite",
  ]);
  assert.equal(result.flags.target, "claude");
  assert.equal(result.flags.mergeStrategy, "overwrite");
});

test("parses --flag=value form", () => {
  const result = parseArgs(["--target=github", "--apex-prefix=ACM"]);
  assert.equal(result.flags.target, "github");
  assert.equal(result.placeholders.APEX_PREFIX, "ACM");
});

test("parses boolean flags without consuming the next token", () => {
  const result = parseArgs(["--dry-run", "--target", "both"]);
  assert.equal(result.dryRun, true);
  assert.equal(result.flags.target, "both");
});

test("parses --self-update and --skip-version-check", () => {
  const result = parseArgs(["--self-update", "--skip-version-check"]);
  assert.equal(result.selfUpdate, true);
  assert.equal(result.skipVersionCheck, true);
});

test("throws on unknown flag", () => {
  assert.throws(
    () => parseArgs(["--not-a-real-flag", "value"]),
    /Unknown argument/,
  );
});

test("throws when a value-flag is missing its value", () => {
  assert.throws(() => parseArgs(["--target"]), /Missing value/);
});

test("throws on a bare positional argument", () => {
  assert.throws(() => parseArgs(["oops"]), /Unexpected argument/);
});
