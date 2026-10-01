---
name: sf-deploy
description: Deploy staged Salesforce metadata to a sandbox org using SF CLI. Use when the user asks to deploy, push, or send code to an org or a named sandbox alias. Handles conflict detection via org retrieve + diff before deploying.
---

# Salesforce Sandbox Deploy

Deploy all staged Salesforce source files to a target sandbox org via SF CLI.

## Sandbox note — all sf CLI commands require `dangerouslyDisableSandbox: true`

The SF CLI writes its log file to `~/.sf/sf-YYYY-MM-DD.log`, which is outside the Claude Code sandbox write allowlist. Every `sf project retrieve` and `sf project deploy` call will be silently auto-denied unless the sandbox is disabled. Use `dangerouslyDisableSandbox: true` on every Bash call that invokes `sf`.

## Process

### 1. Identify staged Salesforce components

```bash
git diff --name-only --cached | grep "^force-app/"
```

Only deploy files under `force-app/` — ignore docs, .gitignore, etc.

### 2. Check for conflicts (retrieve org version for comparison)

Use `--target-metadata-dir` (Metadata API format) to retrieve without touching source tracking:

```bash
sf project retrieve start \
  --metadata "ApexClass:ClassName" \
  --target-org <org-alias> \
  --target-metadata-dir .org-retrieve \
  --unzip \
  --wait 10
```

Retrieved files land in `.org-retrieve/unpackaged/unpackaged/classes/`.

For LWC components use `LightningComponentBundle:ComponentName`.

### 3. Diff org vs local

```bash
diff .org-retrieve/unpackaged/unpackaged/classes/MyClass.cls \
     force-app/main/default/classes/MyClass.cls
```

**Safe to proceed** if diffs are only header/comment additions.  
**Stop and investigate** if the org has substantive code not in local — that would be overwritten.

### 3b. Merging org-only content before deploying

**Permission sets** — diffs often show the same entries at different line positions (alphabetical sort varies). Before flagging an entry as "org-only", grep the local file to confirm the entry is truly absent, not just reordered.

**CustomLabels** — the org accumulates labels from all dev branches. When org has labels local doesn't, merge them in with Python before deploying:

```python
import xml.etree.ElementTree as ET

NS = "http://soap.sforce.com/2006/04/metadata"
ET.register_namespace("", NS)

org_tree = ET.parse(".org-retrieve/unpackaged/unpackaged/labels/CustomLabels.labels")
local_tree = ET.parse("force-app/main/default/labels/CustomLabels.labels-meta.xml")

org_root = org_tree.getroot()
local_root = local_tree.getroot()

local_names = {
    el.find("{" + NS + "}fullName").text
    for el in local_root.findall("{" + NS + "}labels")
}

for el in org_root.findall("{" + NS + "}labels"):
    if el.find("{" + NS + "}fullName").text not in local_names:
        local_root.append(el)

try:
    ET.indent(local_tree, space="    ")
except AttributeError:
    pass

local_tree.write(
    "force-app/main/default/labels/CustomLabels.labels-meta.xml",
    xml_declaration=True,
    encoding="UTF-8",
)
```

After running, re-stage the file: `git add force-app/main/default/labels/CustomLabels.labels-meta.xml`

**Watch for duplicate customPermissions** — if a permission set already has a `<customPermissions>` block near the top (alphabetical position) and the diff also shows one appended near the bottom from the org, the result will have a duplicate that fails deployment with `Element customPermissions is duplicated`. Remove the bottom copy before deploying.

### 4. Deploy all staged components

Build source-dir args dynamically — LWC must use the component folder, not individual files:

```bash
SOURCES=$(git diff --name-only --cached | grep "^force-app/" | while read f; do
  if echo "$f" | grep -q "^force-app/main/default/lwc/"; then
    echo "$f" | sed 's|\(force-app/main/default/lwc/[^/]*\)/.*|\1|'
  elif echo "$f" | grep -q "^force-app/main/default/experiences/"; then
    echo "force-app/main/default/experiences/mysite1"
  else
    echo "$f"
  fi
done | sort -u)

CMD="sf project deploy start --ignore-conflicts --target-org <org-alias> --wait 20"
while IFS= read -r src; do CMD="$CMD -d \"$src\""; done <<< "$SOURCES"
eval $CMD
```

`--ignore-conflicts` is safe once the diff confirms the org has no exclusive changes.

**Critical: never pass `-d` with a path outside `force-app/`.** Paths outside the project (e.g. `/tmp/...`) get recorded in source tracking with unsafe relative sequences (`../../../../...`) which permanently break all future deploys and `sf project reset tracking` on that org. If you need to deploy a modified version of a file that differs from source-controlled state, overwrite it locally, deploy, then restore — or use the staging area below.

### 4b. Deploying a subset to a higher org without polluting source tracking

