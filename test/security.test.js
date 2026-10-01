import { test } from "node:test";
import assert from "node:assert/strict";
import { resolveWithinRoot, assertSafeRelativePath } from "../src/security.js";

test("resolves a normal relative path within root", () => {
  const result = resolveWithinRoot(
    "/tmp/project",
    ".github/copilot-instructions.md",
  );
  assert.equal(result, "/tmp/project/.github/copilot-instructions.md");
});

test("rejects absolute paths", () => {
  assert.throws(() => assertSafeRelativePath("/etc/passwd"), /Absolute paths/);
});

test("rejects path traversal via ..", () => {
  assert.throws(
    () => resolveWithinRoot("/tmp/project", "../../etc/passwd"),
    /Unsafe path segment/,
  );
});

test("rejects traversal hidden in the middle of a path", () => {
  assert.throws(
    () => resolveWithinRoot("/tmp/project", ".github/../../etc/passwd"),
    /Unsafe path segment/,
  );
});
