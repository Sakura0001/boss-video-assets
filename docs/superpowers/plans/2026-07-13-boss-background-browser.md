# Boss CLI Background Browser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an ownership-safe managed headless Chrome lifecycle to boss-cli so normal commands run without stealing focus.

**Architecture:** A pure runtime module validates private process metadata and classifies the configured CDP endpoint. A controller serializes explicit start, stop, restart, and login mode transitions with the existing Boss session lock. Existing CDP connection code records managed launches and rejects silent managed mode mismatches, while ordinary page operations become background-safe by default.

**Tech Stack:** Node.js ESM, Puppeteer Core/CDP, Node built-in `node:test`, compiled JavaScript and `.d.ts` artifacts.

---

### Task 1: Runtime Metadata and Status Classification

**Files:**
- Create: `tools/boss-cli/dist/browser/browser_runtime.js`
- Create: `tools/boss-cli/dist/browser/browser_runtime.d.ts`
- Create: `tools/boss-cli/test/browser_runtime.test.js`
- Modify: `tools/boss-cli/dist/config.js`
- Modify: `tools/boss-cli/dist/config.d.ts`
- Modify: `tools/boss-cli/package.json`

- [x] **Step 1: Add failing runtime tests**

Test `parseBrowserRuntime`, atomic mode-`0600` persistence, stale cleanup, and `stopped`/`running`/`unmanaged` classification using temporary paths and injected PID/endpoint probes.

```js
test('classifies a matching live runtime as managed running', async () => {
  const result = await inspectBrowserRuntime(config, {
    readRuntime: async () => runtime,
    processExists: async () => true,
    probeEndpoint: async () => 'ws://127.0.0.1/devtools/browser/test',
  });
  assert.equal(result.state, 'running');
  assert.equal(result.runtime.mode, 'headless');
});
```

- [x] **Step 2: Verify RED**

Run: `node --test test/browser_runtime.test.js`

Expected: FAIL because `dist/browser/browser_runtime.js` does not exist.

- [x] **Step 3: Implement runtime metadata**

Export:

```js
export const BROWSER_RUNTIME_SCHEMA_VERSION = 1;
export function parseBrowserRuntime(value) {}
export async function readBrowserRuntime(filePath = BROWSER_RUNTIME_FILE) {}
export async function writeBrowserRuntime(runtime, filePath = BROWSER_RUNTIME_FILE) {}
export async function removeBrowserRuntime(filePath = BROWSER_RUNTIME_FILE) {}
export async function probeBrowserEndpoint(port, timeoutMs = 800) {}
export async function inspectBrowserRuntime(config, deps = {}) {}
```

Use `writeFile(temp, ..., { mode: 0o600 })`, `chmod(temp, 0o600)`, and `rename(temp, target)` for atomic private writes. Never persist the WebSocket endpoint.

- [x] **Step 4: Add package test command and declarations**

Set:

```json
"test": "node --test test/*.test.js"
```

Export `BROWSER_RUNTIME_FILE` from config as `process.env.BOSS_BROWSER_RUNTIME_FILE?.trim() || join(CACHE_DIR, 'browser-runtime.json')`. This override is used only for isolated tests and advanced multi-instance setups.

- [x] **Step 5: Verify GREEN**

Run: `npm test`

Expected: all runtime tests pass and no production browser is opened.

- [x] **Step 6: Commit**

```bash
git add tools/boss-cli/package.json tools/boss-cli/dist/config.js tools/boss-cli/dist/config.d.ts tools/boss-cli/dist/browser/browser_runtime.js tools/boss-cli/dist/browser/browser_runtime.d.ts tools/boss-cli/test/browser_runtime.test.js
git commit -m "Add managed browser runtime metadata"
```

### Task 2: Managed Browser Controller

**Files:**
- Create: `tools/boss-cli/dist/browser/browser_controller.js`
- Create: `tools/boss-cli/dist/browser/browser_controller.d.ts`
- Create: `tools/boss-cli/test/browser_controller.test.js`
- Modify: `tools/boss-cli/dist/browser/cdp_browser.js`
- Modify: `tools/boss-cli/dist/browser/cdp_browser.d.ts`
- Modify: `tools/boss-cli/dist/browser/index.js`
- Modify: `tools/boss-cli/dist/browser/index.d.ts`

