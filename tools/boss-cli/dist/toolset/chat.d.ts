import type { ElementHandle, Page } from 'puppeteer-core';
export declare function runGetCommunicationHistory(page: Page): Promise<string>;
export declare function clickChatListRow(targetWrap: ElementHandle<Element>): Promise<void>;
export declare function runOpenCandidateChat(page: Page, candidateName: string, exact?: boolean): Promise<string>;
//# sourceMappingURL=chat.d.ts.map
