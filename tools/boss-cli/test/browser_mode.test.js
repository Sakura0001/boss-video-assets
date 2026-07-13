import assert from 'node:assert/strict';
import test from 'node:test';

import { detachSpawnedBrowserProcess, resolveRequestedBrowserMode } from '../dist/browser/cdp_browser.js';
import { configureHeadlessForCommand } from '../dist/cli/cliRouter.js';

test('an unset mode does not override an already managed browser', () => {
    assert.equal(resolveRequestedBrowserMode({}, {}), undefined);
});

test('an explicit environment mode is normalized', () => {
    assert.equal(resolveRequestedBrowserMode({}, { BOSS_BROWSER_HEADLESS: 'true' }), 'headless');
    assert.equal(resolveRequestedBrowserMode({}, { BOSS_BROWSER_HEADLESS: '1' }), 'headless');
    assert.equal(resolveRequestedBrowserMode({}, { BOSS_BROWSER_HEADLESS: 'false' }), 'headful');
});

test('an explicit API option takes precedence over the environment', () => {
    assert.equal(
        resolveRequestedBrowserMode({ headless: false }, { BOSS_BROWSER_HEADLESS: 'true' }),
        'headful',
    );
});

test('normal command setup preserves an unset browser mode', () => {
    const env = {};
    configureHeadlessForCommand('list', env);
    assert.equal(Object.hasOwn(env, 'BOSS_BROWSER_HEADLESS'), false);
});

test('login command setup explicitly requests headful mode', () => {
    const env = {};
    configureHeadlessForCommand('login', env);
    assert.equal(env.BOSS_BROWSER_HEADLESS, 'false');
});

test('detaching a spawned browser unreferences the process and both output streams', () => {
    const calls = [];
    const stream = (name) => ({
        resume() {
            calls.push(`${name}:resume`);
        },
        unref() {
            calls.push(`${name}:unref`);
        },
    });
    detachSpawnedBrowserProcess({
        stdout: stream('stdout'),
        stderr: stream('stderr'),
        unref() {
            calls.push('process:unref');
        },
    });
    assert.deepEqual(calls, [
        'stdout:resume',
        'stdout:unref',
        'stderr:resume',
        'stderr:unref',
        'process:unref',
    ]);
});
