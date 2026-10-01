import fs from "node:fs/promises";

/**
 * Minimal .env-style parser: KEY=value, '#' comments, blank lines, and
 * single/double-quoted values. Deliberately does not evaluate or execute
 * any value — values are treated as opaque strings only.
 */
export function parseEnvContent(content) {
  const result = {};
  const lines = content.split(/\r?\n/);

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;

    const eqIdx = line.indexOf("=");
    if (eqIdx === -1) continue;

    const key = line.slice(0, eqIdx).trim();
    if (!key) continue;

    let value = line.slice(eqIdx + 1).trim();
    const isDoubleQuoted =
      value.startsWith('"') && value.endsWith('"') && value.length >= 2;
    const isSingleQuoted =
      value.startsWith("'") && value.endsWith("'") && value.length >= 2;

    if (isDoubleQuoted || isSingleQuoted) {
      value = value.slice(1, -1);
    } else {
      const commentIdx = value.indexOf(" #");
      if (commentIdx !== -1) value = value.slice(0, commentIdx).trim();
    }

    result[key] = value;
  }

  return result;
}

export async function loadEnvFile(filePath) {
  try {
    const content = await fs.readFile(filePath, "utf8");
    return parseEnvContent(content);
  } catch (err) {
    if (err.code === "ENOENT") return {};
    throw err;
  }
}
