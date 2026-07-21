import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { RECOMMEND_REFRESH_GAP_MS } from '../dist/browser/human_delay.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const cli = path.resolve(here, '../dist/cli/index.js');

test('recommend refresh interval stays within one to two seconds', () => {
  assert.deepEqual(RECOMMEND_REFRESH_GAP_MS, { min: 1000, max: 2000 });
});

test('help documents the explicit recommendation refresh flag', () => {
  const result = spawnSync(process.execPath, [cli, 'help'], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stderr, /boss recommend \[岗位关键字\] \[--refresh\]/);
  assert.match(result.stderr, /--refresh：随机等待 1–2 秒后显式刷新推荐页/);
});
