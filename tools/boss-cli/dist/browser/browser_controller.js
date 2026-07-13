import puppeteer from 'puppeteer-core';
import { BROWSER_RUNTIME_FILE, BROWSER_USER_DATA_DIR } from '../config.js';
import { withBossSessionLock } from '../common/boss_session_lock.js';
import { launchManagedBrowser, REMOTE_DEBUGGING_PORT } from './cdp_browser.js';
import { inspectBrowserRuntime, probeBrowserEndpoint, removeBrowserRuntime, } from './browser_runtime.js';

const STOP_TIMEOUT_MS = 5000;
const STOP_POLL_MS = 100;

function assertMode(mode) {
    if (mode !== 'headless' && mode !== 'headful') {
        throw new Error(`Unsupported browser mode: ${String(mode)}`);
    }
}

export function resolveBrowserRuntimeConfig(options = {}) {
    return options.config ?? {
        filePath: options.runtimeFile?.trim() || BROWSER_RUNTIME_FILE,
        port: options.port ?? REMOTE_DEBUGGING_PORT,
        userDataDir: options.userDataDir?.trim() ||
            process.env.BOSS_BROWSER_USER_DATA_DIR?.trim() ||
            BROWSER_USER_DATA_DIR,
    };
}

function effectiveState(status) {
    return status.state === 'stale' ? status.effectiveState : status.state;
}

async function defaultConnectForClose(webSocketDebuggerUrl) {
    return puppeteer.connect({ browserWSEndpoint: webSocketDebuggerUrl });
}

async function defaultWaitForEndpointToClose(port, timeoutMs = STOP_TIMEOUT_MS) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
        if (!(await probeBrowserEndpoint(port, Math.min(500, STOP_POLL_MS)))) {
            return true;
        }
        await new Promise((resolve) => setTimeout(resolve, STOP_POLL_MS));
    }
    return !(await probeBrowserEndpoint(port, Math.min(500, STOP_POLL_MS)));
}

function dependencies(options) {
    return {
        inspectRuntime: options.deps?.inspectRuntime ?? inspectBrowserRuntime,
        launchBrowser: options.deps?.launchBrowser ?? launchManagedBrowser,
        connectForClose: options.deps?.connectForClose ?? defaultConnectForClose,
        waitForEndpointToClose: options.deps?.waitForEndpointToClose ?? defaultWaitForEndpointToClose,
        removeRuntime: options.deps?.removeRuntime ?? removeBrowserRuntime,
    };
}

export async function getBrowserStatusUnlocked(options = {}) {
    const config = resolveBrowserRuntimeConfig(options);
    const deps = dependencies(options);
    return deps.inspectRuntime(config);
}

export async function startBrowserUnlocked(mode, options = {}) {
    assertMode(mode);
    const config = resolveBrowserRuntimeConfig(options);
    const deps = dependencies(options);
    const status = await deps.inspectRuntime(config);
    const state = effectiveState(status);
    if (state === 'running') {
        if (status.runtime.mode === mode) {
            return { action: 'already-running', runtime: status.runtime };
        }
        throw new Error(`Boss browser is running in ${status.runtime.mode} mode. Run boss browser restart --${mode}.`);
    }
    if (state === 'unmanaged') {
        throw new Error('Boss browser endpoint is unmanaged. Close the legacy Boss browser once before using lifecycle commands.');
    }
    const launched = await deps.launchBrowser({
        headless: mode === 'headless',
        userDataDir: config.userDataDir,
        remoteDebuggingPort: config.port,
        runtimeFile: config.filePath,
    });
    await Promise.resolve(launched.browser.disconnect());
    return { action: 'started', runtime: launched.runtime };
}

export async function stopBrowserUnlocked(options = {}) {
    const config = resolveBrowserRuntimeConfig(options);
    const deps = dependencies(options);
    const status = await deps.inspectRuntime(config);
    const state = effectiveState(status);
    if (state === 'stopped') {
        return { action: 'already-stopped' };
    }
    if (state === 'unmanaged') {
        throw new Error('Boss browser endpoint is unmanaged. Refusing to close an unverified Chrome process.');
    }
    const browser = await deps.connectForClose(status.webSocketDebuggerUrl);
    await browser.close();
    if (!(await deps.waitForEndpointToClose(config.port, STOP_TIMEOUT_MS))) {
        throw new Error('Managed Boss browser did not stop before timeout; runtime metadata was preserved.');
    }
    await deps.removeRuntime(config.filePath);
    return { action: 'stopped', runtime: status.runtime };
}

export async function restartBrowserUnlocked(mode, options = {}) {
    assertMode(mode);
    await stopBrowserUnlocked(options);
    return startBrowserUnlocked(mode, options);
}

export async function getBrowserStatus(options = {}) {
    return withBossSessionLock(() => getBrowserStatusUnlocked(options));
}

export async function startBrowser(mode, options = {}) {
    return withBossSessionLock(() => startBrowserUnlocked(mode, options));
}

export async function stopBrowser(options = {}) {
    return withBossSessionLock(() => stopBrowserUnlocked(options));
}

export async function restartBrowser(mode, options = {}) {
    return withBossSessionLock(() => restartBrowserUnlocked(mode, options));
}
