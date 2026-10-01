import { test } from "node:test";
import assert from "node:assert/strict";
import { parseEnvContent } from "../src/env.js";

test("parses simple KEY=value pairs", () => {
  const result = parseEnvContent("FOO=bar\nBAZ=qux");
  assert.deepEqual(result, { FOO: "bar", BAZ: "qux" });
});

test("ignores blank lines and comments", () => {
  const result = parseEnvContent(
    "# a comment\n\nFOO=bar\n   \n# another\nBAZ=qux",
  );
  assert.deepEqual(result, { FOO: "bar", BAZ: "qux" });
});

test("strips surrounding double and single quotes", () => {
  const result = parseEnvContent("NAME=\"My Project\"\nTEAM='Platform Team'");
  assert.deepEqual(result, { NAME: "My Project", TEAM: "Platform Team" });
});

test("strips inline comments on unquoted values but not quoted ones", () => {
  const result = parseEnvContent(
    'A=value # trailing comment\nB="value # not a comment"',
  );
  assert.deepEqual(result, { A: "value", B: "value # not a comment" });
});

test("never executes or evaluates values (treated as opaque strings)", () => {
  const result = parseEnvContent("CMD=$(rm -rf /)\nBACKTICK=`echo hi`");
  assert.equal(result.CMD, "$(rm -rf /)");
  assert.equal(result.BACKTICK, "`echo hi`");
});

test("returns empty object for missing file", async () => {
  const { loadEnvFile } = await import("../src/env.js");
  const result = await loadEnvFile("/nonexistent/path/.env");
  assert.deepEqual(result, {});
});