- [x] **Step 1: Add failing controller tests**

Use injected launch/connect/wait adapters to verify:

```js
test('same-mode start is idempotent', async () => {});
test('different-mode start requires restart', async () => {});
test('stop refuses unmanaged endpoint', async () => {});
test('restart does not start when stop fails', async () => {});
test('managed stop closes through CDP and removes metadata', async () => {});
```

- [x] **Step 2: Verify RED**

Run: `node --test test/browser_controller.test.js`

Expected: FAIL because the controller module does not exist.

- [x] **Step 3: Refactor CDP launch boundary**

Keep `connectBrowser(options)` as the normal command entry point and add an internal/exported launch operation returning the connected browser and child PID. On every successful spawn, persist:

```js
{
  schemaVersion: 1,
  pid: proc.pid,
  port: REMOTE_DEBUGGING_PORT,
  mode: headless ? 'headless' : 'headful',
  userDataDir,
  startedAt: new Date().toISOString(),
}
```

When an existing managed browser has a different requested mode, throw an actionable `boss browser restart --headless|--headful` error. Continue allowing ordinary commands to connect to an unmanaged legacy endpoint.

- [x] **Step 4: Implement controller operations**

Export locked public operations and injectable unlocked operations:

```js
export async function getBrowserStatus(options = {}) {}
export async function startBrowser(mode, options = {}) {}
export async function stopBrowser(options = {}) {}
export async function restartBrowser(mode, options = {}) {}
export async function startBrowserUnlocked(mode, options = {}) {}
export async function stopBrowserUnlocked(options = {}) {}
```

Only `running` metadata authorizes CDP close. Wait for the endpoint to disappear before deleting metadata. Never automatically signal or kill a PID.

- [x] **Step 5: Export declarations and verify GREEN**

Run: `npm test`

Expected: runtime and controller tests pass.

- [x] **Step 6: Commit**

```bash
git add tools/boss-cli/dist/browser tools/boss-cli/test/browser_controller.test.js
git commit -m "Add managed browser lifecycle controller"
```

### Task 3: Background-Safe Page Focus and Login Transition

**Files:**
- Modify: `tools/boss-cli/dist/common/boss_session_page.js`
- Modify: `tools/boss-cli/dist/toolset/login.js`
- Modify: `tools/boss-cli/dist/toolset/login.d.ts`
- Create: `tools/boss-cli/test/browser_focus.test.js`
- Create: `tools/boss-cli/test/login_mode.test.js`

- [x] **Step 1: Add failing focus tests**

Extract and test:

```js
export function shouldBringBossPageToFront(env = process.env) {
  return env.BOSS_BROWSER_FOREGROUND === 'true' || env.BOSS_BROWSER_FOREGROUND === '1';
}
```

Assert default false and explicit true. Add an injected login-mode transition test proving managed headless becomes headful while unmanaged endpoints fail safely.

- [x] **Step 2: Verify RED**

Run: `node --test test/browser_focus.test.js test/login_mode.test.js`

Expected: FAIL because focus policy and login transition helpers do not exist.

- [x] **Step 3: Remove unconditional normal focus activation**

Call `page.bringToFront()` only when `shouldBringBossPageToFront()` is true. Keep login's explicit `bringToFront()`.

- [x] **Step 4: Make login lifecycle-aware**

Under one Boss session lock:

- inspect status;
- restart managed headless to headful;
- start headful if stopped;
- refuse unmanaged endpoint migration;
- open and focus the login page;
- detach without closing the visible browser.

Expose a small injected `ensureHeadfulBrowserForLogin` helper for tests without launching Chrome.

- [x] **Step 5: Verify GREEN**

Run: `npm test`

Expected: all tests pass without opening Chrome.

- [x] **Step 6: Commit**

```bash
git add tools/boss-cli/dist/common/boss_session_page.js tools/boss-cli/dist/toolset/login.js tools/boss-cli/dist/toolset/login.d.ts tools/boss-cli/test/browser_focus.test.js tools/boss-cli/test/login_mode.test.js
git commit -m "Keep normal browser operations in background"
```

