import type { Page } from 'puppeteer-core';
/**
 * 与 `list` 一致：若当前不在沟通列表则点侧栏「沟通」进入 `/web/chat/index`，
 * 再点左侧筛选「全部」并等待列表稳定。`chat` 在按姓名找人前需处于该状态。
 */
export declare function ensureChatIndexAllFilter(page: Page): Promise<void>;
export declare function runGetCandidateList(opts?: {
    unreadOnly?: boolean;
}): Promise<string>;
//# sourceMappingURL=list.d.ts.map