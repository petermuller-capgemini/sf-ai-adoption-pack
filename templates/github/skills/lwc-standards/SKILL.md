---
name: lwc-standards
description: "Apply {{PROJECT_NAME}} LWC development standards — component structure, reactivity, SLDS, event patterns, data access hierarchy, Jest testing, and quality gates. Run with: /lwc-standards [componentName]"
---

# lwc-standards

Apply the full {{PROJECT_NAME}} Lightning Web Component development standards.

**Applies to:** `force-app/**/lwc/**`

---

## Component Structure

- Each LWC resides in its own folder under `force-app/main/default/lwc/`.
- **Folder naming**: start with `{{LWC_PREFIX}}` prefix, no hyphens within folder name (e.g., `{{LWC_PREFIX}}OrderTable`).
- **Reference in markup** using kebab-case: `<{{LWC_PREFIX}}-order-table></{{LWC_PREFIX}}-order-table>`.
- **PascalCase for class names** in JavaScript files.

### Bundle files

```
{{LWC_PREFIX}}OrderTable/
├── {{LWC_PREFIX}}OrderTable.html
├── {{LWC_PREFIX}}OrderTable.js
├── {{LWC_PREFIX}}OrderTable.js-meta.xml
├── {{LWC_PREFIX}}OrderTable.css           (optional)
├── labels.js                   (MANDATORY for {{LWC_PREFIX}}-prefixed components)
├── constants.js                (as needed; see Labels & Constants section)
└── __tests__/
    ├── {{LWC_PREFIX}}OrderTable.test.js   (MANDATORY)
    └── data/<wireAdapterName>.json  (when using @wire)
```

### API version

- Always set `<apiVersion>{{SF_API_VERSION}}</apiVersion>` in every `js-meta.xml`.
- Never use a version more than two releases behind the org's current release.

### Labels and Constants ({{LWC_PREFIX}}-prefixed components only)

**All {{LWC_PREFIX}}-prefixed LWCs must externalize labels and constants** to dedicated co-located files. This removes magic strings from component logic and ensures consistency.

#### labels.js (MANDATORY)
- Co-locate a `labels.js` file with your component.
- Import all custom labels using `@salesforce/label/c.{{APEX_PREFIX}}_*` with camelCase property names (drop `lbl` or `label` prefixes from the label name).
- Spread in any labels from `c/{{LWC_PREFIX}}CommonLabels` using `...COMMON_LABELS`.
- Export a frozen object: `const LABELS = Object.freeze({...}); export default LABELS;`.
- The main component file imports it: `import LABELS from './labels';` and uses `LABELS.propertyName`.
- Existing template-facing fields like `label = {...}` or `labels = LABELS` are built from `LABELS` so HTML bindings continue to work.
- If `labels.js` already exists in an older component, extend it with its existing export name instead of creating a new one.

Example (`{{LWC_PREFIX}}_orderDetailPage/labels.js`):
```javascript
import COMMON_LABELS from 'c/{{LWC_PREFIX}}CommonLabels';
import cancelBookingError from '@salesforce/label/c.{{APEX_PREFIX}}_CancelActionError';
import cancelBookingSuccess from '@salesforce/label/c.{{APEX_PREFIX}}_CancelActionSuccess';

const LABELS = Object.freeze({
    ...COMMON_LABELS,
    cancelBookingError,
    cancelBookingSuccess,
});

export default LABELS;
```

#### constants.js (as needed)
- Co-locate a `constants.js` file for status values, event names, paths, regex patterns, option lists, storage keys, page sizes, record type constants, and other non-label data.
- Use named exports (no default export).
- Event name constants use the `EVT_` prefix (e.g., `EVT_ITEMS_UPDATED`).
- Import in the main file: `import { CONSTANT_NAME, EVT_NAME } from './constants';`.
- Check existing shared utilities (`c/{{LWC_PREFIX}}OrderConstants`, `c/{{LWC_PREFIX}}CommonLabels`, `c/{{LWC_PREFIX}}DateUtils`) before creating local constants — do not duplicate.
- Functions, loggers, and anything dependent on component imports stay in the main file, not constants.js.

Example (`{{LWC_PREFIX}}_amendPersonalDetails/constants.js`):
```javascript
export const TITLE_OPTIONS = [
    { value: 'Mr', label: 'Mr' },
    { value: 'Mrs', label: 'Mrs' },
];

export const EVT_CANCEL_CHANGES = 'cancelchanges';
export const EVT_DETAILS_UPDATED = 'personaldetailsupdated';

export const NAME_PATTERN = /^[a-zA-Z0-9](?:[a-zA-Z0-9\s'&.-]*[a-zA-Z0-9])?$/;
```

#### User-visible text
- All hardcoded, user-facing strings must become custom labels (in `labels.js`), not constants.
- This applies to button labels, error messages, section headings, and any text shown to end users.

