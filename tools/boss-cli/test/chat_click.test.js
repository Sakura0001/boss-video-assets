import assert from 'node:assert/strict';
import test from 'node:test';

import * as chat from '../dist/toolset/chat.js';

test('chat row selection uses a Puppeteer mouse click', async () => {
  const events = [];
  const row = {
    click: async () => {
      events.push('mouse-click');
    },
  };
  const wrap = {
    evaluate: async (callback) => {
      callback({
        querySelector: () => ({
          scrollIntoView: () => events.push('scroll'),
          click: () => events.push('dom-click'),
        }),
      });
    },
    $: async (selector) => {
      events.push(`query:${selector}`);
      return row;
    },
  };

  assert.equal(typeof chat.clickChatListRow, 'function');
  await chat.clickChatListRow(wrap);

  assert.deepEqual(events, ['scroll', 'query:.geek-item', 'mouse-click']);
});
