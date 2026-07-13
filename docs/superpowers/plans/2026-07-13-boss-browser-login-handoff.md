# Boss Browser Login Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require visible user-confirmed Boss login before background mode, automatically open Boss in both modes, and expose login/risk failures instead of generic selector timeouts.

**Architecture:** A focused `boss_entry` module owns Boss entry navigation and pure page-state classification. Browser lifecycle commands run start/restart plus entry validation under one session lock; cold headless launches are rejected, while a confirmed headful-to-headless restart validates the authenticated chat shell. Existing risk-page auto-recovery is removed so callers can stop on the real Boss state.

**Tech Stack:** Node.js ESM, Puppeteer Core/CDP, Node built-in `node:test`, committed JavaScript and `.d.ts` artifacts.

---

### Task 1: Boss Entry State Classification

**Files:**
- Create: `tools/boss-cli/dist/browser/boss_entry.js`
- Create: `tools/boss-cli/dist/browser/boss_entry.d.ts`
- Create: `tools/boss-cli/test/boss_entry.test.js`
- Modify: `tools/boss-cli/dist/browser/index.js`
- Modify: `tools/boss-cli/dist/browser/index.d.ts`

- [ ] **Step 1: Write failing classifier tests**

```js
import {
  classifyBossEntrySnapshot,
  formatBossEntryFailure,
} from '../dist/browser/boss_entry.js';

test('classifies an authenticated chat shell as ready', () => {
  assert.deepEqual(classifyBossEntrySnapshot({
    url: 'https://www.zhipin.com/web/chat/index',
    title: 'BOSS直聘',
    hasMenu: true,
  }), { kind: 'ready', url: 'https://www.zhipin.com/web/chat/index', title: 'BOSS直聘' });
});

test('extracts Boss risk code without page contents', () => {
  const state = classifyBossEntrySnapshot({
    url: 'https://www.zhipin.com/web/passport/zp/403.html?code=32',
    title: 'www.zhipin.com',
    hasMenu: false,
  });
  assert.equal(state.kind, 'risk_blocked');
  assert.equal(state.code, '32');
  assert.match(formatBossEntryFailure(state), /code=32/);
});
```

- [ ] **Step 2: Run the test and verify RED**

Run: `node --test test/boss_entry.test.js`

Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `dist/browser/boss_entry.js`.

- [ ] **Step 3: Implement the pure classifier**

```js
export const BOSS_CHAT_ENTRY_URL = 'https://www.zhipin.com/web/chat/index';
export const BOSS_LOGIN_ENTRY_URL = 'https://www.zhipin.com/web/user/?ka=header-login';

export function classifyBossEntrySnapshot({ url, title, hasMenu }) {
  const parsed = new URL(url);
  const path = parsed.pathname;
  const base = { url, title };
  if (/\/web\/(?:common\/(?:403|nonsupport)\.html|user\/safe\/verify|passport\/)/.test(path)) {
    return { ...base, kind: 'risk_blocked', code: parsed.searchParams.get('code') ?? '' };
  }
  if (path.includes('/web/user/')) return { ...base, kind: 'login_required' };
  if ((path === '/web/chat' || path.startsWith('/web/chat/')) && hasMenu) {
    return { ...base, kind: 'ready' };
  }
  if (path === '/web/chat' || path.startsWith('/web/chat/')) {
    return { ...base, kind: 'missing_shell' };
  }
  return { ...base, kind: 'unexpected' };
}
```

`formatBossEntryFailure` must include only state kind, final URL, title, and recognized code. It must not include HTML, cookies, tokens, or page text.

- [ ] **Step 4: Export declarations and verify GREEN**

Run: `node --test test/boss_entry.test.js`

Expected: all entry classifier tests pass.

### Task 2: Entry Navigation and Lifecycle Handoff

**Files:**
- Modify: `tools/boss-cli/dist/browser/boss_entry.js`
- Modify: `tools/boss-cli/dist/browser/boss_entry.d.ts`
- Modify: `tools/boss-cli/dist/toolset/browser.js`
- Modify: `tools/boss-cli/dist/toolset/browser.d.ts`
- Modify: `tools/boss-cli/dist/toolset/login.js`
- Create: `tools/boss-cli/test/browser_toolset.test.js`
- Modify: `tools/boss-cli/test/login_mode.test.js`

- [ ] **Step 1: Write failing lifecycle tests**

Inject controller and navigation dependencies into `runBrowserCommand(command, options)` and assert:

