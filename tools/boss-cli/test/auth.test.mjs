import assert from 'node:assert/strict';
import test from 'node:test';

import {
  assertBossLoggedInFromPage,
  probeLoggedInFromPage,
} from '../dist/common/auth.js';

function fakePage(url, signals) {
  return {
    url: () => url,
    evaluate: async () => signals,
  };
}

test('treats the Boss login URL as logged out without trusting page content', async () => {
  let evaluated = false;
  const page = {
    url: () => 'https://www.zhipin.com/web/user/?ka=header-login',
    evaluate: async () => {
      evaluated = true;
      return { hasNickname: true, navLoginCta: false, hasLogoutHint: true };
    },
  };

  assert.deepEqual(await probeLoggedInFromPage(page), {
    loggedIn: false,
    url: 'https://www.zhipin.com/web/user/?ka=header-login',
  });
  assert.equal(evaluated, false);
});

test('accepts an explicit nickname signal as logged in', async () => {
  const page = fakePage('https://www.zhipin.com/web/chat/index', {
    hasNickname: true,
    navLoginCta: false,
    hasLogoutHint: false,
  });

  assert.deepEqual(await probeLoggedInFromPage(page), {
    loggedIn: true,
    url: 'https://www.zhipin.com/web/chat/index',
  });
  await assert.doesNotReject(assertBossLoggedInFromPage(page));
});

test('rejects a rendered chat shell when the navigation still asks the user to log in', async () => {
  const page = fakePage('https://www.zhipin.com/web/chat/index', {
    hasNickname: false,
    navLoginCta: true,
    hasLogoutHint: false,
  });

  await assert.rejects(
    assertBossLoggedInFromPage(page),
    /Boss 当前未登录.*boss login.*完成登录/s,
  );
});
