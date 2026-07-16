import { chmod, mkdir, open, readFile, rename, rm, writeFile } from 'node:fs/promises';
import { hostname } from 'node:os';
import { dirname } from 'node:path';
import {
  BOSS_COMMAND_PACING_LOCK_FILE,
  BOSS_COMMAND_PACING_STATE_FILE,
} from '../config.js';
import { randomIntInclusive, sleep } from './timing.js';

export type BossCommandPacingProfile = 'initial_outreach' | 'normal' | 'idle_unread_check';

export const BOSS_COMMAND_PACING_PROFILES = {
  initial_outreach: { minMs: 4_000, maxMs: 6_000 },
  normal: { minMs: 6_000, maxMs: 10_000 },
  idle_unread_check: { minMs: 30_000, maxMs: 60_000 },
} as const;

const NORMAL_BOSS_COMMANDS = new Set([
  'login',
  'list',
  'chat',
  'action',
  'send',
  'positions',
  'jd',
  'deep-search',
  'deepsearch',
  'search',
  'preview',
  'recommend',
]);
const LOCK_WAIT_MAX_MS = 30_000;
const LOCK_POLL_MS = 100;

type CommandPacingState = {
  schemaVersion: 1;
  lastCompletedAt: number;
  nextAllowedAt: number;
  lastProfile: BossCommandPacingProfile;
  lastCommand: string;
};

type CommandPacingLock = {
  pid: number;
  createdAt: number;
  hostname: string;
};

export type CommandPacingDependencies = {
  stateFile?: string;
  lockFile?: string;
  now?: () => number;
  sleep?: (ms: number) => Promise<void>;
  sampleDelay?: (profile: BossCommandPacingProfile) => number;
};

export function getBossCommandPacingProfile(
  command: string,
): BossCommandPacingProfile | undefined {
  if (command === 'greet') {
    return 'initial_outreach';
  }
  return NORMAL_BOSS_COMMANDS.has(command) ? 'normal' : undefined;
}

function defaultDelay(profile: BossCommandPacingProfile): number {
  const { minMs, maxMs } = BOSS_COMMAND_PACING_PROFILES[profile];
  return randomIntInclusive(minMs, maxMs);
}

function isPacingState(value: unknown): value is CommandPacingState {
  if (value === null || typeof value !== 'object') {
    return false;
  }
  const state = value as Partial<CommandPacingState>;
  return (
    state.schemaVersion === 1 &&
    Number.isFinite(state.lastCompletedAt) &&
    Number.isFinite(state.nextAllowedAt) &&
    typeof state.lastCommand === 'string' &&
    (state.lastProfile === 'initial_outreach' ||
      state.lastProfile === 'normal' ||
      state.lastProfile === 'idle_unread_check')
  );
}

async function readState(stateFile: string): Promise<CommandPacingState | null> {
  try {
    const parsed: unknown = JSON.parse(await readFile(stateFile, 'utf8'));
    return isPacingState(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

async function writeState(stateFile: string, state: CommandPacingState): Promise<void> {
  await mkdir(dirname(stateFile), { recursive: true, mode: 0o700 });
  const temporaryFile = `${stateFile}.${process.pid}.tmp`;
  await writeFile(temporaryFile, JSON.stringify(state), { encoding: 'utf8', mode: 0o600 });
  await chmod(temporaryFile, 0o600);
  await rename(temporaryFile, stateFile);
  await chmod(stateFile, 0o600);
}

function lockMeta(): CommandPacingLock {
  return { pid: process.pid, createdAt: Date.now(), hostname: hostname() };
}

async function processExists(pid: number): Promise<boolean> {
  if (!Number.isInteger(pid) || pid <= 0) {
    return false;
  }
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return !!(error && typeof error === 'object' && 'code' in error && error.code === 'EPERM');
  }
}

async function clearStaleLock(lockFile: string): Promise<void> {
  try {
    const parsed: unknown = JSON.parse(await readFile(lockFile, 'utf8'));
    if (parsed === null || typeof parsed !== 'object') {
      await rm(lockFile, { force: true });
      return;
    }
    const meta = parsed as Partial<CommandPacingLock>;
    if (typeof meta.pid !== 'number' || typeof meta.hostname !== 'string') {
      await rm(lockFile, { force: true });
      return;
    }
    if (meta.hostname === hostname() && !(await processExists(meta.pid))) {
      await rm(lockFile, { force: true });
    }
  } catch {
    await rm(lockFile, { force: true }).catch(() => {});
  }
}

async function withPacingLock<T>(
  lockFile: string,
  now: () => number,
  wait: (ms: number) => Promise<void>,
  callback: () => Promise<T>,
): Promise<T> {
  await mkdir(dirname(lockFile), { recursive: true, mode: 0o700 });
  const deadline = now() + LOCK_WAIT_MAX_MS;
  while (true) {
    try {
      const handle = await open(lockFile, 'wx', 0o600);
      try {
        await handle.writeFile(JSON.stringify(lockMeta()), 'utf8');
      } finally {
        await handle.close();
      }
      try {
        return await callback();
      } finally {
        await rm(lockFile, { force: true }).catch(() => {});
      }
    } catch (error) {
      const code = error && typeof error === 'object' && 'code' in error ? error.code : '';
      if (code !== 'EEXIST') {
        throw error;
      }
      await clearStaleLock(lockFile);
      if (now() >= deadline) {
        throw new Error(`Boss command pacing lock is busy for more than 30s: ${lockFile}`);
      }
      await wait(LOCK_POLL_MS);
    }
  }
}

/**
 * Serialize public Boss commands and enforce a randomized wait persisted across CLI processes.
 * The state intentionally stores no candidate, message, resume, cookie, or recruiting data.
 */
export async function runPacedBossCommand<T>(
  command: string,
  callback: () => Promise<T>,
  dependencies: CommandPacingDependencies = {},
): Promise<T> {
  const profile = getBossCommandPacingProfile(command);
  if (!profile) {
    return callback();
  }
  const stateFile = dependencies.stateFile ?? BOSS_COMMAND_PACING_STATE_FILE;
  const lockFile = dependencies.lockFile ?? BOSS_COMMAND_PACING_LOCK_FILE;
  const now = dependencies.now ?? Date.now;
  const wait = dependencies.sleep ?? sleep;
  const sampleDelay = dependencies.sampleDelay ?? defaultDelay;

  return withPacingLock(lockFile, now, wait, async () => {
    const previous = await readState(stateFile);
    const waitMs = Math.max(0, (previous?.nextAllowedAt ?? 0) - now());
    if (waitMs > 0) {
      await wait(waitMs);
    }
    try {
      return await callback();
    } finally {
      const completedAt = now();
      const delay = sampleDelay(profile);
      await writeState(stateFile, {
        schemaVersion: 1,
        lastCompletedAt: completedAt,
        nextAllowedAt: completedAt + delay,
        lastProfile: profile,
        lastCommand: command,
      });
    }
  });
}
