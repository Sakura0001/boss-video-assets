/**
 * Boss B 端「主壳」会话：选页、必要时进入沟通页、侧栏 `.menu-list` 探测，
 * 再执行 {@link withBossSessionPage} 回调。与 `src/toolset/chat.ts`（按姓名打开会话等业务）无关。
 */
import type { Page } from 'puppeteer-core';
export declare function shouldBringBossPageToFront(env?: Record<string, string | undefined>): boolean;
/**
 * 在已连接浏览器、且当前页为 Boss 主壳（含侧栏 `.menu-list`）的前提下执行回调。
 * 会先按 URL 确保落在 `/web/chat/*` 主壳页（已在主壳子页则保留原路径，否则跳回沟通页 `/web/chat/index`），
 * 再校验侧栏；回调内可再导航到职位/推荐等业务路由。
 */
export declare function withBossSessionPage<T>(callback: (page: Page) => Promise<T>): Promise<T>;
//# sourceMappingURL=boss_session_page.d.ts.map
