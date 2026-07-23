import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

import { validateMessageSequence } from '../dist/toolset/send.js';

test('accepts exactly three distinct non-empty knowledge-base messages', () => {
  assert.deepEqual(
    validateMessageSequence(['第一条', '第二条', '第三条']),
    ['第一条', '第二条', '第三条'],
  );
});

test('rejects incomplete, empty, or duplicate message sequences', () => {
  assert.throws(() => validateMessageSequence(['第一条', '第二条']), /恰好三条/);
  assert.throws(
    () => validateMessageSequence(['第一条', ' ', '第三条']),
    /不能为空/,
  );
  assert.throws(
    () => validateMessageSequence(['第一条', '第一条', '第三条']),
    /不能重复/,
  );
});

test('help documents the single-session message sequence command', () => {
  const result = spawnSync(process.execPath, ['dist/cli/index.js', 'help'], {
    cwd: new URL('..', import.meta.url),
    encoding: 'utf8',
  });
  assert.equal(result.status, 0);
  assert.match(
    result.stderr,
    /boss send-sequence <姓名> --job <岗位> --messages-json <JSON数组> --json/,
  );
});