```js
function fakeDeps({
  calls = [],
  initialState = 'stopped',
  initialMode = 'headful',
  entryFailure,
} = {}) {
  const deps = {
    stopCalls: 0,
    getStatus: async () => initialState === 'running'
      ? { state: 'running', runtime: { mode: initialMode } }
      : { state: initialState },
    start: async (mode) => {
      calls.push(`start:${mode}`);
      return { action: 'started', runtime: { mode } };
    },
    restart: async (mode) => {
      calls.push(`restart:${mode}`);
      return { action: 'started', runtime: { mode } };
    },
    openEntry: async ({ mode, destination }) => {
      calls.push(`open:${mode}:${destination}`);
      if (entryFailure) throw entryFailure;
      return { kind: destination === 'chat' ? 'ready' : 'login_required' };
    },
    stop: async () => {
      deps.stopCalls += 1;
    },
  };
  return deps;
}

test('headful start opens and focuses the Boss login entry', async () => {
  const calls = [];
  await runBrowserCommand({ action: 'start', mode: 'headful' }, {
    deps: fakeDeps({ calls, initialState: 'stopped' }),
  });
  assert.deepEqual(calls, ['start:headful', 'open:headful:login']);
});

test('headless restart requires a running managed browser and validates chat', async () => {
  const calls = [];
  await runBrowserCommand({ action: 'restart', mode: 'headless' }, {
    deps: fakeDeps({ calls, initialState: 'running', initialMode: 'headful' }),
  });
  assert.deepEqual(calls, ['restart:headless', 'open:headless:chat']);
});

test('failed headless validation leaves the managed browser running', async () => {
  const deps = fakeDeps({ entryFailure: new Error('risk_blocked code=32') });
  await assert.rejects(
    runBrowserCommand({ action: 'restart', mode: 'headless' }, { deps }),
    /risk_blocked.*code=32/,
  );
  assert.equal(deps.stopCalls, 0);
});
```

- [ ] **Step 2: Run tests and verify RED**

Run: `node --test test/browser_toolset.test.js test/login_mode.test.js`

Expected: FAIL because lifecycle commands do not navigate and `runBrowserCommand` has no injected dependency boundary.

- [ ] **Step 3: Implement navigation**

Add `openBossEntryPage(browser, { mode, destination })`:

```js
const target = destination === 'login' ? BOSS_LOGIN_ENTRY_URL : BOSS_CHAT_ENTRY_URL;
await page.goto(target, { waitUntil: 'load', timeout: 60_000 });
if (mode === 'headful') await page.bringToFront();
if (destination === 'chat') {
  await page.waitForSelector('.menu-list', { timeout: 30_000 }).catch(() => {});
}
const state = classifyBossEntrySnapshot({
  url: page.url(),
  title: await page.title(),
  hasMenu: await page.$('.menu-list').then(Boolean),
});
if (destination === 'chat' && state.kind !== 'ready') {
  throw new Error(formatBossEntryFailure(state));
}
return state;
```

The caller disconnects its CDP handle after navigation and never closes the managed Chrome process.

- [ ] **Step 4: Implement lifecycle orchestration under one lock**

`start/restart --headful` must open the login destination before reporting success. `restart --headless` must require a pre-existing managed browser, restart with the same profile, open the chat destination, and validate `ready`. Entry failure returns nonzero and deliberately does not call `stopBrowserUnlocked`.

Refactor `runLogin` to reuse `openBossEntryPage(..., { mode: 'headful', destination: 'login' })` while retaining explicit user control and no login polling.

- [ ] **Step 5: Verify GREEN**

Run: `node --test test/boss_entry.test.js test/browser_toolset.test.js test/login_mode.test.js`

Expected: all lifecycle navigation tests pass without launching production Chrome.

### Task 3: Reject Cold Headless Launches

**Files:**
- Modify: `tools/boss-cli/dist/browser/cdp_browser.js`
- Modify: `tools/boss-cli/dist/browser/cdp_browser.d.ts`
- Modify: `tools/boss-cli/dist/toolset/browser.js`
- Modify: `tools/boss-cli/dist/cli/cliRouter.js`
- Modify: `tools/boss-cli/test/browser_mode.test.js`
- Modify: `tools/boss-cli/test/browser_toolset.test.js`
- Modify: `tools/boss-cli/README.md`
- Modify: `tools/boss-cli/LOCAL_USAGE.md`

- [ ] **Step 1: Write failing cold-start tests**

