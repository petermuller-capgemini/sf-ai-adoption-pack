import path from "node:path";
import { loadEnvFile } from "./env.js";
import {
  DEFAULT_PLACEHOLDERS,
  VALID_TARGETS,
  VALID_MERGE_STRATEGIES,
} from "./constants.js";

/**
 * Precedence: CLI argument > --env-file > project .sf-ai-pack.env > defaults.
 * `defaultMergeStrategy` lets callers (e.g. the update command) change the
 * final fallback without affecting explicit CLI/env overrides.
 */
export async function resolveConfig({
  cliArgs,
  cwd = process.cwd(),
  defaultMergeStrategy = "skip",
  honorStoredMergeStrategy = true,
}) {
  const projectDir = path.resolve(cwd, cliArgs.flags.projectDir || ".");
  const projectEnvPath = path.join(projectDir, ".sf-ai-pack.env");
  const projectEnv = await loadEnvFile(projectEnvPath);

  let specifiedEnv = {};
  if (cliArgs.flags.envFile) {
    const envFilePath = path.resolve(cwd, cliArgs.flags.envFile);
    specifiedEnv = await loadEnvFile(envFilePath);
  }

  const target =
    cliArgs.flags.target || specifiedEnv.TARGET || projectEnv.TARGET || "both";
  // `update` sets honorStoredMergeStrategy=false so a MERGE_STRATEGY=skip
  // value persisted by a prior `install`/`init-config` can't silently
  // suppress the refresh — an explicit --merge-strategy flag still wins.
  const mergeStrategy =
    cliArgs.flags.mergeStrategy ||
    (honorStoredMergeStrategy &&
      (specifiedEnv.MERGE_STRATEGY || projectEnv.MERGE_STRATEGY)) ||
    defaultMergeStrategy;

  if (!VALID_TARGETS.includes(target)) {
    throw new Error(
      `Invalid --target "${target}". Must be one of: ${VALID_TARGETS.join(", ")}.`,
    );
  }
  if (!VALID_MERGE_STRATEGIES.includes(mergeStrategy)) {
    throw new Error(
      `Invalid --merge-strategy "${mergeStrategy}". Must be one of: ${VALID_MERGE_STRATEGIES.join(", ")}.`,
    );
  }

  const placeholders = {
    ...DEFAULT_PLACEHOLDERS,
    ...projectEnv,
    ...specifiedEnv,
    ...cliArgs.placeholders,
  };
  // Control keys may appear in env files; they are not template placeholders.
  delete placeholders.TARGET;
  delete placeholders.MERGE_STRATEGY;

  return {
    projectDir,
    target,
    mergeStrategy,
    dryRun: Boolean(cliArgs.dryRun),
    placeholders,
    cliTarget: cliArgs.flags.target,
    cliPlaceholders: { ...cliArgs.placeholders },
  };
}
