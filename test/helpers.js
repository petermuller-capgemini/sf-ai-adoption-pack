import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

export async function makeTempDir(prefix = "sf-ai-pack-test-") {
  return fs.mkdtemp(path.join(os.tmpdir(), prefix));
}

export async function cleanup(dir) {
  await fs.rm(dir, { recursive: true, force: true });
}

export async function writeFile(root, relPath, content) {
  const full = path.join(root, relPath);
  await fs.mkdir(path.dirname(full), { recursive: true });
  await fs.writeFile(full, content);
  return full;
}

export async function readFileIfExists(fullPath) {
  try {
    return await fs.readFile(fullPath, "utf8");
  } catch (err) {
    if (err.code === "ENOENT") return null;
    throw err;
  }
}