When deploying specific files to a higher org — especially files you've temporarily modified for compatibility — use a clean staging area instead of the project directory:

```bash
# One-time setup (safe path, no special characters)
mkdir -p /tmp/claude/sitdeploy/force-app/main/default/classes \
         /tmp/claude/sitdeploy/force-app/main/default/permissionsets \
         /tmp/claude/sitdeploy/force-app/main/default/labels \
         /tmp/claude/sitdeploy/force-app/main/default/flows \
         /tmp/claude/sitdeploy/force-app/main/default/objects/OrderItemSummary/fields

cat > /tmp/claude/sitdeploy/sfdx-project.json << 'EOF'
{
  "packageDirectories": [{"path": "force-app", "default": true}],
  "name": "sitdeploy", "namespace": "", "sourceApiVersion": "{{SF_API_VERSION}}"
}
EOF

# Copy only the files you want to deploy
cp force-app/main/default/classes/MyClass.cls \
   force-app/main/default/classes/MyClass.cls-meta.xml \
   /tmp/claude/sitdeploy/force-app/main/default/classes/

# Deploy from the staging dir
cd /tmp/claude/sitdeploy
sf project deploy start --ignore-conflicts \
  --target-org <org-alias> --wait 20 \
  -d "force-app/main/default/classes/MyClass.cls"
cd -
```

This completely bypasses the project's source tracking — no corruption risk, and the deploy only includes exactly what you copied.

### 5. Check result

```bash
sf project deploy report --job-id <deploy-id> --target-org <org-alias>
```

Review the Component Failures table. Each failure shows the metadata type, name, and error message.

### 5b. If source tracking is corrupted (UnsafeFilepathError)

Symptom: every deploy and `sf project reset tracking` fails with `The filepath "../../../../..."  contains unsafe character sequences`.

Fix — delete the corrupted isogit tracking database (SF CLI rebuilds it automatically on the next deploy):

```bash
# Get the org ID
sf data query --query "SELECT Id FROM Organization LIMIT 1" --target-org <org-alias>
# Then delete:
rm -rf .sf/orgs/<orgId>/localSourceTracking
```

Run this with `! rm -rf .sf/orgs/<orgId>/localSourceTracking` in the Claude Code terminal if the sandbox blocks it.

### 6. Stage the theme JSON if adding new Experience Cloud pages

If new views use a custom `themeLayoutType` (e.g. `CustomBookingLayout`), that key must exist in the experience's theme JSON at:

```
force-app/main/default/experiences/<site>/themes/<theme>.json
```

Add the layout key to the `"layouts"` map and a matching entry to the `"views"` array with `"componentName": "c:<lwcName>"` before deploying the ExperienceBundle.

## Key flags

| Flag | Purpose |
|---|---|
| `--ignore-conflicts` | Bypass source-tracking conflict detection (safe after diff confirms no org-only changes) |
| `--target-metadata-dir` | Retrieve in zip/Metadata format — bypasses source tracking so files are always pulled fresh |
| `--unzip` | Extract the retrieved zip automatically |
| `-d` / `--source-dir` | Specify individual files or folders to deploy |
| `--wait 20` | Wait up to 20 minutes for the async deploy to complete |

## Default target org

`my-sandbox` (alias: `user@example.com.my-sandbox`)

## Branching strategy and org promotion pipeline

Feature branches are created from `main` for git history/diff purposes, but they are **not** deployed to an org that matches `main`. The actual promotion path is:

```
dev-sandbox(es)  →  integration  →  qa  →  staging  →  main
```

All orgs from `integration` upward already carry the **cumulative code** from every dev branch that has been promoted. A "big bang" merge back to `main` happens at the end of the release.

### Implications for branch reviews

When inspecting a feature branch that is based on `main`:

- A method or constant that appears "missing" from the branch (because it only exists in a dev-sandbox staged/committed change) is **not a gap** — it will already be live in the target org (`integration`) when the promotion lands.
- Only verify that the branch carries its own **net-new delta** correctly (the code this story introduces that does not yet exist anywhere in the pipeline).
- Do **not** flag pre-existing infrastructure classes (`{{APEX_PREFIX}}_OrderRepository`, `{{APEX_PREFIX}}_OrderConstants`, etc.) as missing unless the branch itself introduces a new method or constant on them that isn't on any other promoted branch.

### Implications for deployment

When deploying to a dev sandbox during development:

- The org already has everything from prior promotions; you are only adding the delta for the current story.
- If a compile failure references a symbol that exists in a sibling dev branch (not yet on the current sandbox), retrieve and deploy that branch's file first, or confirm the symbol is already in the org from a previous deployment.

## Rules

- **Never** run `git commit` or `git push` — commits go through your {{CICD_TOOL}}
- `git add` is fine; staging is safe
- Retrieve and diff before deploying to avoid overwriting org-only changes
- Use `--ignore-conflicts` only after confirming the diff is safe
