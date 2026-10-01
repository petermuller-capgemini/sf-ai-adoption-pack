/**
 * Merges generated permissions/hooks into an existing .claude/settings.json
 * object instead of replacing it outright. Malformed existing JSON is
 * reported (never thrown away silently) so the caller can back it up first.
 */
export function mergeClaudeSettings(existingRaw, incoming) {
  let existing = {};
  let wasMalformed = false;

  if (existingRaw && existingRaw.trim()) {
    try {
      existing = JSON.parse(existingRaw);
    } catch {
      wasMalformed = true;
      existing = {};
    }
  }

  const merged = JSON.parse(JSON.stringify(existing));

  if (incoming.permissions?.allow) {
    merged.permissions = merged.permissions || {};
    const existingAllow = new Set(merged.permissions.allow || []);
    for (const rule of incoming.permissions.allow) existingAllow.add(rule);
    merged.permissions.allow = Array.from(existingAllow);
  }

  if (incoming.hooks) {
    merged.hooks = merged.hooks || {};
    for (const [event, incomingEntries] of Object.entries(incoming.hooks)) {
      const existingEntries = merged.hooks[event] || [];
      for (const incomingEntry of incomingEntries) {
        const isDuplicate = existingEntries.some(
          (entry) =>
            entry.matcher === incomingEntry.matcher &&
            JSON.stringify(entry.hooks) === JSON.stringify(incomingEntry.hooks),
        );
        if (!isDuplicate) existingEntries.push(incomingEntry);
      }
      merged.hooks[event] = existingEntries;
    }
  }

  return { merged, wasMalformed };
}
