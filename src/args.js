// Maps CLI flag names to either a control key (flags.*) or a {{PLACEHOLDER}} name.
const CONTROL_FLAGS = new Set([
  "target",
  "projectDir",
  "envFile",
  "mergeStrategy",
]);

const FLAG_DEFS = {
  "--target": "target",
  "--project-dir": "projectDir",
  "--env-file": "envFile",
  "--merge-strategy": "mergeStrategy",
  "--project-name": "PROJECT_NAME",
  "--project-description": "PROJECT_DESCRIPTION",
  "--team-name": "TEAM_NAME",
  "--apex-prefix": "APEX_PREFIX",
  "--lwc-prefix": "LWC_PREFIX",
  "--flow-prefix": "FLOW_PREFIX",
  "--subflow-prefix": "SUBFLOW_PREFIX",
  "--config-prefix": "CONFIG_PREFIX",
  "--test-data-factory": "TEST_DATA_FACTORY",
  "--logger-class": "LOGGER_CLASS",
  "--logger-factory": "LOGGER_FACTORY",
  "--utility-controller": "UTILITY_CONTROLLER",
  "--default-psg": "DEFAULT_PSG",
  "--min-coverage": "MIN_COVERAGE",
  "--target-coverage": "TARGET_COVERAGE",
  "--sf-api-version": "SF_API_VERSION",
  "--salesforce-clouds": "SALESFORCE_CLOUDS",
  "--external-integrations": "EXTERNAL_INTEGRATIONS",
  "--cicd-tool": "CICD_TOOL",
  "--work-item-tool": "WORK_ITEM_TOOL",
};

/**
 * Parses argv into { flags, placeholders, dryRun }. Supports both
 * "--flag value" and "--flag=value" forms. Throws on unknown flags.
 */
export function parseArgs(argv) {
  const result = {
    flags: {},
    placeholders: {},
    dryRun: false,
    selfUpdate: false,
    skipVersionCheck: false,
  };

  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];

    if (token === "--dry-run") {
      result.dryRun = true;
      continue;
    }

    if (token === "--self-update") {
      result.selfUpdate = true;
      continue;
    }

    if (token === "--skip-version-check") {
      result.skipVersionCheck = true;
      continue;
    }

    if (!token.startsWith("--")) {
      throw new Error(`Unexpected argument: ${token}`);
    }

    const eqIdx = token.indexOf("=");
    let key = token;
    let value;

    if (eqIdx !== -1) {
      key = token.slice(0, eqIdx);
      value = token.slice(eqIdx + 1);
    } else {
      value = argv[i + 1];
      if (value === undefined || value.startsWith("--")) {
        throw new Error(`Missing value for argument ${key}`);
      }
      i++;
    }

    const mapped = FLAG_DEFS[key];
    if (!mapped) {
      throw new Error(`Unknown argument: ${key}`);
    }

    if (CONTROL_FLAGS.has(mapped)) {
      result.flags[mapped] = value;
    } else {
      result.placeholders[mapped] = value;
    }
  }

  return result;
}
