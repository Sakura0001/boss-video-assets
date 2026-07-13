import assert from 'node:assert/strict';
import { mkdtemp, readFile, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {
    BROWSER_RUNTIME_SCHEMA_VERSION,
    inspectBrowserRuntime,
    parseBrowserRuntime,
    readBrowserRuntime,
    writeBrowserRuntime,
} from '../dist/browser/browser_runtime.js';

function runtime(overrides = {}) {
    return {
        schemaVersion: BROWSER_RUNTIME_SCHEMA_VERSION,
        pid: 12345,
        port: 54321,
        mode: 'headless',
        userDataDir: '/tmp/boss-browser-profile',
        startedAt: '2026-07-13T10:00:00.000Z',
        ...overrides,
    };
}

test('parses valid runtime metadata and rejects invalid fields', () => {
    assert.deepEqual(parseBrowserRuntime(runtime()), runtime());
    assert.throws(() => parseBrowserRuntime(runtime({ pid: 0 })), /pid/);
    assert.throws(() => parseBrowserRuntime(runtime({ mode: 'hidden' })), /mode/);
    assert.throws(() => parseBrowserRuntime(runtime({ userDataDir: 'relative' })), /userDataDir/);
    assert.throws(() => parseBrowserRuntime(runtime({ startedAt: 'yesterday' })), /startedAt/);
});

test('writes runtime metadata atomically with user-only permissions', async () => {
    const dir = await mkdtemp(path.join(tmpdir(), 'boss-runtime-'));
    const filePath = path.join(dir, 'nested', 'browser-runtime.json');
    const expected = runtime({ userDataDir: path.join(dir, 'profile') });

    await writeBrowserRuntime(expected, filePath);

    assert.deepEqual(await readBrowserRuntime(filePath), expected);
    assert.equal((await stat(filePath)).mode & 0o777, 0o600);
    assert.equal(JSON.parse(await readFile(filePath, 'utf8')).webSocketDebuggerUrl, undefined);
});

test('classifies absent metadata and endpoint as stopped', async () => {
    const result = await inspectBrowserRuntime(
        { filePath: '/tmp/missing-runtime.json', port: 54321, userDataDir: '/tmp/profile' },
        {
            readRuntime: async () => null,
            probeEndpoint: async () => undefined,
        },
    );

    assert.deepEqual(result, { state: 'stopped' });
});

test('classifies a live endpoint without metadata as unmanaged', async () => {
    const result = await inspectBrowserRuntime(
        { filePath: '/tmp/missing-runtime.json', port: 54321, userDataDir: '/tmp/profile' },
        {
            readRuntime: async () => null,
            probeEndpoint: async () => 'ws://127.0.0.1/devtools/browser/legacy',
        },
    );

    assert.equal(result.state, 'unmanaged');
    assert.equal(result.webSocketDebuggerUrl, 'ws://127.0.0.1/devtools/browser/legacy');
});

test('classifies matching live metadata as managed running', async () => {
    const expected = runtime();
    const result = await inspectBrowserRuntime(
        { filePath: '/tmp/runtime.json', port: expected.port, userDataDir: expected.userDataDir },
        {
            readRuntime: async () => expected,
            processExists: async () => true,
            probeEndpoint: async () => 'ws://127.0.0.1/devtools/browser/managed',
        },
    );

    assert.equal(result.state, 'running');
    assert.deepEqual(result.runtime, expected);
    assert.equal(result.webSocketDebuggerUrl, 'ws://127.0.0.1/devtools/browser/managed');
});

test('removes dead metadata and reports stale stopped state', async () => {
    const expected = runtime();
    let removed = false;
    const result = await inspectBrowserRuntime(
        { filePath: '/tmp/runtime.json', port: expected.port, userDataDir: expected.userDataDir },
        {
            readRuntime: async () => expected,
            processExists: async () => false,
            probeEndpoint: async () => undefined,
            removeRuntime: async () => {
                removed = true;
            },
        },
    );

    assert.equal(removed, true);
    assert.equal(result.state, 'stale');
    assert.equal(result.effectiveState, 'stopped');
    assert.match(result.reason, /process/);
});

test('invalid metadata never authorizes a live endpoint', async () => {
    let removed = false;
    const result = await inspectBrowserRuntime(
        { filePath: '/tmp/runtime.json', port: 54321, userDataDir: '/tmp/profile' },
        {
            readRuntime: async () => {
                throw new Error('Invalid browser runtime metadata: pid');
            },
            probeEndpoint: async () => 'ws://127.0.0.1/devtools/browser/unknown',
            removeRuntime: async () => {
                removed = true;
            },
        },
    );

    assert.equal(removed, true);
    assert.equal(result.state, 'stale');
    assert.equal(result.effectiveState, 'unmanaged');
});
