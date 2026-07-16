import assert from 'node:assert/strict';
import { mkdtemp, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {
  BOSS_COMMAND_PACING_PROFILES,
  getBossCommandPacingProfile,
  runPacedBossCommand,
} from '../dist/browser/command_pacing.js';

test('classifies greet as initial outreach and other Boss commands as normal', () => {
  assert.equal(getBossCommandPacingProfile('greet'), 'initial_outreach');
  assert.equal(getBossCommandPacingProfile('list'), 'normal');
  assert.equal(getBossCommandPacingProfile('send'), 'normal');
  assert.equal(getBossCommandPacingProfile('help'), undefined);
  assert.deepEqual(BOSS_COMMAND_PACING_PROFILES.initial_outreach, { minMs: 4_000, maxMs: 6_000 });
  assert.deepEqual(BOSS_COMMAND_PACING_PROFILES.normal, { minMs: 6_000, maxMs: 10_000 });
});

test('persists the next random wait and applies it before the next Boss command', async () => {
  const directory = await mkdtemp(path.join(tmpdir(), 'boss-command-pacing-'));
  const stateFile = path.join(directory, 'pacing.json');
  const lockFile = path.join(directory, 'pacing.lock');
  const waits = [];
  let now = 1_000;

  const dependencies = {
    stateFile,
    lockFile,
    now: () => now,
    sleep: async (ms) => {
      waits.push(ms);
    },
    sampleDelay: () => 6_789,
  };

  await runPacedBossCommand('list', async () => 'first', dependencies);
  assert.deepEqual(waits, []);

  await runPacedBossCommand('chat', async () => 'second', dependencies);
  assert.deepEqual(waits, [6_789]);

  const fileStat = await stat(stateFile);
  assert.equal(fileStat.mode & 0o777, 0o600);
});

test('still schedules the next wait when a Boss command fails', async () => {
  const directory = await mkdtemp(path.join(tmpdir(), 'boss-command-pacing-'));
  const waits = [];
  const dependencies = {
    stateFile: path.join(directory, 'pacing.json'),
    lockFile: path.join(directory, 'pacing.lock'),
    now: () => 1_000,
    sleep: async (ms) => {
      waits.push(ms);
    },
    sampleDelay: () => 5_432,
  };

  await assert.rejects(
    runPacedBossCommand('send', async () => {
      throw new Error('simulated command failure');
    }, dependencies),
    /simulated command failure/,
  );

  await runPacedBossCommand('list', async () => 'recovered', dependencies);
  assert.deepEqual(waits, [5_432]);
});
