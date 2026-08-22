import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

import { validateMessageSequence } from '../dist/toolset/send.js';

test('accepts exactly two distinct non-empty knowledge-base messages', () => {
  assert.deepEqual(
    validateMessageSequence(['第一条', '第二条']),
    ['第一条', '第二条'],
  );
});

test('rejects incomplete, empty, duplicate, or oversized message sequences', () => {
  assert.throws(() => validateMessageSequence(['第一条']), /恰好两条/);
  assert.throws(
    () => validateMessageSequence(['第一条', ' ']),
    /不能为空/,
  );
  assert.throws(
    () => validateMessageSequence(['第一条', '第一条']),
    /不能重复/,
  );
  assert.throws(
    () => validateMessageSequence(['第一条', '第二条', '第三条']),
    /恰好两条/,
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
  assert.match(result.stderr, /依次发送并验证两条消息/);
});
