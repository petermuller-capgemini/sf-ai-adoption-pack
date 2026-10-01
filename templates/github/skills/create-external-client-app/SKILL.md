---
name: create-external-client-app
description: Create and configure a Salesforce External Client App (ECA) for OAuth 2.0 JWT Bearer flow — including integration user, PSG assignment, OAuth settings, policy, security settings, and certificate upload. Use when an external system (e.g. Azure APIM) needs to authenticate into Salesforce REST APIs via JWT.
---

# Create External Client App (JWT Bearer Flow)

Creates a full ECA setup for an external system calling Salesforce REST APIs using OAuth 2.0 JWT Bearer Token flow. Based on a real-world JWT Bearer ECA setup.

**Run with:** `/create-external-client-app [app-name] [org-alias]`

---

## Overview of what gets created

| Artefact | Type | How |
|----------|------|-----|
| `{{APEX_PREFIX}}_<Name>.eca-meta.xml` | ExternalClientApplication | SF CLI deploy |
| OAuth settings (scopes + cert) | ExtlClntAppOauthSettings | SOAP Metadata API |
| OAuth policy (flows, IP, refresh) | ExtlClntAppOauthConfigurablePolicies | SOAP Metadata API |
| OAuth security container | ExtlClntAppOauthSecuritySettings | UI (let it create) |
| Integration user | User SObject | REST API |
| PSG assignment | PermissionSetAssignment | REST API |
| Certificate | ClientAssertionCertificate field | SOAP Metadata API |

---

## Critical findings — read before starting

### 1. The SF CLI does not know these metadata types

The CLI warns `Unable to find type ExtlClntAppOauthSecuritySettings in registry` (and the same for `ExtlClntAppOauthSettings`, `ExtlClntAppOauthConfigurablePolicies`). These types exist in the org's Metadata API at a recent API version but are not in the CLI's registry. **Do not deploy them via `sf project deploy start`** — use SOAP Metadata API directly.

### 2. Do NOT deploy ExtlClntAppOauthSecuritySettings or ExtlClntAppOauthConfigurablePolicies before the UI saves for the first time

The UI generates internal link fields (`oauthLink`, duplicate key on `{{APEX_PREFIX}}_<Name>_oauthSecurity`) when you first save. If these records exist beforehand, the UI throws:
- `Cannot invoke "String.split(String)" because "oauthLink" is null`
- `duplicate key value violates unique constraint "ak3tl_setup_entity_data"`

**Correct order:**
1. Deploy `ExternalClientApplication` ECA file only
2. Let the user save the ECA in Setup UI (creates `oauthSecurity` + `oauthPlcy` with correct internal links)
3. SOAP-deploy `ExtlClntAppOauthSettings` with the certificate
4. SOAP-deploy `ExtlClntAppOauthConfigurablePolicies` to set policy (IP, flows, permitted users, PSes)

### 3. The certificate goes in ExtlClntAppOauthSettings, not in the ECA file

The `clientAssertionCertificate` field is on `ExtlClntAppOauthSettings`. Strip the PEM headers, pass the base64 body. The UI cannot upload an external CA-issued cert — it must be deployed via metadata.

### 4. SOAP package structure for singlePackage=true

Root-level `package.xml`, no `unpackaged/` prefix. File extensions:
- `extlClntAppOauthSettings/*.ecaOauth`
- `extlClntAppOauthPolicies/*.ecaOauthPlcy`
- `extlClntAppOauthSecuritySettings/*.ecaOauthSecurity`

### 5. All SF CLI calls need dangerouslyDisableSandbox: true

The CLI writes to `~/.sf/sf-YYYY-MM-DD.log` which is outside the sandbox write allowlist.

---

## Step 1 — Create the ECA metadata file

```xml
<!-- force-app/main/default/externalClientApps/{{APEX_PREFIX}}_<Name>.eca-meta.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<ExternalClientApplication xmlns="http://soap.sforce.com/2006/04/metadata">
    <contactEmail>{{CONTACT_EMAIL}}</contactEmail>
    <description>External Client App for <system>. Enables OAuth 2.0 JWT Bearer Flow...</description>
    <distributionState>Packaged</distributionState>
    <isProtected>false</isProtected>
    <label>{{APEX_PREFIX}} <Name></label>
    <orgScopedExternalApp><org-id>:{{APEX_PREFIX}}_<Name></orgScopedExternalApp>
</ExternalClientApplication>
```

