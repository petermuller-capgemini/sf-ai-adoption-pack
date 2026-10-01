---
name: experience-site-publish
description: Publish (republish) a Salesforce Experience Cloud site via SF CLI REST API after deploying LWC or metadata changes. Use when the user asks to publish, republish, or flush the cache on a community or Experience site.
---

# Experience Cloud Site Publish via SF CLI

After deploying LWC components or metadata that affect an Experience Cloud (Community) site, the site must be republished for the LWR bundle cache to be refreshed. Deployments alone are not enough — the site serves a pre-built static bundle that only updates on publish.

## When to republish

- After deploying any LWC component used in an Experience Cloud site
- After changing site configuration metadata (e.g. `.network-meta.xml`)
- After any change that isn't reflected in the live site despite a successful deploy

## Step 1 — Find the Community Id

If you don't already know the Community Id for the site, query it:

```bash
sf data query \
  --query "SELECT Id, Name, UrlPathPrefix FROM Network WHERE UrlPathPrefix = '<site-path-prefix>'" \
  --target-org <org-alias>
```

Example:

| Org | Site | Community Id |
|---|---|---|
| `<org-alias>` | `my-site` | `<community-id>` |

## Step 2 — Trigger publish

```bash
sf api request rest \
  --method POST \
  --body '{"mode":"raw"}' \
  "/services/data/{{SF_API_VERSION}}/connect/communities/<communityId>/publish" \
  --target-org <org-alias>
```

The response contains a `jobId` field — save it for polling.

**Note:** `--body` must be `'{"mode":"raw"}'` — this is required by the API even though the value is ignored. Omitting it or using an empty body causes an error.

## Step 3 — Poll until complete

```bash
until sf data query \
  --query "SELECT Status FROM BackgroundOperation WHERE Id = '<jobId>'" \
  --target-org <org-alias> 2>&1 | grep -q Complete; do sleep 5; done && echo "Published"
```

Typical publish time: 15–60 seconds. Status values: `Running` → `Complete`.

The org also sends an email confirmation when publishing finishes.

## Step 4 — Verify in browser

After publish completes, do a **hard reload** (Cmd+Shift+R / Ctrl+Shift+R) or open an incognito window to bypass the browser's own cache.

For guest pages that use a one-time token (e.g. `guest-order-details?token=...`), note that tokens expire — do a fresh search to get a new URL rather than reusing the old one.

## Important caveats

### LWC deploy must include ALL component files

When deploying an LWC bundle via `--metadata-dir`, the metadata API treats the deploy as authoritative — any files in the bundle that are **not included** in the deploy package will be **deleted** from the org. Always copy all files (`.html`, `.js`, `.css`, `.js-meta.xml`) into the deploy directory:

```bash
# Correct — all files included
cp force-app/main/default/lwc/myComponent/*.{html,js,css,xml} deploy/lwc/myComponent/
```

Missing a `.css` file will silently wipe the component's styles from the org.

### Deploy directory structure

The `--metadata-dir` flag expects the `package.xml` at the root and metadata folders directly beneath it — **not** the `force-app/main/default/` path prefix:

```
deploy/
  package.xml
  lwc/
    myComponent/
      myComponent.html
      myComponent.js
      myComponent.css
      myComponent.js-meta.xml
```

### Use TMPDIR / scratchpad for the deploy directory

Avoid `/tmp` directly — use `$TMPDIR` in sandbox mode, or the session scratchpad path when sandbox mode blocks `/tmp` writes.

### TypeInferenceError workaround

If `sf project deploy start --metadata ApexClass:ClassName` fails with a `TypeInferenceError` caused by an unrelated metadata file elsewhere in the org (e.g. a custom OAuth security settings file with a non-standard naming pattern), use `--metadata-dir` with an isolated deploy directory instead of the `--metadata` flag.

## Full example

```bash
# 1. Build isolated deploy dir
DEPLOY="$TMPDIR/deploy_lwc"
mkdir -p "$DEPLOY/lwc/{{APEX_PREFIX}}_myComponent"
cp force-app/main/default/lwc/{{APEX_PREFIX}}_myComponent/* "$DEPLOY/lwc/{{APEX_PREFIX}}_myComponent/"
cat > "$DEPLOY/package.xml" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>{{APEX_PREFIX}}_myComponent</members>
        <name>LightningComponentBundle</name>
    </types>
    <version>{{SF_API_VERSION}}</version>
</Package>
EOF

# 2. Deploy to org
sf project deploy start --metadata-dir "$DEPLOY" --target-org <org-alias>

# 3. Publish the Experience site
PUBLISH_RESPONSE=$(sf api request rest \
  --method POST \
  --body '{"mode":"raw"}' \
  "/services/data/{{SF_API_VERSION}}/connect/communities/<community-id>/publish" \
  --target-org <org-alias>)
JOB_ID=$(echo "$PUBLISH_RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)['jobId'])")

# 4. Wait for completion
until sf data query \
  --query "SELECT Status FROM BackgroundOperation WHERE Id = '$JOB_ID'" \
  --target-org <org-alias> 2>&1 | grep -q Complete; do sleep 5; done
echo "Site published"
```
