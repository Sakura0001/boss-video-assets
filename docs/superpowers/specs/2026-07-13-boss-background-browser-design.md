# Boss CLI Background Browser Design

## Goal

Allow `boss-cli` to run normal recruiting commands in a managed headless Chrome process without stealing keyboard or window focus, while preserving the existing visible login flow and browser profile.

This phase does not add a scheduler, daemon, unattended Codex runtime, or any change to the installed `boss-zhaopin` skill.

## Current State

- `boss-cli` already launches Chrome with a dedicated user data directory at `~/.boss-cli/.cache/browser-data` and a stable CDP port, defaulting to `53470`.
- `BOSS_BROWSER_HEADLESS=true` requests headless mode when a new Chrome process is spawned.
- A process already listening on the configured CDP port is reused without checking whether its mode matches the requested mode.
- Every normal Boss command calls `page.bringToFront()`, so a visible browser steals focus.
- Browser process mode is remembered only in the Node process that launched Chrome. A later CLI invocation cannot reliably determine whether the reused browser is headless.
- The repository contains compiled JavaScript and declarations under `dist/`, but no TypeScript sources or `tsconfig.json`; `npm run build` currently exits successfully without compiling files.

## Chosen Approach

Implement one managed Boss browser instance with persistent runtime metadata and explicit lifecycle commands.

New commands:

```text
boss browser status
boss browser start --headless
boss browser start --headful
boss browser stop
boss browser restart --headless
boss browser restart --headful
```

`headful` is the user-facing name for a visible browser. Existing `BOSS_BROWSER_HEADLESS` behavior remains compatible for ordinary commands.

## Runtime Metadata

Store browser metadata at:

```text
~/.boss-cli/.cache/browser-runtime.json
```

`BOSS_BROWSER_RUNTIME_FILE` may override this path for isolated testing or advanced multi-instance setups. The normal default remains fixed under `~/.boss-cli/.cache/`.

The file contains only local process data:

```json
{
  "schemaVersion": 1,
  "pid": 12345,
  "port": 53470,
  "mode": "headless",
  "userDataDir": "/Users/example/.boss-cli/.cache/browser-data",
  "startedAt": "2026-07-13T10:00:00.000Z"
}
```

Write the file atomically with user-only permissions. It must never contain cookies, credentials, candidate data, messages, or CDP WebSocket URLs.

Metadata is authoritative only when all of these conditions hold:

1. The schema and fields are valid.
2. The recorded PID is alive.
3. The recorded localhost CDP port responds.
4. The configured port and user data directory match the metadata.

Stale metadata is removed automatically. A live endpoint without valid matching metadata is classified as `unmanaged`.

## Lifecycle Semantics

### Status

`boss browser status` reports one of:

- `stopped`: no live endpoint and no valid metadata.
- `running`: a managed instance is alive, including PID, mode, port, user data directory, and start time.
- `unmanaged`: a live endpoint exists but cannot be proven to belong to the current boss-cli configuration.
- `stale`: metadata existed but failed validation and was cleaned up; the final status response explains the cleanup.

Status never starts Chrome and never navigates a page.

### Start

`start` defaults to the existing `BOSS_BROWSER_HEADLESS` value and accepts exactly one explicit mode flag.

- If stopped, spawn Chrome in the requested mode and persist metadata after CDP is reachable.
- If the same managed mode is already running, return success without restarting it.
- If the opposite managed mode is running, return an actionable error directing the caller to `restart`.
- If the endpoint is unmanaged, refuse to adopt or close it and tell the user to close the legacy Boss browser once.
- After a successful `headful` start, open and focus the Boss login entry page before reporting success. This also applies when the same managed headful browser is already running, so an empty or unrelated tab is repaired by rerunning `start --headful`.
- A stopped browser cannot be cold-started directly in headless mode. The command must direct the caller to the visible login flow first; normal recruiting commands must follow the same restriction instead of implicitly spawning headless Chrome.
- A failed headful navigation is a command failure. Do not report that the browser is ready while it remains on `chrome://newtab/`.

### Stop

`stop` closes only a managed instance whose PID, port, and user data directory match valid metadata. It first requests a graceful browser shutdown through CDP, waits for the endpoint to disappear, then removes metadata. It never sends a signal to an unverified PID and never closes an unmanaged endpoint.

If graceful shutdown times out, report the failure and preserve enough metadata for diagnosis; do not escalate to `SIGKILL` automatically.

### Restart

`restart` is `stop` followed by `start` under the existing Boss session lock. It supports explicit `--headless` or `--headful` and fails without starting a second browser if stop did not complete.

After `restart --headful` launches the replacement browser, it follows the same Boss entry-page navigation contract as `start --headful`.

`restart --headless` is the explicit handoff after the user confirms visible login. It is accepted only when a managed browser is already running, starts headless Chrome with the same user data directory, opens `/web/chat/index`, and validates the authenticated chat shell before reporting success. A login page, risk page, unexpected URL, or missing chat shell returns a nonzero result while leaving the managed browser running for diagnosis.

## Normal Command Behavior

Normal commands continue to use the configured CDP port and persistent user data directory.

