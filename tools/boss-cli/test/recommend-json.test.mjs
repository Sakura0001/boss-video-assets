import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import {
  assertGreetVerified,
  dedupeRecommendCandidates,
  recommendJobLabelMatches,
  serializeRecommendResult,
} from '../dist/toolset/recommend.js';

function candidate(overrides = {}) {
  return {
    geekId: 'candidate-1',
    name: '候选人',
    salary: '',
    baseInfo: '27年应届生 / 硕士',
    expect: '上海 算法工程师',
    experience: '浙江大学 人工智能',
    advantage: '',
    highlights: [],
    education: [
      {
        startYear: '2024',
        endYear: '2027',
        school: '浙江大学',
        major: '人工智能',
        degree: '硕士',
      },
    ],
    canGreet: true,
    hasHistoryChat: false,
    hasViewed: false,
    ...overrides,
  };
}

test('deduplicates repeated DOM cards by stable geek id', () => {
  const first = candidate();
  const duplicate = candidate({ name: '重复渲染名称' });
  const second = candidate({ geekId: 'candidate-2', name: '另一位' });

  assert.deepEqual(dedupeRecommendCandidates([first, duplicate, second]), [
    first,
    second,
  ]);
});

test('serializes the selected job and structured candidate fields', () => {
  const parsed = JSON.parse(
    serializeRecommendResult('ai应用研发工程师 _ 上海 25-30K', [candidate()]),
  );

  assert.equal(parsed.job, 'ai应用研发工程师 _ 上海 25-30K');
  assert.equal(parsed.candidates.length, 1);
  assert.equal(parsed.candidates[0].geekId, 'candidate-1');
  assert.equal(parsed.candidates[0].baseInfo, '27年应届生 / 硕士');
  assert.deepEqual(parsed.candidates[0].education, [
    {
      startYear: '2024',
      endYear: '2027',
      school: '浙江大学',
      major: '人工智能',
      degree: '硕士',
    },
  ]);
});

test('reuses the current recommendation job when it already matches', () => {
  assert.equal(
    recommendJobLabelMatches(
      'ai应用研发工程师 _ 上海 25-30K',
      'ai应用研发工程师',
    ),
    true,
  );
  assert.equal(
    recommendJobLabelMatches('数据库研发工程师', 'ai应用研发工程师'),
    false,
  );
  assert.equal(recommendJobLabelMatches('', 'ai应用研发工程师'), false);
});

test('verifies greet only after the exact stable id becomes unavailable', () => {
  const verified = assertGreetVerified(
    [candidate({ canGreet: false })],
    'candidate-1',
    '候选人',
  );
  assert.equal(verified.geekId, 'candidate-1');

  assert.throws(
    () => assertGreetVerified([candidate()], 'candidate-1', '候选人'),
    /仍可用/,
  );
  assert.throws(
    () => assertGreetVerified([], 'candidate-1', '候选人'),
    /无法在推荐列表中读回/,
  );
});

test('help documents machine-readable recommend and exact-id greet modes', () => {
  const result = spawnSync(process.execPath, ['dist/cli/index.js', 'help'], {
    cwd: new URL('..', import.meta.url),
    encoding: 'utf8',
  });
  assert.equal(result.status, 0);
  assert.match(result.stderr, /boss recommend \[岗位关键字\] \[--refresh\] \[--json\]/);
  assert.match(result.stderr, /右侧结构化教育经历/);
  assert.match(
    result.stderr,
    /boss greet <姓名> \[--id <候选人ID>\] \[--job <岗位关键字>\] \[--json\]/,
  );
});
