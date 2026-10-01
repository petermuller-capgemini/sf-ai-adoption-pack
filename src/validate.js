import fs from "node:fs/promises";
import path from "node:path";
import { findUnresolvedPlaceholders } from "./template.js";
import { TARGET_DIRS } from "./constants.js";

const TEXT_EXTENSIONS = new Set([
  ".md",
  ".json",
  ".js",
  ".py",
  ".sh",
  ".yml",
  ".yaml",
  ".txt",
]);

async function walkFiles(dir) {
  const files = [];
  async function walk(current) {
    let entries;
    try {
      entries = await fs.readdir(current, { withFileTypes: true });
    } catch (err) {
      if (err.code === "ENOENT") return;
      throw err;
    }
    for (const entry of entries) {
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) await walk(full);
      else if (entry.isFile()) files.push(full);
    }
  }
  await walk(dir);
  return files;
}

export async function validateInstallation({ projectDir, target }) {
  const dirsToScan = target === "both" ? ["github", "claude"] : [target];
  const findings = [];

  for (const key of dirsToScan) {
    const rootDir = path.join(projectDir, TARGET_DIRS[key]);
    const files = (await walkFiles(rootDir)) || [];
    for (const file of files) {
      if (!TEXT_EXTENSIONS.has(path.extname(file))) continue;
      const content = await fs.readFile(file, "utf8");
      const lines = content.split(/\r?\n/);
      lines.forEach((line, idx) => {
        for (const token of findUnresolvedPlaceholders(line)) {
          findings.push({
            file: path.relative(projectDir, file),
            line: idx + 1,
            token,
          });
        }
      });
    }
  }

  return { findings, isClean: findings.length === 0 };
}
