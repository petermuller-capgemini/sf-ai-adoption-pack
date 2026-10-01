import { test } from "node:test";
import assert from "node:assert/strict";
import { mergeClaudeSettings } from "../src/claudeSettingsMerge.js";

test("merges permissions.allow without duplicating entries", () => {
  const existing = JSON.stringify({
    permissions: { allow: ["Bash(sf org list *)"] },
  });
  const incoming = {
    permissions: { allow: ["Bash(sf org list *)", "Bash(sf apex run test *)"] },
  };
  const { merged } = mergeClaudeSettings(existing, incoming);
  assert.deepEqual(merged.permissions.allow.sort(), [
    "Bash(sf apex run test *)",
    "Bash(sf org list *)",
  ]);
});

test("appends new hook entries without duplicating identical ones", () => {
  const hookEntry = {
    matcher: "Bash(sf project deploy start*)",
    hooks: [{ type: "command", command: "python3 hook.py" }],
  };
  const existing = JSON.stringify({ hooks: { PreToolUse: [hookEntry] } });
  const incoming = { hooks: { PreToolUse: [hookEntry] } };
  const { merged } = mergeClaudeSettings(existing, incoming);
  assert.equal(
    merged.hooks.PreToolUse.length,
    1,
    "duplicate hook must not be appended",
  );
});

test("preserves unrelated existing settings", () => {
  const existing = JSON.stringify({
    someOtherSetting: true,
    permissions: { allow: ["X"] },
  });
  const incoming = { permissions: { allow: ["Y"] } };
  const { merged } = mergeClaudeSettings(existing, incoming);
  assert.equal(merged.someOtherSetting, true);
});

test("recovers from malformed existing JSON without throwing", () => {
  const existing = "{ this is not valid json";
  const incoming = { permissions: { allow: ["X"] } };
  const { merged, wasMalformed } = mergeClaudeSettings(existing, incoming);
  assert.equal(wasMalformed, true);
  assert.deepEqual(merged.permissions.allow, ["X"]);
});

test("handles missing/empty existing settings", () => {
  const { merged, wasMalformed } = mergeClaudeSettings("", {
    permissions: { allow: ["X"] },
  });
  assert.equal(wasMalformed, false);
  assert.deepEqual(merged.permissions.allow, ["X"]);
});
