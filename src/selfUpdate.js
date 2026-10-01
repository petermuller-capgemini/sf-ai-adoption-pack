import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const execFileAsync = promisify(execFile);
const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function readOwnPackageJson() {
  const raw = await readFile(
    path.join(__dirname, "..", "package.json"),
    "utf8",
  );
  return JSON.parse(raw);
}

/**
 * Looks up the latest version published to the configured registry.
 * Network access only happens here (update command), never during install.
 */
export async function checkForUpdate() {
  const pkg = await readOwnPackageJson();
  const registry = pkg.publishConfig?.registry || "https://registry.npmjs.org";

  try {
    const { stdout } = await execFileAsync(
      "npm",
      ["view", pkg.name, "version", "--registry", registry],
      { timeout: 15000 },
    );
    const latestVersion = stdout.trim();
    return {
      name: pkg.name,
      currentVersion: pkg.version,
      latestVersion,
      registry,
      updateAvailable: Boolean(latestVersion) && latestVersion !== pkg.version,
    };
  } catch (err) {
    return {
      name: pkg.name,
      currentVersion: pkg.version,
      latestVersion: null,
      registry,
      updateAvailable: false,
      error: err.message,
    };
  }
}

export async function performSelfUpdate({ name, registry }) {
  return execFileAsync(
    "npm",
    ["install", "--global", `${name}@latest`, "--registry", registry],
    { timeout: 120000 },
  );
}
