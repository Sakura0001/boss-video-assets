import assert from 'node:assert/strict';
import test from 'node:test';

import { parseBrowserCommand } from '../dist/cli/cliRouter.js';

test('parses browser status and stop without mode', () => {
    assert.deepEqual(parseBrowserCommand(['status']), { action: 'status' });
    assert.deepEqual(parseBrowserCommand(['stop']), { action: 'stop' });
});

test('parses explicit start and restart modes', () => {
    assert.deepEqual(parseBrowserCommand(['start', '--headless']), {
        action: 'start',
        mode: 'headless',
    });
    assert.deepEqual(parseBrowserCommand(['restart', '--headful']), {
        action: 'restart',
        mode: 'headful',
    });
});

test('allows start and restart to use the environment default mode', () => {
    assert.deepEqual(parseBrowserCommand(['start']), { action: 'start' });
    assert.deepEqual(parseBrowserCommand(['restart']), { action: 'restart' });
});

test('rejects conflicting mode flags before browser access', () => {
    assert.throws(
        () => parseBrowserCommand(['start', '--headless', '--headful']),
        /headless.*headful|conflicting|冲突/i,
    );
});

test('rejects modes on status and stop', () => {
    assert.throws(() => parseBrowserCommand(['status', '--headless']), /用法|usage/i);
    assert.throws(() => parseBrowserCommand(['stop', '--headful']), /用法|usage/i);
});

test('rejects unknown actions, options, and extra arguments', () => {
    assert.throws(() => parseBrowserCommand(['launch']), /用法|usage/i);
    assert.throws(() => parseBrowserCommand(['start', '--fast']), /用法|usage/i);
    assert.throws(() => parseBrowserCommand(['stop', 'now']), /用法|usage/i);
});
