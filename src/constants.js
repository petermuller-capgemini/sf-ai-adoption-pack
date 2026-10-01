export const DEFAULT_PLACEHOLDERS = {
  PROJECT_NAME: "Salesforce Project",
  PROJECT_DESCRIPTION: "Salesforce DX project",
  TEAM_NAME: "Development Team",
  APEX_PREFIX: "APP",
  LWC_PREFIX: "app",
  FLOW_PREFIX: "APP",
  SUBFLOW_PREFIX: "APP_Sub",
  CONFIG_PREFIX: "APP",
  LOGGER_CLASS: "Logger",
  LOGGER_FACTORY: "LoggerFactory",
  TEST_DATA_FACTORY: "TestDataFactory",
  UTILITY_CONTROLLER: "UtilityController",
  DEFAULT_PSG: "APP_Standard_User",
  MIN_COVERAGE: "75",
  TARGET_COVERAGE: "90",
  SF_API_VERSION: "62.0",
  SALESFORCE_CLOUDS: "Sales Cloud",
  EXTERNAL_INTEGRATIONS: "None",
  CICD_TOOL: "GitHub Actions",
  WORK_ITEM_TOOL: "GitHub Issues",
  CONTACT_EMAIL: "admin@example.com",
  COMPANY_DOMAIN: "example.com",
  ORG_ALIAS: "my-org",
  SITE_NAME: "my-site",
};

export const VALID_TARGETS = ["github", "claude", "both"];
export const VALID_MERGE_STRATEGIES = ["skip", "overwrite", "backup", "fail"];

export const TARGET_DIRS = { github: ".github", claude: ".claude" };
