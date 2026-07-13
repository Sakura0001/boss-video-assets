import assert from 'node:assert/strict';
import test from 'node:test';

import {
    restartBrowserUnlocked,
    startBrowserUnlocked,
    stopBrowserUnlocked,
} from '../dist/browser/browser_controller.js';

const config = {
    filePath: '/tmp/browser-runtime.json',
    port: 54321,
    userDataDir: '/tmp/boss-profile',
};

const managedRuntime = {
    schemaVersion: 1,
    pid: 24680,
    port: config.port,
    mode: 'headless',
    userDataDir: config.userDataDir,
    startedAt: '2026-07-13T10:00:00.000Z',
};

function running(mode = 'headless') {
    return {
        state: 'running',
        runtime: { ...managedRuntime, mode },
        webSocketDebuggerUrl: 'ws://127.0.0.1/devtools/browser/managed',
    };
}

test('same-mode start is idempotent', async () => {
    let launches = 0;
    const result = await startBrowserUnlocked('headless', {
        config,
        deps: {
            inspectRuntime: async () => running('headless'),
            launchBrowser: async () => {
                launches += 1;
            },
        },
    });

    assert.equal(result.action, 'already-running');
    assert.equal(result.runtime.mode, 'headless');
    assert.equal(launches, 0);
});

test('different-mode start requires explicit restart', async () => {
    await assert.rejects(
        startBrowserUnlocked('headful', {
            config,
            deps: { inspectRuntime: async () => running('headless') },
        }),
        /browser restart --headful/,
    );
});

test('start refuses an unmanaged endpoint', async () => {
    await assert.rejects(
        startBrowserUnlocked('headless', {
            config,
            deps: {
                inspectRuntime: async () => ({
                    state: 'unmanaged',
                    webSocketDebuggerUrl: 'ws://127.0.0.1/devtools/browser/legacy',
                }),
            },
        }),
        /unmanaged|未受管/i,
    );
});

test('stopped start launches once and disconnects the controller handle', async () => {
    let launches = 0;
    let disconnects = 0;
    const launchedRuntime = { ...managedRuntime, mode: 'headful' };
    const result = await startBrowserUnlocked('headful', {
        config,
        deps: {
            inspectRuntime: async () => ({ state: 'stopped' }),
            launchBrowser: async (options) => {
                launches += 1;
                assert.equal(options.headless, false);
                assert.equal(options.userDataDir, config.userDataDir);
                return {
                    browser: {
                        disconnect() {
                            disconnects += 1;
                        },
                    },
                    runtime: launchedRuntime,
                };
            },
        },
    });

    assert.equal(result.action, 'started');
    assert.deepEqual(result.runtime, launchedRuntime);
    assert.equal(launches, 1);
    assert.equal(disconnects, 1);
});

test('stop refuses an unmanaged endpoint without connecting', async () => {
    let connects = 0;
    await assert.rejects(
        stopBrowserUnlocked({
            config,
            deps: {
                inspectRuntime: async () => ({
                    state: 'unmanaged',
                    webSocketDebuggerUrl: 'ws://127.0.0.1/devtools/browser/legacy',
                }),
                connectForClose: async () => {
                    connects += 1;
                },
            },
        }),
        /unmanaged|未受管/i,
    );
    assert.equal(connects, 0);
});

test('managed stop closes through CDP and removes metadata after endpoint disappears', async () => {
    let closes = 0;
    let removals = 0;
    const result = await stopBrowserUnlocked({
        config,
        deps: {
            inspectRuntime: async () => running(),
            connectForClose: async (endpoint) => {
                assert.match(endpoint, /^ws:/);
                return {
                    async close() {
                        closes += 1;
                    },
                };
            },
            waitForEndpointToClose: async (port) => {
                assert.equal(port, config.port);
                return true;
            },
            removeRuntime: async (filePath) => {
                assert.equal(filePath, config.filePath);
                removals += 1;
            },
        },
    });

    assert.equal(result.action, 'stopped');
    assert.equal(closes, 1);
    assert.equal(removals, 1);
});

test('failed stop preserves metadata and prevents restart launch', async () => {
    let launches = 0;
    let removals = 0;
    const deps = {
        inspectRuntime: async () => running(),
        connectForClose: async () => ({ close: async () => { } }),
        waitForEndpointToClose: async () => false,
        removeRuntime: async () => {
            removals += 1;
        },
        launchBrowser: async () => {
            launches += 1;
        },
    };

    await assert.rejects(restartBrowserUnlocked('headful', { config, deps }), /did not stop|未停止/i);
    assert.equal(removals, 0);
    assert.equal(launches, 0);
});