- If no browser exists, a normal command may launch headful Chrome, but an explicit headless request fails with instructions to complete the visible login flow first.
- A newly launched headful process writes managed metadata and opens the Boss login entry page.
- If `BOSS_BROWSER_HEADLESS` or an API option explicitly requests a mode and a managed browser is running in the other mode, fail with an instruction to run `boss browser restart` instead of silently reusing it.
- If no mode is explicitly requested, reuse the current managed mode. This lets a validated `boss browser restart --headless` handoff be followed by ordinary `boss` commands without exporting an environment variable.
- If a legacy unmanaged endpoint exists, preserve compatibility by allowing ordinary commands to connect, but lifecycle commands must not stop it. This avoids breaking current users while keeping destructive operations ownership-safe.
- Ordinary commands do not call `page.bringToFront()` by default.
- `BOSS_BROWSER_FOREGROUND=true` restores focus activation for debugging.
- `boss login` remains visible and may call `bringToFront()`.
- After Chrome is ready, the launcher unreferences the child process and both output streams so one-shot CLI commands return immediately while Chrome remains alive.

## Login Flow

Login always requires a visible browser.

1. If a managed headless browser is active, `boss login` performs a managed restart into headful mode.
2. It opens and focuses the Boss login page, then returns as it does today so the user can complete login.
3. Browser data remains in the same user data directory, preserving the authenticated profile.
4. The user explicitly confirms that login or verification is complete; the CLI does not poll or infer that confirmation.
5. The caller then runs `boss browser restart --headless` to perform the validated background handoff.

The headful lifecycle commands and `boss login` share one entry-page navigation helper. This avoids two commands drifting into different visible startup behavior while keeping lifecycle ownership and login-mode transitions separate.

An unmanaged endpoint is never automatically closed by `boss login`; the command returns an actionable migration message instead.

## Concurrency

Reuse the existing `withBossSessionLock` mechanism for all lifecycle state changes. Browser start, stop, restart, login mode changes, and normal page operations must not mutate the same instance concurrently.

Lifecycle internals must expose an unlocked implementation so `restart` can perform stop and start while holding one outer lock without deadlocking.

## Error Handling

- Invalid or conflicting flags produce usage errors without touching browser state.
- Corrupt metadata is quarantined or removed and reported as stale; it never authorizes process termination.
- Port conflicts are reported as unmanaged endpoints.
- A mode mismatch never silently restarts a browser during a normal recruiting command.
- Login expiry, captcha, and Boss risk-control behavior remain handled by existing command errors and the recruiting skill. This branch does not automate bypasses.
- Explicit lifecycle commands return nonzero on failed state transitions.
- Boss 403, verification, security-check, and login URLs are terminal diagnostic states during startup and command readiness checks. Do not automatically retry, redirect away from, or hide them behind a generic selector timeout.
- Readiness failures include the final URL, page title, and recognized Boss error code when available, without logging cookies, tokens, or page contents.

## Code Organization

- `dist/browser/browser_runtime.js`: metadata validation, atomic persistence, endpoint/PID health checks, and pure lifecycle decision helpers.
- `dist/browser/browser_controller.js`: start, stop, restart, and status orchestration.
- `dist/browser/boss_entry.js`: visible entry navigation, headless chat-shell validation, and safe page-state classification.
- `dist/browser/cdp_browser.js`: delegates launch and reuse checks to the runtime/controller contract and records newly spawned processes.
- `dist/common/boss_session_page.js`: removes unconditional focus activation and honors `BOSS_BROWSER_FOREGROUND`.
- `dist/toolset/browser.js`: CLI-facing browser lifecycle operations.
- `dist/toolset/login.js`: managed headless-to-headful transition.
- `dist/cli/cliRouter.js`: parses and documents the new command family.
- Matching `.d.ts` files document public exports. Existing source maps are not regenerated because source TypeScript is absent.

## Testing

Add Node's built-in test runner and avoid real Boss actions in automated tests.

Unit tests cover:

- metadata validation and private atomic writes;
- stale, stopped, running, and unmanaged status classification;
- same-mode start idempotency;
- mode mismatch requiring explicit restart;
- refusal to stop an unmanaged endpoint;
- graceful managed stop behavior;
- CLI mode flag parsing;
- normal commands not requesting foreground focus;
- login remaining foreground-only.
- headful start and restart opening the Boss entry page before reporting success;
- same-mode headful start repairing a blank tab;
- stopped headless start and implicit normal-command cold launch being rejected;
- user-confirmed headful-to-headless restart opening and validating the Boss chat shell;
- headful navigation failures propagating as command failures.
- login, 403, verification, unexpected URL, and missing-shell diagnostics preserving the running browser for inspection.

An integration-style test uses a temporary directory, random localhost port, and injected fake process/CDP adapters. Automated tests must not open Boss, use the production profile, send messages, or terminate the production browser.

Manual validation is performed only after automated verification:

1. Use an isolated test port and profile to verify headful start/status/stop/restart and rejection of cold headless start.
2. Verify headful start opens the Boss entry page and a visible test window does not steal focus during a non-login command.
3. With user authorization, complete visible login, explicitly confirm it, then restart headless using the same profile.
4. Confirm the headless restart validates `/web/chat/index`, then run `boss list --unread` and perform no state-changing action.
5. Confirm login, 403, verification, and missing-shell states fail with actionable diagnostics and no retry.

## Branch and Deployment Boundary

Implementation lives only on `feature/boss-background-browser` until user validation succeeds.

Before approval, do not:

- merge into `main`;
- overwrite `/opt/homebrew/bin/boss` or its installed package;
- modify `/Users/yuyu/.codex/skills/boss-zhaopin/`;
- send live candidate messages or perform state-changing Boss actions.

After user approval, merge separately, install the validated CLI build, then update the skill to start or require managed headless mode during automatic runs.
