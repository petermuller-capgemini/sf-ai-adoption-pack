import fs from "node:fs/promises";
import path from "node:path";

const PLACEHOLDER_PATTERN = /\{\{([A-Z0-9_]+)\}\}/g;

export function replacePlaceholders(content, placeholders) {
  return content.replace(PLACEHOLDER_PATTERN, (match, key) =>
    Object.prototype.hasOwnProperty.call(placeholders, key)
      ? String(placeholders[key])
      : match,
  );
}

export function findUnresolvedPlaceholders(content) {
  const tokens = [];
  let match;
  PLACEHOLDER_PATTERN.lastIndex = 0;
  while ((match = PLACEHOLDER_PATTERN.exec(content)) !== null) {
    tokens.push(match[1]);
  }
  return tokens;
}

const BINARY_EXTENSIONS = new Set([
  ".png",
  ".jpg",
  ".jpeg",
  ".gif",
  ".ico",
  ".pdf",
  ".zip",
]);

export async function listTemplateFiles(templateRoot) {
  const files = [];
  async function walk(dir) {
    const entries = await fs.readdir(dir, { withFileTypes: true });
    for (const entry of entries) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        await walk(full);
      } else if (entry.isFile()) {
        files.push(path.relative(templateRoot, full));
      }
    }
  }
  await walk(templateRoot);
  return files;
}

export async function renderTemplateFile(templateRoot, relPath, placeholders) {
  const absPath = path.join(templateRoot, relPath);
  const ext = path.extname(relPath);
  if (BINARY_EXTENSIONS.has(ext)) {
    return { content: await fs.readFile(absPath), isBinary: true };
  }
  const raw = await fs.readFile(absPath, "utf8");
  return { content: replacePlaceholders(raw, placeholders), isBinary: false };
}