### Task 4: Browser CLI Commands

**Files:**
- Create: `tools/boss-cli/dist/toolset/browser.js`
- Create: `tools/boss-cli/dist/toolset/browser.d.ts`
- Modify: `tools/boss-cli/dist/toolset/index.js`
- Modify: `tools/boss-cli/dist/toolset/index.d.ts`
- Modify: `tools/boss-cli/dist/cli/cliRouter.js`
- Modify: `tools/boss-cli/dist/cli/cliRouter.d.ts`
- Create: `tools/boss-cli/test/browser_cli.test.js`
- Modify: `tools/boss-cli/README.md`
- Modify: `tools/boss-cli/LOCAL_USAGE.md`

- [x] **Step 1: Add failing CLI parser tests**

Export a pure parser and test valid and invalid forms:

```js
parseBrowserCommand(['status']);
parseBrowserCommand(['start', '--headless']);
parseBrowserCommand(['restart', '--headful']);
parseBrowserCommand(['stop']);
```

Conflicting flags, unsupported options, and extra positional arguments must throw before controller invocation.

- [x] **Step 2: Verify RED**

Run: `node --test test/browser_cli.test.js`

Expected: FAIL because `parseBrowserCommand` is missing.

- [x] **Step 3: Implement CLI toolset and routing**

Add help entries and route `boss browser ...` through `implBrowserCommand`. Format concise status text with no WebSocket URL or sensitive browser data.

- [x] **Step 4: Document migration and usage**

Document:

```bash
boss browser status
boss browser start --headless
boss browser restart --headful
boss login
boss browser restart --headless
```

Explain that an old unowned process must be closed once before lifecycle management begins.

- [x] **Step 5: Verify GREEN and syntax**

Run:

```bash
npm test
node --check dist/browser/browser_runtime.js
node --check dist/browser/browser_controller.js
node --check dist/browser/cdp_browser.js
node --check dist/common/boss_session_page.js
node --check dist/toolset/login.js
node --check dist/toolset/browser.js
node --check dist/cli/cliRouter.js
node dist/cli/index.js help
```

Expected: tests pass, syntax checks pass, and help lists browser commands.

- [x] **Step 6: Commit**

```bash
git add tools/boss-cli/dist tools/boss-cli/test tools/boss-cli/README.md tools/boss-cli/LOCAL_USAGE.md
git commit -m "Expose background browser lifecycle commands"
```

### Task 5: Isolated Browser Smoke Test and Branch Verification

**Files:**
- Modify: `docs/superpowers/plans/2026-07-13-boss-background-browser.md`

- [x] **Step 1: Run full non-live verification**

Run:

```bash
cd tools/boss-cli
npm test
git diff --check
```

Expected: all tests pass and no whitespace errors.

- [x] **Step 2: Start a disposable managed headless browser**

Use a temporary user data directory and nonproduction port:

```bash
BOSS_BROWSER_REMOTE_DEBUGGING_PORT=53571 \
BOSS_BROWSER_USER_DATA_DIR=/tmp/boss-cli-background-smoke/profile \
BOSS_BROWSER_RUNTIME_FILE=/tmp/boss-cli-background-smoke/runtime.json \
node dist/cli/index.js browser start --headless
```

Do not navigate to Boss or run a recruiting command.

- [x] **Step 3: Verify lifecycle and cleanup**

Run `status`, idempotent `start --headless`, mode-mismatch `start --headful`, `restart --headful`, and `stop` against the same disposable configuration. Confirm the endpoint closes and no Chrome process remains on port `53571`.

- [x] **Step 4: Review scope and private data**

Confirm only the feature branch changed, no runtime metadata/profile files are tracked, no candidate data or credentials exist, and neither the installed CLI nor installed skill changed.

- [ ] **Step 5: Commit plan completion and push branch**

```bash
git add docs/superpowers/plans/2026-07-13-boss-background-browser.md
git commit -m "Complete background browser implementation plan"
git push origin feature/boss-background-browser
```

- [ ] **Step 6: Hand off user validation**

Provide the branch path, exact isolated validation commands, known one-time legacy-browser migration requirement, and state clearly that `main`, `/opt/homebrew/bin/boss`, and the installed skill remain unchanged.
