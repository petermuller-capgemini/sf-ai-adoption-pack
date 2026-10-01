import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { listTemplateFiles, renderTemplateFile } from "./template.js";
import { resolveWithinRoot } from "./security.js";
import { mergeClaudeSettings } from "./claudeSettingsMerge.js";
import { TARGET_DIRS } from "./constants.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const TEMPLATES_ROOT = path.join(__dirname, "..", "templates");

export async function fileExists(targetPath) {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

async function writeFileEnsuringDir(targetPath, content) {
  await fs.mkdir(path.dirname(targetPath), { recursive: true });
  await fs.writeFile(targetPath, content);
}

async function backupExisting(targetPath) {
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const backupPath = `${targetPath}.bak.${stamp}`;
  await fs.copyFile(targetPath, backupPath);
  return backupPath;
}

function isClaudeSettingsFile(target, relPath) {
  return target === "claude" && relPath === "settings.json";
}

export async function installTarget({
  target,
  projectDir,
  placeholders,
  mergeStrategy,
  dryRun,
  log = () => {},
}) {
  const templateRoot = path.join(TEMPLATES_ROOT, target);
  const result = { written: [], skipped: [], backedUp: [], merged: [] };

  if (!(await fileExists(templateRoot))) {
    log(`No templates found for target "${target}" — skipping.`);
    return result;
  }

  const targetDir = TARGET_DIRS[target];
  const relFiles = await listTemplateFiles(templateRoot);

  for (const relPath of relFiles) {
    const destRelPath = path.join(targetDir, relPath);
    const destPath = resolveWithinRoot(projectDir, destRelPath);
    const exists = await fileExists(destPath);

    if (isClaudeSettingsFile(target, relPath) && exists) {
      const { content: renderedJson } = await renderTemplateFile(
        templateRoot,
        relPath,
        placeholders,
      );
      const incoming = JSON.parse(renderedJson);
      const existingRaw = await fs.readFile(destPath, "utf8");
      const { merged, wasMalformed } = mergeClaudeSettings(
        existingRaw,
        incoming,
      );

      if (wasMalformed) {
        if (!dryRun) await backupExisting(destPath);
        result.backedUp.push(destRelPath);
      }
      if (!dryRun) {
        await writeFileEnsuringDir(
          destPath,
          JSON.stringify(merged, null, 2) + "\n",
        );
      }
      result.merged.push(destRelPath);
      continue;
    }

    if (exists) {
      if (mergeStrategy === "skip") {
        result.skipped.push(destRelPath);
        continue;
      }
      if (mergeStrategy === "fail") {
        throw new Error(
          `File already exists and merge-strategy is "fail": ${destRelPath}`,
        );
      }
      if (mergeStrategy === "backup") {
        if (!dryRun) await backupExisting(destPath);
        result.backedUp.push(destRelPath);
      }
      // "overwrite" falls through to the write below.
    }

    const { content } = await renderTemplateFile(
      templateRoot,
      relPath,
      placeholders,
    );
    if (!dryRun) await writeFileEnsuringDir(destPath, content);
    result.written.push(destRelPath);
  }

  return result;
}

export async function runInstall(config) {
  const targets =
    config.target === "both" ? ["github", "claude"] : [config.target];
  const results = {};
  for (const target of targets) {
    results[target] = await installTarget({ ...config, target });
  }
  return results;
}