#### Testing
- Jest tests mock `@salesforce/label/...` virtually; re-exports needed by tests (e.g., a regex pattern like `NAME_PATTERN`) can be re-exported from the main file for test use.

### Core Design Principles

- **Single responsibility**: presentational components for UI, container components for logic/data, utility modules for shared services.
- Avoid tight coupling — don't combine modal rendering, form handling, service calls, and navigation in one component.
- **Document `@api` properties** — every `@api` property must have JSDoc with description, type, and default value.

---

## Core Principles

### 1. Lightning Components Over HTML Tags

Use Lightning base components: `<lightning-button>` not `<button>`, `<lightning-input>` not `<input>`, `<lightning-combobox>` not `<select>`, etc.

### 2. Reactive Properties

```javascript
// ✅ Primitives are reactive without @track
simpleValue = 'initial';
count = 0;
handleUpdate() { this.count++; }  // Reactive

// ✅ @track ONLY for nested mutations without reassignment
@track complexData = { user: { preferences: { theme: 'dark' } } };
handleDeepUpdate() { this.complexData.user.preferences.theme = 'light'; }

// ✅ BETTER: Immutable patterns (no @track needed)
regularData = { user: { name: 'John' } };
handleImmutableUpdate() { this.regularData = { ...this.regularData, user: { ...this.regularData.user, name: 'Jane' } }; }
```

### 3. SLDS Compliance

Use SLDS utility classes with `slds-var-` prefix:
```html
<div class="slds-var-m-around_medium slds-var-p-top_large">
<div class="slds-grid slds-wrap slds-gutters_small">
<h2 class="slds-text-heading_medium slds-var-m-bottom_small">
```

### 4. Avoid Custom CSS (Prefer SLDS)

Use CSS custom properties (design tokens) when custom CSS is necessary; never override SLDS base classes.

### 5. Event Handling Patterns

- **Parent → child**: pass data as `@api` properties (prefer primitives)
- **Child → parent**: dispatch a `CustomEvent`; the parent listens and updates its own data
- **`@api` properties are read-only after initialization** — never assign back to your own `@api` property; create a shallow copy: `const copy = { ...this.myProp };`
- Use **primitive types** in `event.detail`; if passing objects, copy first: `detail: { ...this.item }`
- Use **default `bubbles: false, composed: false`** unless genuinely crossing shadow boundaries

```javascript
// ✅ Default: private, non-bubbling
this.dispatchEvent(new CustomEvent('itemselected', { detail: item.id }));

// ⚠️ Cross-shadow: document as public API contract
this.dispatchEvent(new CustomEvent('{{LWC_PREFIX}}-item-selected', { detail: item.id, bubbles: true, composed: true }));
```

### 6. Data Access Hierarchy

Always select the highest-priority option:

1. **LDS base components** (`lightning-record-form`, etc.) — for single record create/read/update
2. **GraphQL wire adapter** — preferred for multi-field or multi-object reads
3. **LDS wire adapters** (`getRecord`, etc.) — single-record reads
4. **Apex** — use only when above don't apply

**Critical LDS limitations:**
- Custom Metadata Types (CMT) are NOT supported by LDS — use `@AuraEnabled(cacheable=true)` Apex.
- Apex and LDS do NOT share a data cache — do not mix them for the same records.

**Cache invalidation:**
```javascript
import { notifyRecordUpdateAvailable } from 'lightning/uiRecordApi';
async handleSave() {
    await updateMyRecord({ recordId: this.recordId, ...fields });
    await notifyRecordUpdateAvailable([{ recordId: this.recordId }]);
}
```

### 7. Error Handling

```javascript
async handleAsyncOperation() {
    this.isLoading = true;
    this.error = null;
    try {
        const result = await this.performOperation();
        this.dispatchEvent(new ShowToastEvent({ title: 'Success', message: 'Done', variant: 'success' }));
    } catch (error) {
        this.error = error;
        this.dispatchEvent(new ShowToastEvent({ title: 'Error', message: error.body?.message || 'An error occurred', variant: 'error', mode: 'sticky' }));
    } finally {
        this.isLoading = false;
    }
}
```

### 8. Performance Optimization

Use `lwc:if`, `lwc:elseif`, `lwc:else` (API v58.0+). Do NOT use legacy `if:true`/`if:false` in new components.

Use keyed iteration: `key="{item.id}"` for `for:each`.

### 9. Accessibility

- Include ARIA attributes for interactive elements.
- Implement keyboard navigation for modals and dropdowns.
- Use semantic HTML (`<section>`, `<header>`, `<footer>`, `<nav>`).
- Test with screen readers.

---

## Jest Testing (Mandatory)

Every LWC component bundle **must** include a Jest test file.

### Test anatomy

