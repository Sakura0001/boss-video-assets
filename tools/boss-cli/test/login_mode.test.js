import assert from 'node:assert/strict';
import test from 'node:test';

import { ensureHeadfulBrowserForLogin } from '../dist/toolset/login.js';

const runtime = {
    schemaVersion: 1,
    pid: 12345,
    port: 54321,
    mode: 'headless',
    userDataDir: '/tmp/boss-profile',
    startedAt: '2026-07-13T10:00:00.000Z',
};

test('login restarts a managed headless browser as headful', async () => {
    const actions = [];
    const result = await ensureHeadfulBrowserForLogin({
        deps: {
            getStatus: async () => ({
                state: 'running',
                runtime,
                webSocketDebuggerUrl: 'ws://127.0.0.1/devtools/browser/managed',
            }),
            restart: async (mode) => {
                actions.push(`restart:${mode}`);
                return { action: 'started', runtime: { ...runtime, mode } };
            },
        },
    });

    assert.deepEqual(actions, ['restart:headful']);
    assert.equal(result.runtime.mode, 'headful');
});

test('login reuses a managed headful browser', async () => {
    let starts = 0;
    const headful = { ...runtime, mode: 'headful' };
    const result = await ensureHeadfulBrowserForLogin({
        deps: {
            getStatus: async () => ({
                state: 'running',
                runtime: headful,
                webSocketDebuggerUrl: 'ws://127.0.0.1/devtools/browser/managed',
            }),
            start: async () => {
                starts += 1;
            },
        },
    });

    assert.equal(result.action, 'already-headful');
    assert.deepEqual(result.runtime, headful);
    assert.equal(starts, 0);
});

test('login starts a headful browser when stopped', async () => {
    const modes = [];
    await ensureHeadfulBrowserForLogin({
        deps: {
            getStatus: async () => ({ state: 'stopped' }),
            start: async (mode) => {
                modes.push(mode);
                return { action: 'started', runtime: { ...runtime, mode } };
            },
        },
    });
    assert.deepEqual(modes, ['headful']);
});

test('login refuses to close or adopt an unmanaged endpoint', async () => {
    let restarts = 0;
    await assert.rejects(
        ensureHeadfulBrowserForLogin({
            deps: {
                getStatus: async () => ({
                    state: 'unmanaged',
                    webSocketDebuggerUrl: 'ws://127.0.0.1/devtools/browser/legacy',
                }),
                restart: async () => {
                    restarts += 1;
                },
            },
        }),
        /unmanaged|未受管/i,
    );
    assert.equal(restarts, 0);
});