```js
test('normal commands reject an explicit headless cold start', () => {
  assert.throws(
    () => assertManagedLaunchAllowed({ state: 'stopped' }, 'headless'),
    /boss login.*已登录.*restart --headless/i,
  );
});

test('browser start --headless rejects stopped state', async () => {
  await assert.rejects(
    runBrowserCommand({ action: 'start', mode: 'headless' }, {
      deps: fakeDeps({ initialState: 'stopped' }),
    }),
    /先.*boss login/i,
  );
});
```

- [ ] **Step 2: Run tests and verify RED**

Run: `node --test test/browser_mode.test.js test/browser_toolset.test.js`

Expected: FAIL because stopped state currently launches headless Chrome.

- [ ] **Step 3: Add the cold-start guard**

Export and call:

```js
export function assertManagedLaunchAllowed(status, requestedMode) {
  const stopped = status.state === 'stopped' ||
    (status.state === 'stale' && status.effectiveState === 'stopped');
  if (requestedMode === 'headless' && stopped) {
    throw new Error('不能直接冷启动无头 Boss 浏览器。请先运行 boss login，完成登录后由用户确认，再运行 boss browser restart --headless。');
  }
}
```

The explicit lifecycle restart path remains authorized because it verifies a running managed browser before stop/start. Normal commands with no browser may still start headful Chrome.

- [ ] **Step 4: Update help and usage docs**

Document exactly:

```text
boss login
# 用户完成登录并明确确认
boss browser restart --headless
boss browser status
```

Remove examples that cold-start `browser start --headless` from a stopped state.

- [ ] **Step 5: Verify GREEN**

Run: `node --test test/browser_mode.test.js test/browser_toolset.test.js`

Expected: cold headless launches fail with the visible-login instructions; headful start and confirmed restart remain green.

### Task 4: Surface Risk Pages and Complete Verification

**Files:**
- Modify: `tools/boss-cli/dist/common/boss_page_guards.js`
- Modify: `tools/boss-cli/dist/common/boss_session_page.js`
- Create: `tools/boss-cli/test/boss_session_diagnostics.test.js`
- Modify: `tools/boss-cli/README.md`
- Modify: `tools/boss-cli/LOCAL_USAGE.md`

- [ ] **Step 1: Write failing diagnostic tests**

Export a small readiness diagnostic helper and assert that a Boss 403 URL is reported immediately rather than converted to `.menu-list` timeout:

```js
test('reports Boss 403 directly', () => {
  const error = createBossReadinessError({
    url: 'https://www.zhipin.com/web/passport/zp/403.html?code=32',
    title: 'www.zhipin.com',
    hasMenu: false,
  });
  assert.match(error.message, /risk_blocked.*code=32/);
  assert.doesNotMatch(error.message, /cookie|html/i);
});
```

- [ ] **Step 2: Run test and verify RED**

Run: `node --test test/boss_session_diagnostics.test.js`

Expected: FAIL because readiness errors currently collapse into a generic 30-second selector timeout.

- [ ] **Step 3: Stop hiding risk navigation**

Remove risk/verification URLs from the request-blocking and automatic navigation-recovery paths in `boss_page_guards.js`. Keep unrelated page instrumentation unchanged. In `ensureMenuListMountedAfterLoad`, classify the current URL before waiting and again on timeout; throw `formatBossEntryFailure(state)` for non-ready terminal states.

Do not add retries, alternate URLs, security-script workarounds, or CAPTCHA handling.

- [ ] **Step 4: Run focused and full verification**

Run:

```bash
node --test test/boss_entry.test.js test/browser_toolset.test.js test/browser_mode.test.js test/login_mode.test.js test/boss_session_diagnostics.test.js
npm test
node --check dist/browser/boss_entry.js
node --check dist/browser/cdp_browser.js
node --check dist/common/boss_page_guards.js
node --check dist/common/boss_session_page.js
node --check dist/toolset/browser.js
node --check dist/toolset/login.js
git diff --check
```

Expected: all tests and syntax checks pass; no command opens production Chrome.

- [ ] **Step 5: Commit and push**

```bash
git add tools/boss-cli/dist tools/boss-cli/test tools/boss-cli/README.md tools/boss-cli/LOCAL_USAGE.md docs/superpowers/plans/2026-07-13-boss-browser-login-handoff.md
git commit -m "Require visible login before headless Boss mode"
git push origin feature/boss-background-browser
```

- [ ] **Step 6: Run authorized manual validation**

With the production browser stopped, verify cold headless start fails without opening Chrome. Run `boss login`, wait for the user to confirm login, then run `boss browser restart --headless`. Verify it returns `ready` for `/web/chat/index`, then run read-only `boss list --unread`. Do not greet, send, accept resumes, or exchange WeChat during validation.