Deploy via CLI:
```bash
sf project deploy start --target-org <org-alias> \
  --source-dir force-app/main/default/externalClientApps/{{APEX_PREFIX}}_<Name>.eca-meta.xml
```

Query the new ECA ID:
```bash
sf data query --target-org <org-alias> \
  --query "SELECT Id FROM ExternalClientApplication WHERE DeveloperName='{{APEX_PREFIX}}_<Name>'"
```

---

## Step 2 — Create the integration user

```bash
SF_ACCESS_TOKEN=$(sf org display --target-org <org-alias> --json | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['accessToken'])")
SF_INSTANCE=<instance-url>

curl -s -X POST \
  -H "Authorization: Bearer $SF_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  "$SF_INSTANCE/services/data/{{SF_API_VERSION}}/sobjects/User" \
  -d '{
    "Username": "<org-prefix>.<name>@{{COMPANY_DOMAIN}}.<org-alias>",
    "Email": "<org-prefix>.<name>@{{COMPANY_DOMAIN}}",
    "FirstName": "{{APEX_PREFIX}}",
    "LastName": "<Name> Integration",
    "Alias": "<8-char>",
    "ProfileId": "<profile-id>",
    "TimeZoneSidKey": "Europe/London",
    "LocaleSidKey": "en_GB",
    "LanguageLocaleKey": "en_US",
    "EmailEncodingKey": "UTF-8",
    "IsActive": true
  }'
```

Profile `<profile-id>` = `{{APEX_PREFIX}}_MA_API_Integration` ({{ORG_ALIAS}}). Re-query for other orgs:
```bash
sf data query --target-org <org-alias> --query "SELECT Id FROM Profile WHERE Name='{{APEX_PREFIX}}_MA_API_Integration'"
```

---

## Step 3 — Assign the PSG

```bash
# Get PSG PermissionSet ID (PSGs appear in PermissionSet with the same Name)
sf data query --target-org <org-alias> \
  --query "SELECT Id FROM PermissionSet WHERE Name='{{APEX_PREFIX}}_APIM_Integration'"

curl -s -X POST \
  -H "Authorization: Bearer $SF_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  "$SF_INSTANCE/services/data/{{SF_API_VERSION}}/sobjects/PermissionSetAssignment" \
  -d '{"AssigneeId": "<user-id>", "PermissionSetId": "<psg-id>"}'
```

`{{APEX_PREFIX}}_APIM_Integration` PSG (ID `<psg-id>` on {{ORG_ALIAS}}) bundles:
- `{{APEX_PREFIX}}_Manage_Order_API` — all Order API Apex classes + field access
- `{{APEX_PREFIX}}_Integration_User` — Named Credential + integration framework access
- `{{APEX_PREFIX}}_OMS_Manager` — OMS object permissions
- `Function_Profile_Master_Account_Edit`

---

## Step 4 — Let the UI save the ECA first

In Setup → External Client Apps → {{APEX_PREFIX}} \<Name\> → Edit:

- **Callback URL:** `https://test.salesforce.com/services/oauth2/success`
- **Selected OAuth Scopes:** `Manage user data via APIs (api)` + `Perform requests at any time (refresh_token)`
- Save

This creates `{{APEX_PREFIX}}_<Name>_oauthSecurity` and the internal `oauthLink` reference. **Do not proceed to steps 5–6 until the UI save succeeds.**

---

## Step 5 — SOAP-deploy the certificate via ExtlClntAppOauthSettings

The certificate body is the PEM file with headers stripped and newlines removed.

