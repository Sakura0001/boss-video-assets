import { randomUUID } from 'node:crypto';
import { chmod, mkdir, readFile, rename, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { BROWSER_RUNTIME_FILE } from '../config.js';

export const BROWSER_RUNTIME_SCHEMA_VERSION = 1;

function invalid(field) {
    throw new Error(`Invalid browser runtime metadata: ${field}`);
}

export function parseBrowserRuntime(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
        invalid('root');
    }
    const runtime = value;
    if (runtime.schemaVersion !== BROWSER_RUNTIME_SCHEMA_VERSION) {
        invalid('schemaVersion');
    }
    if (!Number.isInteger(runtime.pid) || runtime.pid <= 0) {
        invalid('pid');
    }
    if (!Number.isInteger(runtime.port) || runtime.port <= 0 || runtime.port > 65535) {
        invalid('port');
    }
    if (runtime.mode !== 'headless' && runtime.mode !== 'headful') {
        invalid('mode');
    }
    if (typeof runtime.userDataDir !== 'string' || !path.isAbsolute(runtime.userDataDir)) {
        invalid('userDataDir');
    }
    if (typeof runtime.startedAt !== 'string' || Number.isNaN(Date.parse(runtime.startedAt))) {
        invalid('startedAt');
    }
    return {
        schemaVersion: BROWSER_RUNTIME_SCHEMA_VERSION,
        pid: runtime.pid,
        port: runtime.port,
        mode: runtime.mode,
        userDataDir: runtime.userDataDir,
        startedAt: runtime.startedAt,
    };
}

export async function readBrowserRuntime(filePath = BROWSER_RUNTIME_FILE) {
    let raw;
    try {
        raw = await readFile(filePath, 'utf8');
    }
    catch (error) {
        if (error && typeof error === 'object' && error.code === 'ENOENT') {
            return null;
        }
        throw error;
    }
    let value;
    try {
        value = JSON.parse(raw);
    }
    catch {
        invalid('json');
    }
    return parseBrowserRuntime(value);
}

export async function writeBrowserRuntime(runtime, filePath = BROWSER_RUNTIME_FILE) {
    const parsed = parseBrowserRuntime(runtime);
    const parent = path.dirname(filePath);
    await mkdir(parent, { recursive: true, mode: 0o700 });
    const tempPath = path.join(parent, `.${path.basename(filePath)}.${process.pid}.${randomUUID()}.tmp`);
    let renamed = false;
    try {
        await writeFile(tempPath, `${JSON.stringify(parsed, null, 2)}\n`, {
            encoding: 'utf8',
            flag: 'wx',
            mode: 0o600,
        });
        await chmod(tempPath, 0o600);
        await rename(tempPath, filePath);
        renamed = true;
        await chmod(filePath, 0o600);
    }
    finally {
        if (!renamed) {
            await rm(tempPath, { force: true }).catch(() => { });
        }
    }
    return parsed;
}

export async function removeBrowserRuntime(filePath = BROWSER_RUNTIME_FILE) {
    await rm(filePath, { force: true });
}

export async function processExists(pid) {
    if (!Number.isInteger(pid) || pid <= 0) {
        return false;
    }
    try {
        process.kill(pid, 0);
        return true;
    }
    catch (error) {
        return !!(error && typeof error === 'object' && error.code === 'EPERM');
    }
}

export async function probeBrowserEndpoint(port, timeoutMs = 800) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const response = await fetch(`http://127.0.0.1:${port}/json/version`, {
            signal: controller.signal,
        });
        if (!response.ok) {
            return undefined;
        }
        const payload = await response.json();
        return typeof payload.webSocketDebuggerUrl === 'string' && payload.webSocketDebuggerUrl.length > 0
            ? payload.webSocketDebuggerUrl
            : undefined;
    }
    catch {
        return undefined;
    }
    finally {
        clearTimeout(timer);
    }
}

async function staleResult(reason, webSocketDebuggerUrl, removeRuntime, filePath) {
    let cleanupError;
    try {
        await removeRuntime(filePath);
    }
    catch (error) {
        cleanupError = error instanceof Error ? error.message : String(error);
    }
    return {
        state: 'stale',
        effectiveState: webSocketDebuggerUrl ? 'unmanaged' : 'stopped',
        reason,
        ...(webSocketDebuggerUrl ? { webSocketDebuggerUrl } : {}),
        ...(cleanupError ? { cleanupError } : {}),
    };
}

export async function inspectBrowserRuntime(config, deps = {}) {
    const readRuntime = deps.readRuntime ?? readBrowserRuntime;
    const removeRuntime = deps.removeRuntime ?? removeBrowserRuntime;
    const pidExists = deps.processExists ?? processExists;
    const probeEndpoint = deps.probeEndpoint ?? probeBrowserEndpoint;
    let runtime;
    let readError;
    try {
        runtime = await readRuntime(config.filePath);
    }
    catch (error) {
        readError = error instanceof Error ? error.message : String(error);
        runtime = null;
    }
    const webSocketDebuggerUrl = await probeEndpoint(config.port);
    if (readError) {
        return staleResult(readError, webSocketDebuggerUrl, removeRuntime, config.filePath);
    }
    if (!runtime) {
        return webSocketDebuggerUrl
            ? { state: 'unmanaged', webSocketDebuggerUrl }
            : { state: 'stopped' };
    }
    if (runtime.port !== config.port) {
        return staleResult('runtime port does not match configured port', webSocketDebuggerUrl, removeRuntime, config.filePath);
    }
    if (path.resolve(runtime.userDataDir) !== path.resolve(config.userDataDir)) {
        return staleResult('runtime userDataDir does not match configured userDataDir', webSocketDebuggerUrl, removeRuntime, config.filePath);
    }
    if (!(await pidExists(runtime.pid))) {
        return staleResult('runtime process is not alive', webSocketDebuggerUrl, removeRuntime, config.filePath);
    }
    if (!webSocketDebuggerUrl) {
        return staleResult('runtime endpoint is not reachable', undefined, removeRuntime, config.filePath);
    }
    return {
        state: 'running',
        runtime,
        webSocketDebuggerUrl,
    };
}