```javascript
import { createElement } from 'lwc';
import {{LWC_PREFIX}}OrderTable from 'c/{{LWC_PREFIX}}OrderTable';

describe('c-{{LWC_PREFIX}}-order-table', () => {
    afterEach(() => {
        while (document.body.firstChild) {
            document.body.removeChild(document.body.firstChild);
        }
    });

    it('renders the component with default state', () => {
        const element = createElement('c-{{LWC_PREFIX}}-order-table', { is: {{LWC_PREFIX}}OrderTable });
        document.body.appendChild(element);
        const heading = element.shadowRoot.querySelector('h2');
        expect(heading.textContent).toBe('Orders');
    });
});
```

**Key rules:**
- Top-level `describe` must match kebab-case element name (e.g., `c-{{LWC_PREFIX}}-order-table`)
- `afterEach()` must clean up DOM
- Always use `element.shadowRoot.querySelector()` — never `document.querySelector()`
- Test files must end in `.test.js`

### Asynchronous updates

```javascript
element.title = 'Updated Title';
return Promise.resolve().then(() => {
    expect(element.shadowRoot.querySelector('h2').textContent).toBe('Updated Title');
});
```

### @wire adapter testing

```javascript
import { getRecord } from 'lightning/uiRecordApi';
const mockGetRecord = require('./data/getRecord.json');

it('renders from wire data', () => {
    const element = createElement('c-{{LWC_PREFIX}}-order-card', { is: {{LWC_PREFIX}}OrderCard });
    document.body.appendChild(element);
    getRecord.emit(mockGetRecord);
    return Promise.resolve().then(() => {
        expect(element.shadowRoot.querySelector('.order-name').textContent).toBe('Order-001');
    });
});
```

### Coverage requirements

| Scenario | Minimum | Target |
|---|---|---|
| All LWC components | 80% | **90%** |
| Business-critical components | 90% | **100%** |
| Security/access-control logic | 100% | 100% |

### Mandatory test scenarios checklist

- [ ] Initial render — default state
- [ ] `@api` property changes — re-renders correctly
- [ ] User interactions — event handlers fire and update state
- [ ] Wire adapter — success path
- [ ] Wire adapter — error path
- [ ] Imperative Apex — success path (if used)
- [ ] Imperative Apex — error path (if used)
- [ ] Conditional rendering — all `lwc:if` branches exercised
- [ ] Custom event dispatch — correct `detail` payload

---

## Common Anti-Patterns to Avoid

- **Direct DOM Manipulation**: never `document.querySelector()` or similar
- **jQuery or External Libraries**: avoid non-Lightning compatible libraries
- **Inline Styles**: use SLDS classes instead of `style` attributes
- **Hardcoded Values**: use custom labels, custom metadata, or constants
- **Magic numbers**: declare as named constants
- **Locale hardcoding**: use `LOCALE` from `@salesforce/i18n/locale`
- **Unnecessary `@track`**: use immutable patterns instead
- **Memory Leaks**: always clean up event listeners in `disconnectedCallback()`

---

## Structured Logging in LWC

```javascript
import { createLogger } from 'c/{{LOGGER_FACTORY}}';

export default class {{LWC_PREFIX}}Example extends LightningElement {
    logger = createLogger('{{LWC_PREFIX}}Example');
    handleClick() {
        this.logger.info('Button clicked, user {0}', 'currentUser');
    }
}
```

---

## Quality Gates

### Lint and Format

```bash
# ESLint
npm run lint:all

# Prettier
npm run format:check

# Jest tests for specific component
npm run test:unit -- --testPathPattern {{LWC_PREFIX}}OrderTable

# With coverage
npm run test:unit:coverage

# IDOR scan on Apex controller
python3 .github/skills/salesforce-code-quality/scripts/idor_scanner.py --files {{APEX_PREFIX}}_OrderController.cls --output terminal
```

Pre-commit hooks (husky + lint-staged) auto-run ESLint `--fix` + Prettier on staged files on `git commit`.

### Component Checklist

- [ ] **{{LWC_PREFIX}}-prefixed components** — `labels.js` exists and exports frozen `LABELS` object; all `@salesforce/label` imports are in `labels.js`, not the main file
- [ ] **No hardcoded user-visible strings** in component JS — all labels are in `labels.js`, imported and used via `LABELS.propertyName`
- [ ] **constants.js** exists (if needed) — status values, event names, paths, regex patterns, option lists use named exports; no default export
- [ ] **No duplicate constants** — checked `c/{{LWC_PREFIX}}OrderConstants`, `c/{{LWC_PREFIX}}CommonLabels`, `c/{{LWC_PREFIX}}DateUtils`, and other shared utilities before creating local ones
- [ ] **Event names follow naming** — event name constants use `EVT_` prefix (e.g., `EVT_ITEM_SELECTED`)
- [ ] **No direct `@salesforce/label` imports** in main component file — all labels come through `labels.js`