```python
import base64, zipfile, io, re, json, subprocess, tempfile, os

result = subprocess.run(['sf', 'org', 'display', '--target-org', '<org-alias>', '--json'], capture_output=True, text=True)
d = json.loads(result.stdout)
TOKEN = d['result']['accessToken']
INSTANCE = d['result']['instanceUrl']
SOAP_EP = f"{INSTANCE}/services/Soap/m/{{SF_API_VERSION}}"

with open('/path/to/certificate.crt') as f:
    pem = f.read()
cert_body = ''.join(
    line for line in pem.splitlines()
    if 'BEGIN CERTIFICATE' not in line and 'END CERTIFICATE' not in line and line.strip()
)

oauth_settings = f'''<?xml version="1.0" encoding="UTF-8"?>
<ExtlClntAppOauthSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <clientAssertionCertificate>{cert_body}</clientAssertionCertificate>
    <commaSeparatedOauthScopes>Api, RefreshToken</commaSeparatedOauthScopes>
    <externalClientApplication>{{APEX_PREFIX}}_<Name></externalClientApplication>
    <isFirstPartyAppEnabled>false</isFirstPartyAppEnabled>
    <label>{{APEX_PREFIX}}_<Name>_oauth</label>
</ExtlClntAppOauthSettings>'''

package_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>{{APEX_PREFIX}}_<Name>_oauth</members>
        <name>ExtlClntAppOauthSettings</name>
    </types>
    <version>{{SF_API_VERSION}}</version>
</Package>'''

buf = io.BytesIO()
with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('package.xml', package_xml)
    z.writestr('extlClntAppOauthSettings/{{APEX_PREFIX}}_<Name>_oauth.ecaOauth', oauth_settings)

zip_b64 = base64.b64encode(buf.getvalue()).decode()

deploy_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<env:Envelope xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">
  <env:Header>
    <urn:SessionHeader xmlns:urn="http://soap.sforce.com/2006/04/metadata">
      <urn:sessionId>{TOKEN}</urn:sessionId>
    </urn:SessionHeader>
  </env:Header>
  <env:Body>
    <urn:deploy xmlns:urn="http://soap.sforce.com/2006/04/metadata">
      <urn:ZipFile>{zip_b64}</urn:ZipFile>
      <urn:DeployOptions>
        <urn:checkOnly>false</urn:checkOnly>
        <urn:ignoreWarnings>true</urn:ignoreWarnings>
        <urn:rollbackOnError>true</urn:rollbackOnError>
        <urn:singlePackage>true</urn:singlePackage>
      </urn:DeployOptions>
    </urn:deploy>
  </env:Body>
</env:Envelope>"""

with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, dir='/tmp') as f:
    f.write(deploy_body)
    tmpfile = f.name

result = subprocess.run(
    ['curl', '-s', '-X', 'POST',
     '-H', 'Content-Type: text/xml;charset=UTF-8',
     '-H', 'SOAPAction: deploy',
     f'--header=Authorization: Bearer {TOKEN}',
     '--data-binary', f'@{tmpfile}',
     SOAP_EP],
    capture_output=True, text=True
)
os.unlink(tmpfile)
m = re.search(r'<id>([^<]+)</id>', result.stdout)
print('Deploy ID:', m.group(1) if m else result.stdout[:300])
```

Poll for completion:
```bash
curl -s -H "Authorization: Bearer $SF_ACCESS_TOKEN" \
  "$SF_INSTANCE/services/data/{{SF_API_VERSION}}/metadata/deployRequest/<deploy-id>?includeDetails=true" \
  | python3 -c "
import json,sys; dr=json.load(sys.stdin).get('deployResult',{})
print(dr.get('status'), dr.get('done'), dr.get('success'))
errs=dr.get('details',{}).get('componentFailures',[])
if isinstance(errs,dict): errs=[errs]
for e in errs: print('ERR:', e.get('problem'))
"
```

---

## Step 6 — SOAP-deploy the OAuth policy

Deploy **after** the UI save (step 4) to avoid duplicate-key conflicts. Do not include `namedUserJwtSessionTimeoutType` or `sessionTimeoutInMinutes` — those fields cause "Invalid plugin settings" if Named User JWT isn't toggled on at the same time.

```xml
<!-- extlClntAppOauthPolicies/{{APEX_PREFIX}}_<Name>_oauthPlcy.ecaOauthPlcy -->
<?xml version="1.0" encoding="UTF-8"?>
<ExtlClntAppOauthConfigurablePolicies xmlns="http://soap.sforce.com/2006/04/metadata">
    <commaSeparatedPermissionSet>{{APEX_PREFIX}}_Integration_User</commaSeparatedPermissionSet>
    <externalClientApplication>{{APEX_PREFIX}}_<Name></externalClientApplication>
    <ipRelaxationPolicyType>Enforce</ipRelaxationPolicyType>
    <isClientCredentialsFlowEnabled>false</isClientCredentialsFlowEnabled>
    <isGuestCodeCredFlowEnabled>false</isGuestCodeCredFlowEnabled>
    <isTokenExchangeFlowEnabled>false</isTokenExchangeFlowEnabled>
    <label>{{APEX_PREFIX}}_<Name>_oauthPlcy</label>
    <permittedUsersPolicyType>AdminApprovedPreAuthorized</permittedUsersPolicyType>
    <refreshTokenPolicyType>Infinite</refreshTokenPolicyType>
    <requiredSessionLevel>STANDARD</requiredSessionLevel>
</ExtlClntAppOauthConfigurablePolicies>
```

