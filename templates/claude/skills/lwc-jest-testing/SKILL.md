---
name: lwc-jest-testing
description: "Create Jest unit tests for {{LWC_PREFIX}} LWC components in this project. Reads the component JS to discover Apex imports, wire adapters, @api properties, and DOM structure, then generates a passing __tests__/<name>.test.js following the hard-won patterns from this codebase. Run with: /lwc-jest-testing <componentName or path>. Omit the argument to scan for all LWCs under force-app/main/default/lwc/ that have no __tests__ directory."
disable-model-invocation: false
---

# lwc-jest-testing

Generate Jest unit tests for one or more {{LWC_PREFIX}} LWC components.

## Invocation

```
/lwc-jest-testing myComponent
/lwc-jest-testing force-app/main/default/lwc/myComponent
/lwc-jest-testing          ← scans all LWCs missing __tests__
```

---

## Step 1 — Discover targets

If an argument was given, resolve it to the component directory:
- Accept either the bare component name (`myComponent`) or a full path.
- Full path: `force-app/main/default/lwc/<componentName>`.

If no argument, run:
```bash
find force-app/main/default/lwc -mindepth 1 -maxdepth 1 -type d | while read d; do
  [ ! -d "$d/__tests__" ] && echo "$d"
done
```
Present the list and confirm with the user before proceeding.

---

## Step 2 — Read the component

For each target, read **all bundle files**:
- `<name>.js` — the primary source
- `<name>.html` — to understand the DOM structure, CSS classes used, and directives

Key things to extract from the JS:

| What to find | How it appears | Impact on test |
|---|---|---|
| Imperative Apex imports | `import foo from '@salesforce/apex/Ctrl.method'` | Needs `jest.mock(..., () => ({ default: jest.fn() }), { virtual: true })` + import the mock fn to call `.mockResolvedValue()` etc. |
| Wire Apex imports | `@wire(foo, {...})` where foo is an apex import | Needs `registerApexTestWireAdapter` |
| Wire LDS imports | `@wire(getRecord, {...})` etc. from `lightning/uiRecordApi` or similar | Needs `registerLdsTestWireAdapter` |
| Message channel | `import { MessageContext } from 'lightning/messageService'` or `@salesforce/messageChannel/...` | Mock the channel module: `jest.mock('@salesforce/messageChannel/...', () => ({}), { virtual: true })` |
| i18n locale | `import LOCALE from '@salesforce/i18n/locale'` | `jest.mock('@salesforce/i18n/locale', () => ({ default: 'en-GB' }), { virtual: true })` |
| `@api` properties | `@api propName` | Set via `Object.assign(el, { propName: value })` before `appendChild` or after + `await Promise.resolve()` |
| `static renderMode = 'light'` | Light DOM component | Use `el.querySelector()` NOT `el.shadowRoot.querySelector()` |
| NavigationMixin | `extends NavigationMixin(LightningElement)` | Import `{ CurrentPageReference }` from `'lightning/navigation'` and use `registerLdsTestWireAdapter` |
| CustomEvent dispatches | `this.dispatchEvent(new CustomEvent(...))` | Add event listener on `el` and assert with `jest.fn()` |

---

## Step 3 — Write the test file

Path: `force-app/main/default/lwc/<name>/__tests__/<name>.test.js`

### Ordering rules (CRITICAL — affects whether tests pass)

1. All `jest.mock(...)` calls **must come first**, before any `import` statements.
2. Only mock `@salesforce/apex/*` imports that are actually used in the component.
3. Only import the mock function variable if you actually call `.mockResolvedValue()` / `.mockRejectedValue()` on it in a test — otherwise omit the import to avoid lint warnings.

### Mock patterns

**Imperative Apex** (most common pitfall):
```js
// MUST have { virtual: true } — no physical file exists
// MUST return { default: jest.fn() } — the Babel transform does require(...).default
jest.mock('@salesforce/apex/{{APEX_PREFIX}}_MyCtrl.myMethod', () => ({ default: jest.fn() }), { virtual: true });

import myMethod from '@salesforce/apex/{{APEX_PREFIX}}_MyCtrl.myMethod';
// Now myMethod IS jest.fn() — call .mockResolvedValue() / .mockRejectedValue() on it directly
```

**Wire Apex adapter**:
```js
import myWiredApex from '@salesforce/apex/{{APEX_PREFIX}}_MyCtrl.myApexMethod';
import { registerApexTestWireAdapter } from '@salesforce/wire-service-jest-util';
const mockMyWiredApex = registerApexTestWireAdapter(myWiredApex);
// In test: mockMyWiredApex.emit({ ... }) or mockMyWiredApex.error({ ... })
```

**Wire LDS adapter** (`getRecord`, `CurrentPageReference`, `MessageContext`, etc.):
```js
import { CurrentPageReference } from 'lightning/navigation';
import { registerLdsTestWireAdapter } from '@salesforce/wire-service-jest-util';
const mockCurrentPageReference = registerLdsTestWireAdapter(CurrentPageReference);
// In test: mockCurrentPageReference.emit({ state: { ... } })
```

**DO NOT use `createApexTestWireAdapter`** — it has a timing incompatibility with how
`overriddenRegisterDecorators` runs at module-load time; the spy never gets wired.
`registerApexTestWireAdapter` is deprecated but works correctly via late-binding.

**Message channel** (no default export needed):
```js
jest.mock('@salesforce/messageChannel/{{APEX_PREFIX}}_MyChannel__c', () => ({}), { virtual: true });
```

**i18n locale**:
```js
jest.mock('@salesforce/i18n/locale', () => ({ default: 'en-GB' }), { virtual: true });
```

### Test file template

