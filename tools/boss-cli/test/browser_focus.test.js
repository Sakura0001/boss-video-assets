import assert from 'node:assert/strict';
import test from 'node:test';

import { shouldBringBossPageToFront } from '../dist/common/boss_session_page.js';

test('normal Boss page operations stay in the background by default', () => {
    assert.equal(shouldBringBossPageToFront({}), false);
    assert.equal(shouldBringBossPageToFront({ BOSS_BROWSER_FOREGROUND: 'false' }), false);
});

test('foreground focus can be explicitly restored for debugging', () => {
    assert.equal(shouldBringBossPageToFront({ BOSS_BROWSER_FOREGROUND: 'true' }), true);
    assert.equal(shouldBringBossPageToFront({ BOSS_BROWSER_FOREGROUND: '1' }), true);
});