Package:
```xml
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>{{APEX_PREFIX}}_<Name>_oauthPlcy</members>
        <name>ExtlClntAppOauthConfigurablePolicies</name>
    </types>
    <version>{{SF_API_VERSION}}</version>
</Package>
```

File path in ZIP: `extlClntAppOauthPolicies/{{APEX_PREFIX}}_<Name>_oauthPlcy.ecaOauthPlcy`

---

## Step 7 — Enable Named User JWT Bearer in the UI

Setup → External Client Apps → {{APEX_PREFIX}} \<Name\> → Edit → OAuth Flows section → toggle on **Named User JWT Bearer**.

This cannot be done via metadata alone (the toggle sets an internal field that only the policy's `namedUserJwtSessionTimeoutType` reflects after the fact).

---

## Step 8 — Pre-authorize the integration user

Because `permittedUsersPolicyType = AdminApprovedPreAuthorized` and `commaSeparatedPermissionSet = {{APEX_PREFIX}}_Integration_User`, any user with the `{{APEX_PREFIX}}_Integration_User` PS is automatically pre-authorized. The integration user gets this via the `{{APEX_PREFIX}}_APIM_Integration` PSG (step 3) — no manual pre-auth needed.

---

## Verification

```bash
# Confirm cert and scopes are set
sf data query --target-org <org-alias> --query \
  "SELECT Id, OauthScopesAPI, OauthScopesREFRESH_TOKEN, ClientAssertionCertificate \
   FROM ExtlClntAppOauthSettings WHERE ExternalClientApplicationId='<eca-id>'"

# Confirm user and PSG
sf data query --target-org <org-alias> --query \
  "SELECT PermissionSet.Name FROM PermissionSetAssignment WHERE AssigneeId='<user-id>'"
```

---

## External system JWT claim requirements

For the external system (e.g. Azure APIM) to authenticate:

| JWT claim | Value |
|-----------|-------|
| `iss` | Consumer key of the ECA (shown in Setup → External Client Apps → {{APEX_PREFIX}} \<Name\>) |
| `sub` | `<org-prefix>.<name>@{{COMPANY_DOMAIN}}.<org-alias>` |
| `aud` | `https://test.salesforce.com` (sandbox) / `https://login.salesforce.com` (prod) |
| `exp` | Unix timestamp, max 3 minutes ahead |
| Signing key | Private key matching the uploaded certificate |

Token endpoint: `https://test.salesforce.com/services/oauth2/token`
Grant type: `urn:ietf:params:oauth:grant-type:jwt-bearer`

---

## Retrieving existing ECA config for reference

The SF CLI cannot retrieve these types cleanly. Use SOAP directly:

```bash
SF_ACCESS_TOKEN=$(sf org display --target-org <org> --json | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['accessToken'])")
SF_INSTANCE=<instance>

# Retrieve all OAuth settings and policies (wildcard)
curl -s -X POST \
  -H "Content-Type: text/xml;charset=UTF-8" \
  -H "SOAPAction: retrieve" \
  "$SF_INSTANCE/services/Soap/m/{{SF_API_VERSION}}" \
  -d '... <members>*</members> <name>ExtlClntAppOauthSettings</name> ...'
# Then checkRetrieveStatus with includeZip=true and unzip the result
```

Known file extensions by type:

| Metadata type | Directory | Extension |
|--------------|-----------|-----------|
| ExternalClientApplication | `externalClientApps/` | `.eca` / `.eca-meta.xml` |
| ExtlClntAppOauthSettings | `extlClntAppOauthSettings/` | `.ecaOauth` |
| ExtlClntAppOauthConfigurablePolicies | `extlClntAppOauthPolicies/` | `.ecaOauthPlcy` |
| ExtlClntAppOauthSecuritySettings | `extlClntAppOauthSecuritySettings/` | `.ecaOauthSecurity` |
| ExtlClntAppGlobalOauthSettings | `extlClntAppGlobalOauthSettings/` | _(see describe)_ |