```js
// jest.mock calls FIRST — before imports
jest.mock('@salesforce/apex/{{APEX_PREFIX}}_MyCtrl.imperativeMethod', () => ({ default: jest.fn() }), { virtual: true });

import imperativeMethod from '@salesforce/apex/{{APEX_PREFIX}}_MyCtrl.imperativeMethod';
import wiredApexMethod from '@salesforce/apex/{{APEX_PREFIX}}_MyCtrl.wiredApexMethod';
import { registerApexTestWireAdapter } from '@salesforce/wire-service-jest-util';
import MyComponent from 'c/myComponent';
import { createElement } from 'lwc';

const mockWiredApexMethod = registerApexTestWireAdapter(wiredApexMethod);

async function flushPromises() {
    await new Promise((resolve) => setTimeout(resolve, 0));
}

describe('c-my-component', () => {
    afterEach(() => {
        while (document.body.firstChild) {
            document.body.removeChild(document.body.firstChild);
        }
        jest.clearAllMocks();
    });

    it('renders without error', async () => {
        const el = createElement('c-my-component', { is: MyComponent });
        document.body.appendChild(el);
        await Promise.resolve();
        expect(el.shadowRoot.querySelector('.my-wrapper')).not.toBeNull();
    });

    // ... additional tests
});
```

### DOM query rules

| Context | Query API |
|---|---|
| Shadow DOM (default) | `el.shadowRoot.querySelector('.class')` |
| Light DOM (`static renderMode = 'light'`) | `el.querySelector('.class')` — no `.shadowRoot` |

**Never use `querySelector('#someId')`** — LWC appends unique suffixes to `id` attributes in shadow DOM, so ID selectors always return `null`. Use:
- Class: `.my-class`
- Attribute: `input[type="email"]`, `input[autocomplete="postal-code"]`, `input[autocomplete="family-name"]`
- Role: `[role="alert"]`
- Data attribute: `[data-value="LHR5"]`

### What to test

Cover these scenarios in priority order:
1. **Initial render** — component mounts, key wrapper element present
2. **`@api` properties** — set via `Object.assign(el, {...})` before `appendChild`, assert effect
3. **Wire adapter — success** — `.emit(mockData)` then assert DOM
4. **Wire adapter — error** — `.error({...})` then assert error state shown
5. **Imperative Apex — success** — `method.mockResolvedValue(...)`, trigger action, assert result
6. **Imperative Apex — error** — `method.mockRejectedValue(new Error(...))`, assert graceful handling
7. **User interactions** — dispatch `CustomEvent` from DOM elements, assert state change
8. **Custom event dispatch** — `el.addEventListener('myevent', handler)`, trigger action, assert handler called
9. **Conditional rendering** — exercise both truthy and falsy branches of key `lwc:if` conditions

### What NOT to test
- Private methods (not `@api`) — can't be called externally, will throw
- Implementation details — test observable DOM/event behaviour only
- Scenarios that can't happen (e.g. impossible null paths the component guards against internally)

---

## Step 4 — Run and fix

```bash
npx jest force-app/main/default/lwc/<componentName> --no-coverage 2>&1
```

Fix any failures. Common issues:

| Error | Cause | Fix |
|---|---|---|
| `Cannot find module '@salesforce/apex/...'` | Missing `{ virtual: true }` on `jest.mock` | Add third arg `{ virtual: true }` |
| `Cannot read properties of undefined (reading 'mockResolvedValue')` | Mock factory returns `jest.fn()` directly instead of `{ default: jest.fn() }` | Change factory to `() => ({ default: jest.fn() })` |
| `Cannot set properties of null` when setting `input.value` | Used `#id` selector — LWC scopes ids | Switch to attribute selector: `input[type="email"]` etc. |
| `[LWC error]: Light DOM components can't render shadow DOM templates` | `static renderMode = 'light'` in JS but HTML missing `lwc:render-mode="light"` | Add `lwc:render-mode="light"` to `<template>` tag in HTML |
| `LWC1034: Ambiguous attribute value lwc:if="{expr}"` | Quoted curly brace: `lwc:if="{expr}"` | Remove quotes: `lwc:if={expr}` |
| `LWC1135: Invalid directive 'lwc:dom' on element` | `lwc:dom="manual"` is invalid in Light DOM | Remove the directive |
| Test hangs / async assertion fails | Async state not settled | Use `await flushPromises()` (not just `await Promise.resolve()`) after triggering async calls |
| `wire adapter was not called` with `createApexTestWireAdapter` | Timing issue — decorator decorator registration runs before adapter is set | Replace with `registerApexTestWireAdapter` |

---

## Step 5 — ESLint check

After tests pass, confirm no new lint warnings in the test file:
```bash
./node_modules/.bin/eslint force-app/main/default/lwc/<componentName>/__tests__/<componentName>.test.js
```

The `.eslintrc.json` already has `@lwc/lwc/no-async-operation: off` for `**/__tests__/**/*.js` — `setTimeout` inside `flushPromises()` is intentional and safe.

Remove any import variables that are declared but never used in a test assertion — they will generate `no-unused-vars` warnings and should be removed along with their corresponding `jest.mock` call if it's also unreferenced.

---

## Reference: project jest setup

- Jest runner: `@salesforce/sfdx-lwc-jest` (v7.8+)
- Wire util: `@salesforce/wire-service-jest-util`
- Apex Babel transform: `@lwc/jest-transformer` → `apex-scoped-import.js`
  - All `@salesforce/apex/*` imports become `require('...').default` at runtime
  - This is why the mock factory MUST return `{ default: jest.fn() }` not `jest.fn()`
- Run all tests: `npm run test:unit`
- Run one component: `npx jest <componentName> --no-coverage`
