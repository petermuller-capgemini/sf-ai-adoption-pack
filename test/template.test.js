import { test } from "node:test";
import assert from "node:assert/strict";
import {
  replacePlaceholders,
  findUnresolvedPlaceholders,
} from "../src/template.js";

test("replaces known placeholders", () => {
  const result = replacePlaceholders("Hello {{PROJECT_NAME}}!", {
    PROJECT_NAME: "Acme",
  });
  assert.equal(result, "Hello Acme!");
});

test("leaves unknown placeholders untouched", () => {
  const result = replacePlaceholders("Hello {{UNKNOWN_TOKEN}}!", {
    PROJECT_NAME: "Acme",
  });
  assert.equal(result, "Hello {{UNKNOWN_TOKEN}}!");
});

test("findUnresolvedPlaceholders detects every remaining token", () => {
  const tokens = findUnresolvedPlaceholders("{{A}} and {{B}} and {{A}}");
  assert.deepEqual(tokens, ["A", "B", "A"]);
});

test("findUnresolvedPlaceholders returns empty array when fully resolved", () => {
  const tokens = findUnresolvedPlaceholders("no placeholders here");
  assert.deepEqual(tokens, []);
});
