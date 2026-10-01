import path from "node:path";

/**
 * Rejects absolute paths and ".." segments before any path is joined to a root.
 */
export function assertSafeRelativePath(relPath) {
  if (path.isAbsolute(relPath)) {
    throw new Error(`Absolute paths are not allowed: "${relPath}"`);
  }
  const normalized = relPath.split(path.sep).join("/");
  if (normalized.split("/").includes("..")) {
    throw new Error(`Unsafe path segment ".." detected in "${relPath}"`);
  }
}

/**
 * Resolves relPath against root and verifies the result does not escape root,
 * guarding against path traversal when writing generated files.
 */
export function resolveWithinRoot(root, relPath) {
  assertSafeRelativePath(relPath);
  const resolvedRoot = path.resolve(root);
  const target = path.resolve(resolvedRoot, relPath);
  if (target !== resolvedRoot && !target.startsWith(resolvedRoot + path.sep)) {
    throw new Error(`Resolved path escapes project root: "${relPath}"`);
  }
  return target;
}
